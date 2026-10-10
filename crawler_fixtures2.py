from datetime import datetime, timedelta
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from zoneinfo import ZoneInfo
import os

def run_table_based_crawler_v2():
    if not os.path.exists("data.json"):
        print("❌ data.json 파일이 존재하지 않습니다. 먼저 update_data.py를 실행해 주세요.")
        return

    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    target_matches = []
    daily_matches_input = data.get("daily_matches", {})
    
    # 💡 update_data.py와 동일한 방식으로 오늘 및 내일 날짜 키를 동적으로 계산
    kst = ZoneInfo("Asia/Seoul")
    today_kst = datetime.now(kst)
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    
    # offset=1 이 곧 '내일'입니다.
    tomorrow_dt = today_kst + timedelta(days=1)
    m_str = tomorrow_dt.strftime("%m")
    d_str = tomorrow_dt.strftime("%d")
    w_str = weekdays[tomorrow_dt.weekday()]
    
    # data.json에 기록되는 날짜 키 포맷과 일치시킴 (예: "10-11 (일)")
    tomorrow_date_key_prefix = f"{m_str}-{d_str} ({w_str})"
    print(f"📅 동적 계산된 내일 날짜 키 패턴: {tomorrow_date_key_prefix}")

    for date_key, matches in daily_matches_input.items():
        # 내일 날짜 키로 시작하는 블록을 정확히 타겟팅
        if date_key.startswith(tomorrow_date_key_prefix):
            print(f"🎯 발견한 내일 경기 블록: {date_key} (총 {len(matches)}개 경기)")
            for m in matches:
                m_code = m.get("match_code")
                if m_code and m_code not in [t["match_code"] for t in target_matches]:
                    target_matches.append({
                        "match_code": m_code,
                        "league": m.get("league", ""),
                        "home": m.get("home", ""),
                        "away": m.get("away", "")
                    })

    print(f"🎯 [내일 경기 정밀 수집] 총 {len(target_matches)}개 경기 수집 시작")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
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

                # ==========================================
                # 💡 팀전적 (오직 '전체' 탭의 첫 번째 종합 성적 행 1개만 엄격 타격 수집)
                # ==========================================
                rankings_data = []
                collected_teams = set()
                try:
                    standings_div = detail_soup.find("div", id="dv_league_standings")
                    target_tables = [standings_div] if standings_div else detail_soup.find_all("table", class_=["team-table-home", "team-table-guest"])
                    
                    for t_box in target_tables:
                        standing_rows = t_box.find_all("tr", class_=["tr_h_standing", "tr_a_standing"]) if t_box else []
                        for s_row in standing_rows:
                            row_id = s_row.get("id", "")
                            
                            # 조건별 세부 전적(_ht_) 행은 무조건 차단
                            if "_ht_" in row_id:
                                continue
                                
                            cols = [c.get_text(strip=True) for c in s_row.find_all(["th", "td"])]
                            if len(cols) >= 10:
                                rank_val = cols[0]
                                team_name = cols[1]
                                
                                # 순위가 없거나, 이미 '전체' 전적을 수집한 팀이거나, 타탭/헤더 텍스트인 경우 무시
                                if not rank_val or team_name in collected_teams or "홈" in team_name or "원정" in team_name:
                                    continue
                                
                                # 해당 팀의 첫 번째 발견된 행('전체' 탭 성적)만 허용하고 세트에 추가하여 타탭 행 차단
                                collected_teams.add(team_name)
                                
                                rankings_data.append({
                                    "rank": rank_val, "team": team_name, "played": cols[2],
                                    "win": cols[3], "draw": cols[4], "loss": cols[5],
                                    "goals_for": cols[6], "goals_against": cols[7],
                                    "goal_diff": cols[8], "points": cols[9]
                                })
                except Exception as e:
                    print(f"  - 순위 파싱 예외 ({m_id}): {e}")

                h2h_data = {"matches": []}
                try:
                    h2h_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "상대전적" in tag.get_text())
                    if h2h_heading:
                        h_table = h2h_heading.find_next("table")
                        if h_table:
                            for h_row in h_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                joined = "".join(cols)
                                if any(w in joined for w in ["득점", "실점", "유효슈팅", "코너", "파울", "점유율", "옐로카드", "최근 10경기", "날짜"]):
                                    continue
                                if len(cols) >= 3:
                                    h2h_data["matches"].append({"row_data": cols})
                    if len(h2h_data["matches"]) > 5:
                        h2h_data["matches"] = h2h_data["matches"][:5]
                except Exception as e:
                    print(f"  - 상대전적 파싱 예외 ({m_id}): {e}")

                recent_form = {"matches": []}
                try:
                    recent_heading = detail_soup.find(lambda tag: tag.name in ["h2", "h3", "h4", "div"] and "최근전적" in tag.get_text())
                    if recent_heading:
                        r_table = recent_heading.find_next("table")
                        if r_table:
                            for r_row in r_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                joined = "".join(cols)
                                if any(w in joined for w in ["득점", "실점", "유효슈팅", "코너", "파울", "점유율", "옐로카드", "최근 10경기", "날짜"]):
                                    continue
                                if len(cols) >= 3:
                                    recent_form["matches"].append({"row_data": cols})
                    if len(recent_form["matches"]) > 5:
                        recent_form["matches"] = recent_form["matches"][:5]
                except Exception as e:
                    print(f"  - 최근전적 파싱 예외 ({m_id}): {e}")

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
        
        with open("match_details_v2.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 내일({tomorrow_date_key_prefix}) 경기 총 {counter - 1}개의 데이터가 match_details_v2.json에 저장되었습니다!")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler_v2()
