from datetime import datetime
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from zoneinfo import ZoneInfo
import os

def run_table_based_crawler():
    if not os.path.exists("data.json"):
        print("❌ data.json 파일이 존재하지 않습니다. 먼저 update_data.py를 실행해 주세요.")
        return

    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    target_matches = []
    daily_matches_input = data.get("daily_matches", {})
    
    # 💡 테스트를 위해 10개 경기만 타겟팅
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

    print(f"🎯 [스코어맨 정밀 클린 파싱] 10개 경기 수집 시작")

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
                    r_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "팀순위" in tag.get_text())
                    r_table = r_heading.find_next("table") if r_heading else None
                    if r_table:
                        for r_row in r_table.find_all("tr"):
                            cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"])]
                            if len(cols) >= 9:
                                if "팀" in cols[1] or "전체" in cols[0]:
                                    continue
                                rankings_data.append({
                                    "rank": cols[0], "team": cols[1], "played": cols[2],
                                    "win": cols[3], "draw": cols[4], "loss": cols[5],
                                    "goals_for": cols[6], "goals_against": cols[7],
                                    "goal_diff": cols[8], "points": cols[9] if len(cols) > 9 else ""
                                })
                except Exception as e:
                    print(f"  - 순위 파싱 예외 ({m_id}): {e}")

                # 2. 상대전적 표 형식 추출 (정확한 테이블 행만 타겟팅)
                h2h_data = {"matches": []}
                try:
                    h2h_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "상대전적" in tag.get_text())
                    h_table = h2h_heading.find_next("table") if h2h_heading else None
                    if h_table:
                        for h_row in h_table.find_all("tr"):
                            cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                            # 찌꺼기 텍스트 및 스탯 요약 필터링
                            joined = "".join(cols)
                            if any(w in joined for w in ["득점", "실점", "유효슈팅", "코너", "파울", "점유율", "최근 10경기"]):
                                continue
                            if len(cols) >= 3:
                                h2h_data["matches"].append({"row_data": cols})
                    if len(h2h_data["matches"]) > 5:
                        h2h_data["matches"] = h2h_data["matches"][:5]
                except Exception as e:
                    print(f"  - 상대전적 파싱 예외 ({m_id}): {e}")

                # 3. 최근전적 표 형식 추출 (날짜와 리그 코드가 포함된 진짜 경기 결과 행만 추출)
                recent_form = {"matches": []}
                try:
                    recent_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "최근전적" in tag.get_text())
                    if recent_heading:
                        # 최근전적 테이블 또는 컨테이너 탐색
                        r_table = recent_heading.find_next("table")
                        if r_table:
                            for r_row in r_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                joined = "".join(cols)
                                if any(w in joined for w in ["득점", "실점", "유효슈팅", "코너", "파울", "점유율", "최근 10경기"]):
                                    continue
                                if len(cols) >= 3:
                                    recent_form["matches"].append({"row_data": cols})
                    if len(recent_form["matches"]) > 5:
                        recent_form["matches"] = recent_form["matches"][:5]
                except Exception as e:
                    print(f"  - 최근전적 파싱 예외 ({m_id}): {e}")

                # 4. 결장자 정보 정밀 추출 (## 라인업 영역 바로 아래 결장자 목록 표만 정확히 타겟팅)
                absent_players = {"home": [], "away": []}
                try:
                    lineup_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "라인업" in tag.get_text())
                    if lineup_heading:
                        # 라인업 하위 첫 번째 테이블 또는 결장자 영역 컨테이너
                        l_table = lineup_heading.find_next("table")
                        if l_table:
                            for li_row in l_table.find_all("tr"):
                                player_texts = [p.get_text(strip=True) for p in li_row.find_all("td") if p.get_text(strip=True)]
                                if len(player_texts) >= 2:
                                    left_val = player_texts[0]
                                    right_val = player_texts[-1]
                                    
                                    # 퍼센트, 수치, 불필요한 키워드 필터링
                                    if "%" in left_val or "%" in right_val:
                                        continue
                                    try:
                                        float(left_val)
                                        float(right_val)
                                        continue
                                    except ValueError:
                                        pass
                                    
                                    if left_val and left_val not in ["홈", "원정", "결장", "지난 경기", "H2H", "컨디션", "공격", "수비", "가치", "기타"]:
                                        absent_players["home"].append(left_val)
                                    if right_val and right_val not in ["홈", "원정", "결장", "지난 경기", "H2H", "컨디션", "공격", "수비", "가치", "기타"]:
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
            
        print(f"\n🎉 성공: 총 {counter - 1}개 경기의 깔끔한 데이터가 match_details.json에 저장되었습니다!")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler()
