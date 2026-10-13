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
            home_team_name = target["home"]
            detail_url = f"https://www.scoreman123.com/match/data-{m_id}"

            try:
                driver.get(detail_url)
                time.sleep(1.0)
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")

                # ==========================================
                # 1. 헤드 정보 (stadium, home_stadium, weather 수집)
                # ==========================================
                head_info = {
                    "league": target["league"],
                    "round": "",
                    "stadium": "",
                    "home_stadium": "",  # 홈팀 실제 홈구장 수집 필드
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

                    other_info_div = detail_soup.find("div", {"id": "otherInfo"})
                    if other_info_div:
                        spans = other_info_div.find_all("span")
                        stadium_candidates = []
                        for s in spans:
                            s_text = s.get_text(strip=True)
                            if not s_text or "생중계" in s_text:
                                continue
                            if any(w in s_text for w in ["°C", "°F", "비", "맑음", "구름", "이슬비", "눈", "흐림", "Clear", "Rain", "Cloud", "Snow"]):
                                head_info["weather"] = s_text
                            else:
                                stadium_candidates.append(s_text)

                        if stadium_candidates:
                            head_info["stadium"] = stadium_candidates[0]

                    # ------------------------------------------
                    # 1-1. 홈팀 서브페이지 접근하여 실제 홈구장(home_stadium) 수집
                    # ------------------------------------------
                    home_div = detail_soup.find("div", {"class": "home"})
                    if home_div and home_div.has_attr("data-url"):
                        team_summary_url = "https:" + home_div["data-url"]
                        
                        driver.get(team_summary_url)
                        time.sleep(0.8)
                        team_soup = BeautifulSoup(driver.page_source, "html.parser")
                        
                        info_div = team_soup.find("div", id="info")
                        if info_div:
                            stadium_li = info_div.find("li", class_="home-stadium")
                            if stadium_li:
                                h_stadium_name = stadium_li.get("explain", "").strip()
                                if not h_stadium_name:
                                    div_tag = stadium_li.find("div")
                                    if div_tag:
                                        h_stadium_name = div_tag.get_text(strip=True)
                                head_info["home_stadium"] = h_stadium_name

                        # 원래 경기 상세 페이지로 복귀
                        driver.get(detail_url)
                        time.sleep(0.8)
                        detail_soup = BeautifulSoup(driver.page_source, "html.parser")

                except Exception as e:
                    print(f"  - 헤드 및 홈구장 정보 파싱 예외 ({m_id}): {e}")

                # ==========================================
                # 2. 팀전적 (리그 순위 테이블)
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
                                    "win":
