from datetime import datetime, timedelta
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

def run_comprehensive_crawler():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    kst = ZoneInfo("Asia/Seoul")
    today = datetime.now(kst)
    tomorrow = today + timedelta(days=1)
    
    target_dates = [
        today.strftime("%m-%d"),
        tomorrow.strftime("%m-%d")
    ]
    
    driver = webdriver.Chrome(options=options)
    
    try:
        main_url = "https://www.scoreman123.com/football/fixture?f=sc1"
        print(f"🌐 메인 일정 페이지 접속 중: {main_url}")
        driver.get(main_url)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        match_ids = []
        
        # 메인 페이지에서 경기 ID 수집
        rows = soup.find_all("tr")
        for row in rows:
            row_id = row.get("id", "")
            match_id_match = re.search(r'tr1_(\d+)', row_id)
            if match_id_match:
                m_id = match_id_match.group(1)
                if m_id not in match_ids:
                    match_ids.append(m_id)
            else:
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

        print(f"⚽ 추출된 총 경기 Match ID 목록: {len(match_ids)}개")
        
        daily_matches = {d: [] for d in target_dates}
        match_counter = 1
        
        for m_id in match_ids:
            detail_url = f"https://www.scoreman123.com/match/data-{m_id}"
            try:
                driver.get(detail_url)
                time.sleep(1.0)
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                date_str = today.strftime("%m-%d")
                time_str = "00:00"
                
                header_el = detail_soup.find("h4")
                header_text = header_el.get_text(strip=True) if header_el else ""
                
                # 날짜 및 시간 추출
                date_time_match = re.search(r'(\d{4}\.\d{2}\.\d{2})\s+(\d{2}:\d{2})', detail_soup.get_text())
                if date_time_match:
                    full_date_str = date_time_match.group(1)
                    time_str = date_time_match.group(2)
                    try:
                        dt_obj = datetime.strptime(full_date_str, "%Y.%m.%d")
                        date_str = dt_obj.strftime("%m-%d")
                    except Exception:
                        pass
                
                # 오늘/내일 경기만 필터링
                if date_str not in target_dates:
                    continue
                
                league_el = detail_soup.find("a", href=lambda x: x and "/football/" in x)
                league_name = league_el.get_text(strip=True) if league_el else "기타 리그"
                
                home_team = "홈팀"
                away_team = "원정팀"
                if header_text:
                    if "vs" in header_text.lower() or "VS" in header_text:
                        parts = re.split(r'vs|VS', header_text)
                        if len(parts) >= 2:
                            home_team = parts[0].strip()
                            away_team = re.split(r'라이브스코어|경기분석', parts[1])[0].strip()

                # 구장 정보 안전 추출
                stadium_name = ""
                stadium_el = detail_soup.find("a", href=lambda x: x and any(k in x for k in ["Arena", "Stadium", "Park"]))
                if stadium_el:
                    stadium_name = stadium_el.get_text(strip=True)

                # 1. 팀 순위 정보 수집
                rankings_data = []
                try:
                    tables = detail_soup.find_all("table")
                    for t in tables:
                        headers = [th.get_text(strip=True) for th in t.find_all(["th", "td"])[:10]]
                        if "승점" in "".join(headers) or "승" in headers:
                            rows_list = t.find_all("tr")
                            if len(rows_list) > 1:
                                for r_row in rows_list[1:]:
                                    cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"])]
                                    if len(cols) >= 9:
                                        rankings_data.append({
                                            "rank": cols[0],
                                            "team": cols[1],
                                            "played": cols[2],
                                            "win": cols[3],
                                            "draw": cols[4],
                                            "loss": cols[5],
                                            "goals_for": cols[6],
                                            "goals_against": cols[7],
                                            "goal_diff": cols[8],
                                            "points": cols[9] if len(cols) > 9 else ""
                                        })
                            break
                except Exception:
                    pass

                # 2. 최근전적 수집 (표 및 스코어 안전 정제)
                recent_form = {"summary": {}, "matches": []}
                try:
                    recent_section = detail_soup.find(text=re.compile("최근전적"))
                    if recent_section:
                        parent_div = recent_section.find_parent("div")
                        if parent_div:
                            for r_row in parent_div.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"])]
                                if len(cols) >= 4:
                                    recent_form["matches"].append({
                                        "info": " | ".join(cols[:6])
                                    })
                except Exception:
                    pass

                # 3. 상대전적 수집
                h2h_data = {"summary": {}, "matches": []}
                try:
                    h2h_section = detail_soup.find(text=re.compile("상대전적"))
                    if h2h_section:
                        h2h_parent = h2h_section.find_parent("div")
                        if h2h_parent:
                            for h_row in h2h_parent.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"])]
                                if len(cols) >= 4:
                                    h2h_data["matches"].append({
                                        "info": " | ".join(cols[:6])
                                    })
                except Exception:
                    pass

                # 4. 라인업 결장자 정보 수집
                absent_players = {"home": [], "away": []}
                try:
                    lineup_section = detail_soup.find(text=re.compile("라인업"))
                    if lineup_section:
                        l_parent = lineup_section.find_parent("div")
                        if l_parent:
                            for li_row in l_parent.find_all("tr"):
                                player_texts = [p.get_text(strip=True) for p in li_row.find_all("td") if p.get_text(strip=True)]
                                if len(player_texts) >= 1:
                                    absent_players["home"].append(player_texts[0])
                                if len(player_texts) >= 2:
                                    absent_players["away"].append(player_texts[-1])
                except Exception:
                    pass

                match_item = {
                    "id": match_counter,
                    "match_code": m_id,
                    "league": league_name,
                    "time": time_str,
                    "home": home_team,
                    "away": away_team,
                    "meta_details": {
                        "stadium": stadium_name,
                        "rankings": rankings_data,
                        "recent_form": recent_form,
                        "h2h": h2h_data,
                        "absent_players": absent_players
                    }
                }
                
                daily_matches[date_str].append(match_item)
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
            
        print(f"\n🎉 성공: 오늘/내일 총 {match_counter - 1}개 경기의 상세 정보 수집 완료!")

    except Exception as e:
        print(f"❌ 크롤링 에러 발생: {e}")
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump({"last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"), "daily_matches": {}}, f, ensure_ascii=False, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_comprehensive_crawler()
