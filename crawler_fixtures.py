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

def run_full_detailed_crawler():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    kst = ZoneInfo("Asia/Seoul")
    today = datetime.now(kst)
    date_key = today.strftime("%m-%d")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # 1. 메인 일정 페이지에서 경기별 상세 링크(match/data-XXXXX) 수집
        main_url = "https://www.scoreman123.com/football/fixture?f=sc1"
        print(f"🌐 메인 일정 페이지 접속 중: {main_url}")
        driver.get(main_url)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        match_links = []
        
        # 페이지 내 모든 a 태그 중 /match/data- 링크 추출
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "/match/data-" in href:
                full_link = href if href.startswith("http") else f"https://www.scoreman123.com{href}"
                if full_link not in match_links:
                    match_links.append(full_link)
        
        print(f"⚽ 수집된 상세 경기 링크 수: {len(match_links)}개")
        
        daily_matches = {date_key: []}
        match_id_counter = 1
        
        # 2. 각 경기의 상세 페이지에 직접 접속하여 필요한 정량 통계 파싱
        for detail_url in match_links[:15]: # 테스트 및 부하 방지를 위해 상위 경기부터 순회 (필요시 전체 순회)
            try:
                print(f"🔍 상세 페이지 분석 중: {detail_url}")
                driver.get(detail_url)
                time.sleep(1.5)
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # 기본 대진 정보 추출 (예: 라이프치히 vs 프랑크푸르트)
                title_el = detail_soup.find("h4")
                title_text = title_el.get_text() if title_el else ""
                
                league_el = detail_soup.find("a", href=lambda x: x and "/football/" in x)
                league_name = league_el.get_text(strip=True) if league_el else "기타 리그"
                
                # 팀 정보 및 스탯 파싱 (홈/원정 득점, 실점, 유효슈팅 등)
                team_stats = {"home": {}, "away": {}}
                tables = detail_soup.find_all("table")
                
                for table in tables:
                    rows = table.find_all("tr")
                    for row in rows:
                        cols = row.find_all(["th", "td"])
                        if len(cols) >= 3:
                            key = cols[1].get_text(strip=True)
                            val_home = cols[0].get_text(strip=True)
                            val_away = cols[2].get_text(strip=True)
                            if key in ["득점", "실점", "유효슈팅", "코너", "옐로카드", "파울", "점유율"]:
                                team_stats["home"][key] = val_home
                                team_stats["away"][key] = val_away

                match_item = {
                    "id": match_id_counter,
                    "league": league_name,
                    "time": "01:30", # 상세 페이지 내 시간 파싱으로 고도화 가능
                    "home": "홈팀",  # 타이틀이나 헤더에서 정밀 추출 가능
                    "away": "원정팀",
                    "meta_details": {
                        "stadium": "",
                        "stats": team_stats,
                        "rankings": [],
                        "absent_players": {"home": [], "away": []}
                    }
                }
                
                daily_matches[date_key].append(match_item)
                match_id_counter += 1
                
            except Exception as e:
                print(f"  ⚠️ 상세 페이지 파싱 중 에러: {e}")
                continue

        # 3. 결과 저장
        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 총 {match_id_counter - 1}개 경기의 상세 통계 데이터 수집 완료!")

    except Exception as e:
        print(f"❌ 크롤링 치명적 오류: {e}")
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump({"last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"), "daily_matches": {}}, f, ensure_ascii=False, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_full_detailed_crawler()
