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

def run_id_based_crawler():
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

    print(f"🎯 정밀 수집 대상 경기 수: {len(target_matches)}개")

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
                
                # 1. 팀 순위표 정밀 수집 (중복 제거 및 전체/홈/원정 구조화)
                rankings_data = []
                try:
                    # '팀순위' 타이틀 주변의 테이블만 정확히 타겟팅
                    ranking_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "팀순위" in tag.get_text())
                    target_table = None
                    if ranking_heading:
                        target_table = ranking_heading.find_next("table")
                    else:
                        # 차선책으로 헤더에 '승점'이 포함된 첫 번째 테이블 선택
                        tables = detail_soup.find_all("table")
                        for t in tables:
                            if "승점" in t.get_text():
                                target_table = t
                                break
                    
                    if target_table:
                        rows_list = target_table.find_all("tr")
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
                except Exception as e:
                    print(f"  - 순위 파싱 예외 (ID: {m_id}): {e}")

                # 2. 팀정보 스탯 정밀 수집 (득점, 실점, 유효슈팅, 점유율 등)
                team_stats = {}
                try:
                    stats_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "팀정보" in tag.get_text())
                    stats_table = stats_heading.find_next("table") if stats_heading else None
                    if stats_table:
                        for s_row in stats_table.find_all("tr"):
                            cols = [c.get_text(strip=True) for c in s_row.find_all(["th", "td"])]
                            if len(cols) == 3:
                                stat_name = cols[1]
                                team_stats[stat_name] = {
                                    "home": cols[0],
                                    "away": cols[2]
                                }
                except Exception as e:
                    print(f"  - 팀정보 스탯 파싱 예외 (ID: {m_id}): {e}")

                # 3. 최근전적 수집
                recent_form = {"matches": []}
                try:
                    recent_section = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "최근전적" in tag.get_text())
                    if recent_section:
                        r_table = recent_section.find_next("table")
                        if r_table:
                            for r_row in r_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"])]
                                if len(cols) >= 4:
                                    recent_form["matches"].append({"info": " | ".join(cols)})
                except Exception:
                    pass

                # 4. 상대전적 수집
                h2h_data = {"matches": []}
                try:
                    h2h_section = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "상대전적" in tag.get_text())
                    if h2h_section:
                        h_table = h2h_section.find_next("table")
                        if h_table:
                            for h_row in h_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"])]
                                if len(cols) >= 4:
                                    h2h_data["matches"].append({"info": " | ".join(cols)})
                except Exception:
                    pass

                # 5. 라인업 결장자 정보 수집
                absent_players = {"home": [], "away": []}
                try:
                    lineup_section = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "라인업" in tag.get_text())
                    if lineup_section:
                        l_table = lineup_section.find_next("table")
                        if l_table:
                            for li_row in l_table.find_all("tr"):
                                player_texts = [p.get_text(strip=True) for p in li_row.find_all("td") if p.get_text(strip=True)]
                                if len(player_texts) >= 1:
                                    absent_players["home"].append(player_texts[0])
                                if len(player_texts) >= 2:
                                    absent_players["away"].append(player_texts[-1])
                except Exception:
                    pass

                match_details[m_id] = {
                    "id": counter,
                    "match_code": m_id,
                    "league": target["league"],
                    "home": target["home"],
                    "away": target["away"],
                    "meta_details": {
                        "rankings": rankings_data,
                        "team_stats": team_stats,
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
            
        print(f"\n🎉 성공: 총 {counter - 1}개 경기의 정밀 분석 데이터가 match_details.json에 동기화되었습니다!")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_id_based_crawler()
