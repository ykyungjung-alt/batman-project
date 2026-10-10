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
            detail_url = f"url?id=5match/data-{m_id}"
            
            try:
                driver.get(detail_url)
                time.sleep(0.8)
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # ==========================================
                # 1. 헤드 정보 독립 분류 (리그, 라운드, 시간, 구장, 날씨) - 누락 방지 보완
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
                            head_info["league"] = parts[0].replace("·", "").strip()
                            head_info["round"] = "라운드 " + parts[1].strip()
                        else:
                            head_info["league"] = full_text.replace("·", "").strip()
                    
                    if not head_info["round"]:
                        for span_tag in detail_soup.find_all("span"):
                            txt = span_tag.get_text(strip=True)
                            if "라운드" in txt:
                                head_info["round"] = txt
                                break
                    
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
                        stadium_candidates = []
                        for s in spans:
                            s_text = s.get_text(strip=True)
                            if not s_text or "생중계" in s_text:
                                continue
                            if any(w in s_text for w in ["°C", "비", "맑음", "구름", "이슬비", "눈", "흐림"]):
                                head_info["weather"] = s_text
                            else:
                                stadium_candidates.append(s_text)
                        if stadium_candidates:
                            head_info["stadium"] = stadium_candidates[0]
                except Exception as e:
                    print(f"  - 헤드 정보 파싱 예외 ({m_id}): {e}")

                # ==========================================
                # 2. 리그전적 ('전체' 전적 관련 행만 정밀 타격 수집)
                # ==========================================
                rankings_data = []
                seen_rankings = set()
                try:
                    standings_div = detail_soup.find("div", id="dv_league_standings")
                    target_tables = [standings_div] if standings_div else detail_soup.find_all("table", class_=["team-table-home", "team-table-guest"])
                    
                    for t_box in target_tables:
                        standing_rows = t_box.find_all("tr", class_=["tr_h_standing", "tr_a_standing"]) if t_box else []
                        for s_row in standing_rows:
                            row_id = s_row.get("id", "")
                            
                            if "_ht_" in row_id:
                                continue
                                
                            cols = [c.get_text(strip=True) for c in s_row.find_all(["th", "td"])]
                            if len(cols) >= 10:
                                row_class = " ".join(s_row.get("class", []))
                                
                                if "tr_h_standing" in row_class or "home" in row_id:
                                    team_type = "홈팀 리그전적"
                                else:
                                    team_type = "원정팀 리그전적"
                                
                                sub_category = "최근전적"

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
                # 3. 맞대결 전적 (dv_hth_count 내부의 승무패 통계 및 상세 경기 목록 정밀 타격)
                # ==========================================
                h2h_data = {"home_summary": {}, "away_summary": {}, "matches": []}
                try:
                    h2h_div = detail_soup.find("div", id="dv_head_to_head")
                    if h2h_div:
                        # 💡 상단 체크박스 필터 탭들을 완전히 무시하고 오직 dv_hth_count 영역 내부만 타격
                        hth_count_div = h2h_div.find("div", id="dv_hth_count")
                        target_h2h_vote_area = hth_count_div if hth_count_div else h2h_div
                        
                        vote_divs = target_h2h_vote_area.find_all("div", class_="vote")
                        for v in vote_divs:
                            # ext 클래스를 가진 요소를 직접 타격하여 홈승, 무승부, 원정승 수치만 정확히 추출
                            ext_els = v.find_all("div", class_=["ext", "win-f", "draw-f", "lose-f"])
                            if len(ext_els) >= 3:
                                h2h_data["home_summary"]["record_summary"] = ext_els[0].get_text(strip=True) # 홈 승리 및 퍼센트
                                h2h_data["away_summary"]["record_summary"] = ext_els[2].get_text(strip=True) # 원정 승리 및 퍼센트
                            elif len(ext_els) == 1:
                                # 만약 단일 구조일 경우 대비용 방어 코드
                                pass

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
                # 4. 최근전적 (dv_recent_stats 내부의 순수 통계 3개 블록만 엄격 타격)
                # ==========================================
                recent_form = {"home_summary": {}, "away_summary": {}, "matches": []}
                try:
                    recent_div = detail_soup.find("div", id="dv_recent")
                    if recent_div:
                        stats_div = recent_div.find("div", id="dv_recent_stats")
                        if stats_div:
                            valid_votes = []
                            for v in stats_div.find_all("div", class_="vote"):
                                c_list = v.get("class", [])
                                if "text" in c_list:
                                    continue
                                text_content = v.get_text()
                                if any(k in text_content for k in ["최근전적", "경기당 득점", "경기당 실점"]):
                                    valid_votes.append(v)
                            
                            for v in valid_votes:
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
                # 7. 결장자 수집 (hurtLineup ID 탭 내부 정밀 타격)
                # ==========================================
                absent_players = {"home": [], "away": []}
                try:
                    hurt_div = detail_soup.find("div", id="hurtLineup")
                    if hurt_div:
                        lineupbox = hurt_div.find("ul", class_="lineupbox")
                        if lineupbox:
                            rows = lineupbox.find_all("li", class_="lineupis")
                            for row in rows:
                                home_div = row.find("div", class_="home")
                                if home_div:
                                    player_div = home_div.find("div", class_="player")
                                    if player_div:
                                        p_name = player_div.get_text(strip=True)
                                        if p_name and p_name not in absent_players["home"]:
                                            absent_players["home"].append(p_name)
                                
                                guest_div = row.find("div", class_="guest")
                                if guest_div:
                                    player_div = guest_div.find("div", class_="player")
                                    if player_div:
                                        p_name = player_div.get_text(strip=True)
                                        if p_name and p_name not in absent_players["away"]:
                                            absent_players["away"].append(p_name)
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
            
        print(f"\n🎉 성공: 총 {counter - 1}개 경기의 맞대결 요약 및 모든 데이터가 완벽하게 정제되었습니다!")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler()
