from datetime import datetime
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from zoneinfo import ZoneInfo
import re

def run_match_id_crawler():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    kst = ZoneInfo("Asia/Seoul")
    today = datetime.now(kst)
    date_key = today.strftime("%m-%d") # 예: '10-10'
    
    driver = webdriver.Chrome(options=options)
    
    try:
        main_url = "https://www.scoreman123.com/football/fixture?f=sc1"
        print(f"🌐 메인 일정 페이지 접속 중: {main_url}")
        driver.get(main_url)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        match_ids = []
        
        # tr 태그의 id(예: tr1_3003904) 또는 onclick 내부의 숫자 추출
        rows = soup.find_all("tr")
        for row in rows:
            row_id = row.get("id", "")
            match_id_match = re.search(r'tr1_(\d+)', row_id)
            if match_id_match:
                m_id = match_id_match.group(1)
                if m_id not in match_ids:
                    match_ids.append(m_id)
            else:
                # onclick 속성에서 match id 탐색
                onclick_attr = row.get("onclick", "")
                if not onclick_attr:
                    td = row.find("td", onclick=True)
                    if td:
                        onclick_attr = td.get("onclick", "")
                
                m_match = re.search(r'analysis\((\d+)', onclick_attr)
                if m_match:
                    m_id = m_match.group(1)
                    if m_id not in match_ids:
                        match_ids.append(m_id)

        print(f"⚽ 추출된 고유 경기 Match ID 목록: {match_ids}")
        
        daily_matches = {date_key: []}
        match_counter = 1
        
        # 각 경기 고유 ID로 상세 페이지(https://www.scoreman123.com/match/data-{id}) 직접 접속
        for m_id in match_ids[:20]: # 우선 상위 20경기 수집 (부하 방지)
            detail_url = f"https://www.scoreman123.com/match/data-{m_id}"
            try:
                print(f"🔍 상세 통계 페이지 접속 중: {detail_url}")
                driver.get(detail_url)
                time.sleep(1.2)
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # 리그명 추출
                league_el = detail_soup.find("a", href=lambda x: x and "/football/" in x)
                league_name = league_el.get_text(strip=True) if league_el else "기타 리그"
                
                # 팀명 추출 (타이틀이나 헤더 영역)
                title_el = detail_soup.find("h4")
                home_team = "홈팀"
                away_team = "원정팀"
                if title_el:
                    title_text = title_el.get_text()
                    if "vs" in title_text.lower() or "VS" in title_text:
                        parts = re.split(r'vs|VS', title_text)
                        if len(parts) >= 2:
                            home_team = parts[0].strip()
                            away_team = re.split(r'라이브스코어|경기분석', parts[1])[0].strip()

                # 팀 통계 정량 데이터 파싱 (득점, 실점, 유효슈팅 등)
                team_stats = {"home": {}, "away": {}}
                tables = detail_soup.find_all("table")
                for table in tables:
                    for row in table.find_all("tr"):
                        cols = row.find_all(["th", "td"])
                        if len(cols) >= 3:
                            key = cols[1].get_text(strip=True)
                            val_home = cols[0].get_text(strip=True)
                            val_away = cols[2].get_text(strip=True)
                            if key in ["득점", "실점", "유효슈팅", "코너", "옐로카드", "파울", "점유율"]:
                                team_stats["home"][key] = val_home
                                team_stats["away"][key] = val_away

                match_item = {
                    "id": match_counter,
                    "match_code": m_id,
                    "league": league_name,
                    "time": "00:00",
                    "home": home_team,
                    "away": away_team,
                    "meta_details": {
                        "stadium": "",
                        "stats": team_stats,
                        "rankings": [],
                        "absent_players": {"home": [], "away": []}
                    }
                }
                
                daily_matches[date_key].append(match_item)
                match_counter += 1
                
            except Exception as e:
                print(f"  ⚠️ 상세 페이지 수집 실패 (ID: {m_id}): {e}")
                continue

        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 총 {match_counter - 1}개 경기의 상세 통계 데이터가 match_details.json에 빌드되었습니다!")

    except Exception as e:
        print(f"❌ 크롤링 에러 발생: {e}")
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump({"last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"), "daily_matches": {}}, f, ensure_ascii=False, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_match_id_crawler()
