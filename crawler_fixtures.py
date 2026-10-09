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
import os
import re

def run_table_based_crawler():
    if not os.path.exists("data.json"):
        print("❌ data.json 파일이 존재하지 않습니다. 먼저 update_data.py를 실행해 주세요.")
        return

    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    target_matches = []
    daily_matches_input = data.get("daily_matches", {})
    
    for date_key, matches in daily_matches_input.items():
        if "[오늘]" in date_key or "오늘" in date_key or len(target_matches) < 60:
            for m in matches:
                m_code = m.get("match_code")
                if m_code and m_code not in [t["match_code"] for t in target_matches]:
                    target_matches.append({
                        "match_code": m_code,
                        "league": m.get("league", ""),
                        "home": m.get("home", ""),
                        "away": m.get("away", "")
                    })

    print(f"🎯 표 형식 정밀 수집 대상 경기 수: {len(target_matches)}개")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    kst = ZoneInfo("Asia/Seoul")
    driver = webdriver.Chrome(options=options)
    
    match_details = {}
    counter = 1

    try:
        for target in target_matches:
            m_id = target["match_code"]
            detail_url = f"https://www.scoreman123.com/match/data-{m_id}"
            
            try:
                driver.get(detail_url)
                time.sleep(0.8)
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # 1. 팀 순위표 (표 형식으로 안전하게 추출, 상단 탭 텍스트 필터링)
                rankings_data = []
                try:
                    ranking_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "팀순위" in tag.get_text())
                    target_table = ranking_heading.find_next("table") if ranking_heading else None
                    
                    if target_table:
                        rows_list = target_table.find_all("tr")
                        for r_row in rows_list:
                            cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"])]
                            if len(cols) >= 9:
                                # 탭 이름 등 불필요한 헤더 행 제외
                                if "전체" in cols[0] or "H/A" in cols[0] or "팀" in cols[1]:
                                    continue
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
                except Exception as e:
                    print(f"  - 순위 파싱 예외 (ID: {m_id}): {e}")

                # 2. 상대전적 (표 형식 행렬 기준으로 안전하게 수집)
                h2h_data = {"matches": []}
                try:
                    h2h_section = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "상대전적" in tag.get_text())
                    if h2h_section:
                        h_table = h2h_section.find_next("table")
                        if h_table:
                            for h_row in h_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                if len(cols) >= 4:
                                    h2h_data["matches"].append({
                                        "row_data": cols
                                    })
                except Exception as e:
                    print(f"  - 상대전적 파싱 예외 (ID: {m_id}): {e}")

                # 3. 최근전적 (표 형식 행렬 기준으로 안전하게 수집)
                recent_form = {"matches": []}
                try:
                    recent_section = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "최근전적" in tag.get_text())
                    if recent_section:
                        r_table = recent_section.find_next("table")
                        if r_table:
                            for r_row in r_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                if len(cols) >= 4:
                                    recent_form["matches"].append({
                                        "row_data": cols
                                    })
                except Exception as e:
                    print(f"  - 최근전적 파싱 예외 (ID: {m_id}): {e}")

                # 4. 라인업 결장자 정보 (표 형식 행 기준 수집)
                absent_players = {"home": [], "away": []}
                try:
                    lineup_section = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "라인업" in tag.get_text())
                    if lineup_section:
                        l_table = lineup_section.find_next("table") or lineup_section.find_parent("div")
                        if l_table:
                            for li_row in l_table.find_all("tr"):
                                player_texts = [p.get_text(strip=True) for p in li_row.find_all("td") if p.get_text(strip=True)]
                                if len(player_texts) >= 2:
                                    # 스탯 수치 데이터가 아닌 실제 선수명 행만 선별
                                    absent_players["home"].append(player_texts[0])
                                    absent_players["away"].append(player_texts[-1])
                except Exception as e:
                    print(f"  - 라인업 파싱 예외 (ID: {m_id}): {e}")

                match_details[m_id] = {
                    "id": counter,
                    "match_code": m_id,
                    "league": target["league"],
                    "home": target["home"],
                    "away": target["away"],
                    "meta_details": {
                        "rankings": rankings_data,
                        "recent_form": recent_form,
                        "h2h": h2h_data,
                        "absent_players": absent_players
                    }
                }
                counter += 1

            except Exception as e:
                print(f"  ⚠️ 상세 페이지 수집 실패 (Match ID: {m_id}): {e}")
                continue

        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "match_details": match_details
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 총 {counter - 1}개 경기의 표 형식 정밀 데이터가 match_details.json에 동기화 완료되었습니다!")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler()
