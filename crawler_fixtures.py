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

    print(f"🎯 [스코어맨 DOM 구조 맞춤 파싱] 10개 경기 정밀 수집 시작")

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
                
                # 1. 팀 순위표 파싱 (## 팀순위 헤더 다음의 table 타겟팅)
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

                # 2. 상대전적 파싱 (## 상대전적 헤더 다음의 table 타겟팅)
                h2h_data = {"matches": []}
                try:
                    h2h_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "상대전적" in tag.get_text())
                    h_table = h2h_heading.find_next("table") if h2h_heading else None
                    if h_table:
                        for h_row in h_table.find_all("tr"):
                            cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                            if len(cols) >= 4:
                                h2h_data["matches"].append({"row_data": cols})
                    if len(h2h_data["matches"]) > 5:
                        h2h_data["matches"] = h2h_data["matches"][:5]
                except Exception as e:
                    print(f"  - 상대전적 파싱 예외 ({m_id}): {e}")

                # 3. 최근전적 파싱 (## 최근전적 헤더 다음의 li 혹은 표 형태 리스트 탐색)
                recent_form = {"matches": []}
                try:
                    recent_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "최근전적" in tag.get_text())
                    if recent_heading:
                        # 최근전적은 li 또는 div 행태그로 나열되어 있음
                        container = recent_heading.find_parent("div") or recent_heading
                        items = container.find_all("li")
                        for item in items:
                            txt = item.get_text(strip=True)
                            # 날짜 및 경기 결과 패턴이 포함된 라인만 추출
                            if txt and any(w in txt for w in ["GER", "UEFA", "INT", "분데스리가", "프리미어", "승", "패", "무"]):
                                cols = [span.get_text(strip=True) for span in item.find_all(["span", "div", "a"]) if span.get_text(strip=True)]
                                if len(cols) >= 3:
                                    recent_form["matches"].append({"row_data": cols})
                    if len(recent_form["matches"]) > 5:
                        recent_form["matches"] = recent_form["matches"][:5]
                except Exception as e:
                    print(f"  - 최근전적 파싱 예외 ({m_id}): {e}")

                # 4. 경기일정 파싱 (## 경기일정 헤더 하위 리스트 추출)
                fixtures_data = []
                try:
                    fix_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "경기일정" in tag.get_text())
                    if fix_heading:
                        fix_container = fix_heading.find_parent("div") or fix_heading
                        for li in fix_container.find_all("li"):
                            li_txt = li.get_text(strip=True)
                            if li_txt and ("2026" in li_txt or "일" in li_txt):
                                fixtures_data.append({"info": li_txt})
                except Exception as e:
                    print(f"  - 경기일정 파싱 예외 ({m_id}): {e}")

                # 5. 결장자 정보 파싱 (## 라인업 하위 항목)
                absent_players = {"home": [], "away": []}
                try:
                    lineup_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "라인업" in tag.get_text())
                    if lineup_heading:
                        l_container = lineup_heading.find_parent("div") or lineup_heading
                        for li in l_container.find_all("li"):
                            li_text = li.get_text(strip=True)
                            # 선수명과 번호가 포함된 라인에서 불필요한 기호 제외하고 파싱
                            if li_text and ("-" not in li_text or len(li_text) < 20):
                                parts = [p.strip() for p in li_text.split("") if p.strip()]
                                if len(parts) >= 1:
                                    absent_players["home"].append(parts[0])
                                if len(parts) >= 2:
                                    absent_players["away"].append(parts[-1])
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
                        "fixtures": fixtures_data,
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
            
        print(f"\n🎉 성공: 총 {counter - 1}개 경기의 완벽한 표 및 일정 데이터가 match_details.json에 저장되었습니다!")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler()
