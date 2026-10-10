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
        if "[오늘]" in date_key or "오늘" in date_key:
            for m in matches:
                m_code = m.get("match_code")
                if m_code and m_code not in [t["match_code"] for t in target_matches]:
                    target_matches.append({
                        "match_code": m_code,
                        "league": m.get("league", ""),
                        "home": m.get("home", ""),
                        "away": m.get("away", "")
                    })

    print(f"🎯 [전체 경기 정밀 수집] 총 {len(target_matches)}개 경기 수집 시작")

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
                
                # ==========================================
                # 1. 헤드 정보 독립 분류 (리그, 라운드, 시간, 구장, 날씨)
                # ==========================================
                head_info = {
                    "league": target["league"],
                    "round": "",
                    "match_time_raw": "",
                    "match_time_display": "",
                    "stadium": "",
                    "weather": ""
                }
                
                try:
                    sclass_span = detail_soup.find("span", {"class": "sclassListLink"})
                    if sclass_span:
                        full_text = sclass_span.get_text(separator=" ", strip=True)
                        if "라운드" in full_text:
                            parts = full_text.split("라운드")
                            head_info["league"] = parts[0].strip()
                            head_info["round"] = "라운드 " + parts[1].strip()
                        else:
                            head_info["league"] = full_text
                    
                    time_span = detail_soup.find("span", {"name": "timeData"})
                    if time_span:
                        if time_span.has_attr("data-t"):
                            head_info["match_time_raw"] = time_span["data-t"]
                        disp_text = time_span.get_text(strip=True)
                        if disp_text:
                            head_info["match_time_display"] = disp_text
                        
                    other_info_div = detail_soup.find("div", {"id": "otherInfo"})
                    if other_info_div:
                        spans = other_info_div.find_all("span")
                        for s in spans:
                            s_text = s.get_text(strip=True)
                            if any(w in s_text for w in ["°C", "비", "맑음", "구름", "이슬비", "눈"]):
                                head_info["weather"] = s_text
                            elif s_text:
                                head_info["stadium"] = s_text
                except Exception as e:
                    print(f"  - 헤드 정보 파싱 예외 ({m_id}): {e}")

                # ==========================================
                # 2. 리그전적 (홈팀 리그전적 / 원정팀 리그전적 구분)
                # ==========================================
                rankings_data = []
                seen_rankings = set()
                try:
                    standing_rows = detail_soup.find_all("tr", class_=["tr_h_standing", "tr_a_standing"])
                    for s_row in standing_rows:
                        cols = [c.get_text(strip=True) for c in s_row.find_all(["th", "td"])]
                        if len(cols) >= 10:
                            row_class = " ".join(s_row.get("class", []))
                            row_id = s_row.get("id", "")
                            
                            if "tr_h_standing" in row_class or "home" in row_id:
                                team_type = "홈팀 리그전적"
                            else:
                                team_type = "원정팀 리그전적"
                            
                            sub_category = "전체 전적"
                            if "_ht_" in row_id:
                                sub_category = "조건별 세부 리그전적"
                            elif "rank" in row_id or "standing" in row_id:
                                sub_category = "종합 순위표"

                            row_key = (team_type, sub_category, cols[0], cols[1], cols[2], cols[9])
                            if row_key in seen_rankings:
                                continue
                            seen_rankings.add(row_key)
                            
                            rankings_data.append({
                                "team_type": team_type,
                                "sub_category": sub_category,
                                "rank": cols[0], 
                                "team": cols[1], 
                                "played": cols[2],
                                "win": cols[3], 
                                "draw": cols[4], 
                                "loss": cols[5],
                                "goals_for": cols[6], 
                                "goals_against": cols[7],
                                "goal_diff": cols[8], 
                                "points": cols[9]
                            })
                except Exception as e:
                    print(f"  - 리그전적 파싱 예외 ({m_id}): {e}")

                # ==========================================
                # 3. 맞대결 전적 (ID범위 고정 및 좌우 순서 엄격 적용)
                # ==========================================
                h2h_data = {"home_summary": {}, "away_summary": {}, "matches": []}
                try:
                    h2h_div = detail_soup.find("div", id="dv_head_to_head")
                    if h2h_div:
                        vote_divs = h2h_div.find_all("div", class_="vote")
                        for v in vote_divs:
                            ext_els = v.find_all("div", class_=["ext", "win-f", "draw-f", "lose-f"])
                            if len(ext_els) >= 3:
                                left_val = ext_els[0].get_text(strip=True)
                                label = ext_els[1].get_text(strip=True)
                                right_val = ext_els[2].get_text(strip=True)
                                
                                if "승" in label or "%" in left_val or "무승부" in label:
                                    h2h_data["home_summary"]["record_summary"] = left_val
                                    h2h_data["away_summary"]["record_summary"] = right_val
                                elif "경기당 득점" in label or "득점" in label:
                                    h2h_data["home_summary"]["goals_per_game"] = left_val
                                    h2h_data["away_summary"]["goals_per_game"] = right_val
                                elif "경기당 실점" in label or "실점" in label:
                                    h2h_data["home_summary"]["conceded_per_game"] = left_val
                                    h2h_data["away_summary"]["conceded_per_game"] = right_val

                        h_table = h2h_div.find_next("table")
                        if h_table:
                            for h_row in h_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                if len(cols) >= 3 and not any("득점" in c for c in cols):
                                    h2h_data["matches"].append({"row_data": cols})
                    if len(h2h_data["matches"]) > 10:
                        h2h_data["matches"] = h2h_data["matches"][:10]
                except Exception as e:
                    print(f"  - 맞대결 파싱 예외 ({m_id}): {e}")

                # ==========================================
                # 4. 최근전적 (ID범위 고정 및 좌우 순서 엄격 적용)
                # ==========================================
                recent_form = {"home_summary": {}, "away_summary": {}, "matches": []}
                try:
                    recent_div = detail_soup.find("div", id="dv_recent")
                    if recent_div:
                        vote_divs = recent_div.find_all("div", class_="vote")
                        for v in vote_divs:
                            ext_els = v.find_all("div", class_=["ext", "win-f", "draw-f", "p2"])
                            if len(ext_els) >= 3:
                                left_val = ext_els[0].get_text(strip=True)
                                label = ext_els[1].get_text(strip=True)
                                right_val = ext_els[2].get_text(strip=True)
                                
                                if "최근전적" in label:
                                    recent_form["home_summary"]["recent_record"] = left_val
                                    recent_form["away_summary"]["recent_record"] = right_val
                                elif "경기당 득점" in label:
                                    recent_form["home_summary"]["goals_per_game"] = left_val
                                    recent_form["away_summary"]["goals_per_game"] = right_val
                                elif "경기당 실점" in label:
                                    recent_form["home_summary"]["conceded_per_game"] = left_val
                                    recent_form["away_summary"]["conceded_per_game"] = right_val

                        r_table = recent_div.find_next("table")
                        if r_table:
                            for r_row in r_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                if len(cols) >= 3 and not any("득점" in c for c in cols):
                                    recent_form["matches"].append({"row_data": cols})
                    if len(recent_form["matches"]) > 10:
                        recent_form["matches"] = recent_form["matches"][:10]
                except Exception as e:
                    print(f"  - 최근전적 파싱 예외 ({m_id}): {e}")

                # ==========================================
                # 5. 라인업 및 성향 지표 (좌우 분리 및 6개 규격 제한)
                # ==========================================
                lineup_data = {"home": [], "away": []}
                try:
                    lineup_boxes = detail_soup.find_all("div", class_=["lineupbox", "lineupis", "tacticsbox"])
                    for l_box in lineup_boxes:
                        home_side = l_box.find("div", class_=["home", "left-side"])
                        if home_side:
                            items = home_side.find_all(["div", "li", "span"], class_=["player", "item", "val"])
                            for item in items:
                                text = item.get_text(strip=True)
                                if text and text not in lineup_data["home"]:
                                    lineup_data["home"].append(text)
                        
                        guest_side = l_box.find("div", class_=["guest", "right-side"])
                        if guest_side:
                            items = guest_side.find_all(["div", "li", "span"], class_=["player", "item", "val"])
                            for item in items:
                                text = item.get_text(strip=True)
                                if text and text not in lineup_data["away"]:
                                    lineup_data["away"].append(text)

                    if len(lineup_data["home"]) > 6:
                        lineup_data["home"] = lineup_data["home"][:6]
                    if len(lineup_data["away"]) > 6:
                        lineup_data["away"] = lineup_data["away"][:6]
                except Exception as e:
                    print(f"  - 라인업 성향 파싱 예외 ({m_id}): {e}")

                # ==========================================
                # 6. 경기 일정 (홈/원정 영역 완벽 분리 수집)
                # ==========================================
                fixtures_data = {"home": [], "away": []}
                try:
                    futer_div = detail_soup.find("div", id="dv_futer")
                    if futer_div:
                        home_div = futer_div.find("div", class_="home-div")
                        if home_div:
                            for c_item in home_div.find_all("li", class_="courselis"):
                                league = c_item.find("div", class_="team")
                                time_span = c_item.find("span", {"name": "timeData"})
                                teams = c_item.find("div", class_="corteam")
                                interval = c_item.find("div", class_="interval")
                                
                                match_info = {
                                    "league": league.get_text(strip=True) if league else "",
                                    "match_time": time_span["data-t"] if time_span and time_span.has_attr("data-t") else (time_span.get_text(strip=True) if time_span else ""),
                                    "teams": teams.get_text(separator=" vs ", strip=True) if teams else "",
                                    "interval": interval.get_text(strip=True) if interval else ""
                                }
                                if match_info["teams"] and match_info not in fixtures_data["home"]:
                                    fixtures_data["home"].append(match_info)

                        guest_div = futer_div.find("div", class_="guest-div")
                        if guest_div:
                            for c_item in guest_div.find_all("li", class_="courselis"):
                                league = c_item.find("div", class_="team")
                                time_span = c_item.find("span", {"name": "timeData"})
                                teams = c_item.find("div", class_="corteam")
                                interval = c_item.find("div", class_="interval")
                                
                                match_info = {
                                    "league": league.get_text(strip=True) if league else "",
                                    "match_time": time_span["data-t"] if time_span and time_span.has_attr("data-t") else (time_span.get_text(strip=True) if time_span else ""),
                                    "teams": teams.get_text(separator=" vs ", strip=True) if teams else "",
                                    "interval": interval.get_text(strip=True) if interval else ""
                                }
                                if match_info["teams"] and match_info not in fixtures_data["away"]:
                                    fixtures_data["away"].append(match_info)
                except Exception as e:
                    print(f"  - 경기일정 파싱 예외 ({m_id}): {e}")

                # ==========================================
                # 7. 결장자 수집 (정밀 타격)
                # ==========================================
                absent_players = {"home": [], "away": []}
                try:
                    absent_section = detail_soup.find("div", class_="absent-box") or detail_soup.find("ul", class_="lineupbox")
                    if absent_section:
                        home_absents = absent_section.find_all("div", class_="home")
                        for ha in home_absents:
                            players = ha.find_all("div", class_="player")
                            for p in players:
                                name = p.get_text(strip=True)
                                if name and name not in absent_players["home"]:
                                    absent_players["home"].append(name)
                        
                        away_absents = absent_section.find_all("div", class_="guest")
                        for aa in away_absents:
                            players = aa.find_all("div", class_="player")
                            for p in players:
                                name = p.get_text(strip=True)
                                if name and name not in absent_players["away"]:
                                    absent_players["away"].append(name)
                except Exception as e:
                    print(f"  - 결장자 파싱 예외 ({m_id}): {e}")

                # 최종 구조 결합
                match_details[m_id] = {
                    "match_code": m_id,
                    "head_info": head_info,
                    "home": target["home"],
                    "away": target["away"],
                    "meta_details": {
                        "rankings": rankings_data,
                        "recent_form": recent_form,
                        "h2h": h2h_data,
                        "lineup_summary": lineup_data,
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
            
        print(f"\n🎉 성공: 총 {counter - 1}개 경기의 모든 정밀 데이터가 깔끔하게 동기화되었습니다!")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler()
