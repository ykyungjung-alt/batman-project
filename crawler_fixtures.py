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
    
    # 💡 테스트를 위해 최대 10개 경기만 타겟팅
    for date_key, matches in daily_matches_input.items():
        for m in matches:
            m_code = m.get("match_code")
            if m_code and m_code not in [t["match_code"] for t in target_matches]:
                target_matches.append({
                    "match_code": m_code,
                    "league": m.get("league", ""),
                    "home": m.get("home", ""),
                    "away": m.get("away", "")
                })
            if len(target_matches) >= 10:
                break
        if len(target_matches) >= 10:
            break

    print(f"🎯 [테스트] 딱 10개 경기만 정밀 수집을 시작합니다.")

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
                time.sleep(1.0)
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # 1. 팀 순위표 정밀 추출
                rankings_data = []
                try:
                    ranking_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "팀순위" in tag.get_text())
                    if ranking_heading:
                        target_table = ranking_heading.find_next("table")
                        if target_table:
                            for r_row in target_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"])]
                                if len(cols) >= 9:
                                    # 탭 이름이나 헤더 행 제외
                                    if any(w in cols[0] for w in ["전체", "H/A", "최근", "전반"]) or "팀" in cols[1]:
                                        continue
                                    rankings_data.append({
                                        "rank": cols[0], "team": cols[1], "played": cols[2],
                                        "win": cols[3], "draw": cols[4], "loss": cols[5],
                                        "goals_for": cols[6], "goals_against": cols[7],
                                        "goal_diff": cols[8], "points": cols[9] if len(cols) > 9 else ""
                                    })
                except Exception as e:
                    print(f"  - 순위 파싱 예외 ({m_id}): {e}")

                # 2. 상대전적 표 형식 추출 (최근 5개만 안전하게)
                h2h_data = {"matches": []}
                try:
                    h2h_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "상대전적" in tag.get_text())
                    if h2h_heading:
                        h_table = h2h_heading.find_next("table")
                        if h_table:
                            for h_row in h_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                if len(cols) >= 3:
                                    h2h_data["matches"].append({"row_data": cols})
                    if len(h2h_data["matches"]) > 5:
                        h2h_data["matches"] = h2h_data["matches"][:5]
                except Exception as e:
                    print(f"  - 상대전적 파싱 예외 ({m_id}): {e}")

                # 3. 최근전적 표 형식 추출 (최근 5개만 안전하게)
                recent_form = {"matches": []}
                try:
                    recent_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "최근전적" in tag.get_text())
                    if recent_heading:
                        r_table = recent_heading.find_next("table")
                        if r_table:
                            for r_row in r_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                if len(cols) >= 3:
                                    recent_form["matches"].append({"row_data": cols})
                    if len(recent_form["matches"]) > 5:
                        recent_form["matches"] = recent_form["matches"][:5]
                except Exception as e:
                    print(f"  - 최근전적 파싱 예외 ({m_id}): {e}")

                # 4. 결장자 정보 추출 (라인업 섹션 내부의 테이블 행만 엄선)
                absent_players = {"home": [], "away": []}
                try:
                    lineup_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "라인업" in tag.get_text())
                    if lineup_heading:
                        l_table = lineup_heading.find_next("table")
                        if l_table:
                            for li_row in l_table.find_all("tr"):
                                player_texts = [p.get_text(strip=True) for p in li_row.find_all("td") if p.get_text(strip=True)]
                                # 선수 이름 칸에 스탯 수치(예: 소수점 점수)가 들어오지 않도록 검증
                                if len(player_texts) >= 2:
                                    left_val = player_texts[0]
                                    right_val = player_texts[-1]
                                    try:
                                        float(left_val)
                                        float(right_val)
                                        continue
                                    except ValueError:
                                        pass
                                    
                                    if left_val and left_val not in ["홈", "원정", "결장", "지난 경기"]:
                                        absent_players["home"].append(left_val)
                                    if right_val and right_val not in ["홈", "원정", "결장", "지난 경기"]:
                                        absent_players["away"].append(right_val)
                except Exception as e:
                    print(f"  - 라인업 파싱 예외 ({m_id}): {e}")

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
            
        print(f"\n🎉 테스트 완료: 총 {counter - 1}개 경기 데이터가 match_details.json에 저장되었습니다.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler()
