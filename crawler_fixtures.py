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

    print(f"🎯 [경기일정 및 전체 영역 완벽 정밀 타격] 10개 경기 수집 시작")

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
                
                # 0. 상단 메타 정보 정밀 추출
                match_time = ""
                league_name = target["league"]
                round_info = ""
                stadium_name = ""
                
                try:
                    sclass_span = detail_soup.find("span", {"class": "sclassListLink"})
                    if sclass_span:
                        full_text = sclass_span.get_text(separator=" ", strip=True)
                        league_name = full_text.split("·")[0].strip() if "·" in full_text else full_text
                        round_info = full_text.split("·")[1].strip() if "·" in full_text else ""
                    
                    time_span = detail_soup.find("span", {"name": "timeData"})
                    if time_span and time_span.has_attr("data-t"):
                        match_time = time_span["data-t"]
                        
                    other_info_div = detail_soup.find("div", {"id": "otherInfo"})
                    if other_info_div:
                        stadium_text = other_info_div.get_text(strip=True)
                        if stadium_text:
                            stadium_name = stadium_text
                except Exception:
                    pass

                # 1. 팀 순위표 정밀 추출
                rankings_data = []
                try:
                    standing_rows = detail_soup.find_all("tr", class_=["tr_h_standing", "tr_a_standing"])
                    for s_row in standing_rows:
                        cols = [c.get_text(strip=True) for c in s_row.find_all(["th", "td"])]
                        if len(cols) >= 10:
                            rankings_data.append({
                                "rank": cols[0], "team": cols[1], "played": cols[2],
                                "win": cols[3], "draw": cols[4], "loss": cols[5],
                                "goals_for": cols[6], "goals_against": cols[7],
                                "goal_diff": cols[8], "points": cols[9]
                            })
                    if not rankings_data:
                        r_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "팀순위" in tag.get_text())
                        r_table = r_heading.find_next("table") if r_heading else None
                        if r_table:
                            for r_row in r_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"])]
                                if len(cols) >= 9 and not any(w in cols[0] for w in ["전체", "H/A", "팀"]):
                                    rankings_data.append({
                                        "rank": cols[0], "team": cols[1], "played": cols[2],
                                        "win": cols[3], "draw": cols[4], "loss": cols[5],
                                        "goals_for": cols[6], "goals_against": cols[7],
                                        "goal_diff": cols[8], "points": cols[9] if len(cols) > 9 else ""
                                    })
                except Exception as e:
                    print(f"  - 순위 파싱 예외 ({m_id}): {e}")

                # 2. 상대전적 표 형식 정밀 추출
                h2h_data = {"matches": []}
                try:
                    h2h_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "상대전적" in tag.get_text())
                    if h2h_heading:
                        h_table = h2h_heading.find_next("table")
                        if h_table:
                            for h_row in h_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                joined = "".join(cols)
                                if any(w in joined for w in ["득점", "실점", "유효슈팅", "코너", "파울", "점유율", "최근 10경기", "날짜"]):
                                    continue
                                if len(cols) >= 3:
                                    h2h_data["matches"].append({"row_data": cols})
                    if len(h2h_data["matches"]) > 5:
                        h2h_data["matches"] = h2h_data["matches"][:5]
                except Exception as e:
                    print(f"  - 상대전적 파싱 예외 ({m_id}): {e}")

                # 3. 최근전적 표 형식 정밀 추출
                recent_form = {"matches": []}
                try:
                    recent_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "최근전적" in tag.get_text())
                    if recent_heading:
                        r_table = recent_heading.find_next("table")
                        if r_table:
                            for r_row in r_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                joined = "".join(cols)
                                if any(w in joined for w in ["득점", "실점", "유효슈팅", "코너", "파울", "점유율", "최근 10경기", "날짜"]):
                                    continue
                                if len(cols) >= 3:
                                    recent_form["matches"].append({"row_data": cols})
                        
                        if not recent_form["matches"]:
                            container = recent_heading.find_parent("div") or recent_heading
                            for li in container.find_all(["li", "div"]):
                                li_text = li.get_text(strip=True)
                                if li_text and any(w in li_text for w in ["GER", "UEFA", "INT", "분데스리가", "프리미어", "승", "패", "무", "2026"]) and "경기당" not in li_text:
                                    cols = [span.get_text(strip=True) for span in li.find_all(["span", "div", "a"]) if span.get_text(strip=True)]
                                    if len(cols) >= 3:
                                        recent_form["matches"].append({"row_data": cols})
                    if len(recent_form["matches"]) > 5:
                        recent_form["matches"] = recent_form["matches"][:5]
                except Exception as e:
                    print(f"  - 최근전적 파싱 예외 ({m_id}): {e}")

                # 4. 경기일정 정밀 추출 (dv_futer.plates 및 courselis 구조 기반 타겟팅)
                fixtures_data = []
                try:
                    futer_div = detail_soup.find("div", id="dv_futer")
                    if futer_div:
                        course_items = futer_div.find_all("li", class_="courselis")
                        for c_item in course_items:
                            item_text = c_item.get_text(separator=" ", strip=True)
                            if item_text:
                                fixtures_data.append({"info": item_text})
                except Exception as e:
                    print(f"  - 경기일정 파싱 예외 ({m_id}): {e}")

                # 5. 결장자 정보 정밀 추출
                absent_players = {"home": [], "away": []}
                try:
                    lineup_box = detail_soup.find("ul", class_="lineupbox")
                    if lineup_box:
                        lineup_items = lineup_box.find_all("li", class_="lineupis")
                        for l_item in lineup_items:
                            home_div = l_item.find("div", class_="home")
                            if home_div:
                                player_a = home_div.find("div", class_="player")
                                if player_a:
                                    p_name = player_a.get_text(strip=True)
                                    if p_name and p_name not in absent_players["home"]:
                                        absent_players["home"].append(p_name)
                            
                            guest_div = l_item.find("div", class_="guest")
                            if guest_div:
                                player_a = guest_div.find("div", class_="player")
                                if player_a:
                                    p_name = player_a.get_text(strip=True)
                                    if p_name and p_name not in absent_players["away"]:
                                        absent_players["away"].append(p_name)
                except Exception as e:
                    print(f"  - 결장자 파싱 예외 ({m_id}): {e}")

                match_details[m_id] = {
                    "id": counter,
                    "match_code": m_id,
                    "league": league_name,
                    "round": round_info,
                    "home": target["home"],
                    "away": target["away"],
                    "match_time": match_time,
                    "stadium": stadium_name,
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
            
        print(f"\n🎉 성공: 경기일정(`dv_futer`)까지 완벽 반영된 총 {counter - 1}개 경기 데이터가 동기화되었습니다!")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler()
