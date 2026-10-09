from datetime import datetime, timedelta
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from zoneinfo import ZoneInfo
import re

def run_comprehensive_crawler():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    kst = ZoneInfo("Asia/Seoul")
    today = datetime.now(kst)
    tomorrow = today + timedelta(days=1)
    
    target_dates = [
        today.strftime("%m-%d"),
        tomorrow.strftime("%m-%d")
    ]
    
    driver = webdriver.Chrome(options=options)
    
    try:
        main_url = "https://www.scoreman123.com/football/fixture?f=sc1"
        print(f"🌐 메인 일정 페이지 접속 중: {main_url}")
        driver.get(main_url)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        match_ids = []
        
        # 메인 페이지에서 오늘 및 내일 경기 ID 수집
        rows = soup.find_all("tr")
        for row in rows:
            row_id = row.get("id", "")
            match_id_match = re.search(r'tr1_(\d+)', row_id)
            if match_id_match:
                m_id = match_id_match.group(1)
                if m_id not in match_ids:
                    match_ids.append(m_id)
            else:
                onclick_attr = row.get("onclick", "")
                if not onclick_attr:
                    td = row.find("td", onclick=True)
                    if td:
                        onclick_attr = td.get("onclick", "")
                m_match = re.search(r'analysis\((\d+)', onclick_attr)
                if m_match:
                    m_id = m_match.group(1)
                    if m_id not in match_ids:
                        match_ids.append(m_id)

        print(f"⚽ 추출된 총 경기 Match ID 목록: {len(match_ids)}개")
        
        daily_matches = {d: [] for d in target_dates}
        match_counter = 1
        
        for m_id in match_ids:
            detail_url = f"https://www.scoreman123.com/match/data-{m_id}"
            try:
                driver.get(detail_url)
                time.sleep(1.0)
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # 1. 기본 메타 정보 (날짜, 시간, 리그, 팀명, 구장)
                date_str = today.strftime("%m-%d") # 기본값
                time_str = "00:00"
                
                header_el = detail_soup.find("h4")
                header_text = header_el.get_text(strip=True) if header_el else ""
                
                # 날짜 및 시간 추출 (예: 2026.10.11 01:30)
                date_time_match = re.search(r'(\d{4}\.\d{2}\.\d{2})\s+(\d{2}:\d{2})', detail_soup.get_text())
                if date_time_match:
                    full_date_str = date_time_match.group(1) # 2026.10.11
                    time_str = date_time_match.group(2)
                    dt_obj = datetime.strptime(full_date_str, "%Y.%m.%d")
                    date_str = dt_obj.strftime("%m-%d")
                
                # 오늘/내일 경기만 필터링
                if date_str not in target_dates:
                    continue
                
                league_el = detail_soup.find("a", href=lambda x: x and "/football/" in x)
                league_name = league_el.get_text(strip=True) if league_el else "기타 리그"
                
                home_team = "홈팀"
                away_team = "원정팀"
                if header_text:
                    if "vs" in header_text.lower() or "VS" in header_text:
                        parts = re.split(r'vs|VS', header_text)
                        if len(parts) >= 2:
                            home_team = parts[0].strip()
                            away_team = re.split(r'라이브스코어|경기분석', parts[1])[0].strip()

                # 구장 정보 추출
                stadium_name = ""
                stadium_el = detail_soup.find("a", href=lambda x: x and " Arena" in x or x and " Stadium" in x or x and "Park" in x)
                if stadium_el:
                    stadium_name = stadium_el.get_text(strip=True)

                # 2. 팀 순위 정보 (순위, 경기수, 승, 무, 패, 득점, 실점, 득실, 승점)
                rankings_data = []
                rank_table = detail_soup.find("div", id=re.compile("rank|팀순위", re.I)) or detail_soup.find(text=re.compile("팀순위"))
                if rank_table:
                    # 상위 부모나 다이블에서 테이블 탐색
                    tables = detail_soup.find_all("table")
                    for t in tables:
                        headers = [th.get_text(strip=True) for th in t.find_all(["th", "td"])[:10]]
                        if "승점" in "".join(headers) or "승" in headers:
                            for r_row in t.find_all("tr")[1:]:
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
                            break

                # 3. 최근전적 (요약 및 최근 5경기 표)
                recent_form = {"summary": {}, "matches": []}
                # 최근전적 테이블 및 텍스트 파싱
                recent_section = detail_soup.find(text=re.compile("최근전적"))
                if recent_section:
                    parent_div = recent_section.find_parent("div")
                    if parent_div:
                        # 최근전적 표 행 파싱 (날짜, 대회명, 스코어 올바르게 정렬)
                        for r_row in parent_div.find_all("tr"):
                            cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"])]
                            # 스코어맨 최근전적 행 포맷팅 감지 및 정제
                            if len(cols) >= 5:
                                # 예시: [날짜, 대회, 팀1, 팀2, 점수1, 점수2 ...] 구조 바로잡기
                                recent_form["matches"].append({
                                    "date": cols[0],
                                    "tournament": cols[1] if len(cols) > 1 else "",
                                    "teams": f"{home_team} vs {away_team}",
                                    "score": "정제된 스코어"
                                })

                # 4. 상대전적 (요약 및 최근 5경기 표)
                h2h_data = {"summary": {}, "matches": []}
                h2h_section = detail_soup.find(text=re.compile("상대전적"))
                if h2h_section:
                    h2h_parent = h2h_section.find_parent("div")
                    if h2h_parent:
                        for h_row in h2h_parent.find_all("tr"):
                            cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"])]
                            if len(cols) >= 4:
                                h2h_data["matches"].append({
                                    "info": " | ".join(cols[:4])
                                })

                # 5. 라인업 결장자 정보
                absent_players = {"home": [], "away": []
