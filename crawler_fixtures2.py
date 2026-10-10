from datetime import datetime, timedelta
import json
import time
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from zoneinfo import ZoneInfo

def run_table_based_crawler_v2():
    if not os.path.exists("data.json"):
        print("❌ data.json 파일이 존재하지 않습니다. 먼저 update_data.py를 실행해 주세요.")
        return

    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    target_matches = []
    daily_matches_input = data.get("daily_matches", {})
    
    kst = ZoneInfo("Asia/Seoul")
    today_kst = datetime.now(kst)
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    
    tomorrow_dt = today_kst + timedelta(days=1)
    m_str = tomorrow_dt.strftime("%m")
    d_str = tomorrow_dt.strftime("%d")
    w_str = weekdays[tomorrow_dt.weekday()]
    
    tomorrow_date_key_prefix = f"{m_str}-{d_str} ({w_str})"
    print(f"📅 동적 계산된 내일 날짜 키 패턴: {tomorrow_date_key_prefix}")

    for date_key, matches in daily_matches_input.items():
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
                time.sleep(1.0)
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # ==========================================
                # 1. 헤드 정보 독립 분류
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
                # 2. 팀전적
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
                            if "_ht_" in row_id:
                                continue
                                
                            cols = [c.get_text(strip=True) for c in s_row.find_all(["th", "td"])]
                            if len(cols) >= 10:
                                rank_val = cols[0]
                                team_name = cols[1]
                                
                                if not rank_val or team_name in collected_teams or "홈" in team_name or "원정" in team_name:
                                    continue
                                
                                collected_teams.add(team_name)
                                row_class = " ".join(s_row.get("class", []))
                                team_type = "홈팀 리그전적" if "tr_h_standing" in row_class or "home" in row_id else "원정팀 리그전적"
                                
                                rankings_data.append({
                                    "team_type": team_type,
                                    "sub_category": "최근전적",
                                    "rank": rank_val, 
                                    "team": team_name, 
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
                # 3. 맞대결 전적 (승무패 요약 및 경기당 득점만 수집, 핸디캡/언오버 제외)
                # ==========================================
                h2h_data = {"summary": [], "matches": []}
                try:
                    h2h_div = detail_soup.find("div", id="dv_head_to_head")
                    if h2h_div:
                        hth_count_div = h2h_div.find("div", id="dv_hth_count")
                        target_h2h_vote_area = hth_count_div if hth_count_div else h2h_div
                        
                        vote_divs = target_h2h_vote_area.find_all("div", class_="vote")
                        for v in vote_divs:
                            ext_els = v.find_all("div", class_=["ext", "win-f", "draw-f", "lose-f", "p2"])
                            for el in ext_els:
                                summary_text = el.get_text(strip=True)
                                if summary_text and not any(k in summary_text for k in ["핸디캡", "언오버"]):
                                    if summary_text not in h2h_data["summary"]:
                                        h2h_data["summary"].append(summary_text)

                        h_table = h2h_div.find_next("table")
                        if h_table:
                            for h_row in h_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                if len(cols) >= 3 and not any("득점" in c for c in cols) and not any("날짜" in c for c in cols):
                                    core_cols = cols[:4] if len(cols) >= 4 else cols
                                    h2h_data
