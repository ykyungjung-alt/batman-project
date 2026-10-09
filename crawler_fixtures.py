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

BASE_URL = "https://www.scoreman123.com/football/fixture"

MAJOR_LEAGUES = [
    "K리그1", "K리그 2", 
    "프리미어리그", "잉글랜드 프리미어리그", "세리에 A", "라리가", "분데스리가", "리그 1", "프랑스 리그 1",
    "에레디비시", "메이저 리그 사커", "라리가2", "챔피언쉽", "잉글랜드 챔피언쉽",
    "챔피언스리그", "유로파리그", "유로파 컨퍼런스리그", 
    "AFC챔피언스리그", "AFC 챔피언스리그2", "ASEAN 클럽선수권",
    "FIFA", "월드컵", "아시안컵", "네이션스리그", 
    "아시안게임", "올림픽", "국제 친선경기", 
    "U-23", "U-21", "U-20", "U-17",
    "잉글랜드 FA 컵", "EFL 트로피"
]

def run_optimized_crawler():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    options.add_argument("--lang=ko_KR")
    
    kst = ZoneInfo("Asia/Seoul")
    today_kst = datetime.now(kst)
    tomorrow_kst = today_kst + timedelta(days=1)
    
    target_dates_str = [
        today_kst.strftime("%m-%d"),
        tomorrow_kst.strftime("%m-%d")
    ]
    
    driver = webdriver.Chrome(options=options)
    try:
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "Asia/Seoul"})
    except Exception:
        pass

    daily_matches = {d: [] for d in target_dates_str}
    
    try:
        print(f"🌐 메인 일정 페이지 접속 중: {BASE_URL}")
        driver.get(BASE_URL)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 메인 대진표에서 주요 리그 경기의 Match ID 및 기본 정보 수집
        current_league = ""
        rows = soup.find_all("tr")
        match_targets = []
        
        for row in rows:
            text_content = row.get_text(strip=True)
            if not text_content:
                continue
            
            # 리그명 감지
            if not re.search(r"\d{2}:\d{2}", text_content):
                cleaned = re.sub(r"^[^\w\s]+", "", text_content).replace("+", "").strip()
                cleaned = re.sub(r"경기수\s*\(.*?\)", "", cleaned).strip()
                if 1 < len(cleaned) < 35 and "시간" not in cleaned and "상태" not in cleaned:
                    current_league = cleaned
                continue
            
            # 주요 리그 필터링 (MAJOR_LEAGUES 적용으로 용량 및 부하 원천 차단)
            is_major = any(ml in current_league for ml in MAJOR_LEAGUES)
            if not is_major:
                continue
            
            # Match ID 추출 (tr 태그 id 또는 onclick 분석 함수)
            row_id = row.get("id", "")
            m_match = re.search(r'tr1_(\d+)', row_id)
            m_id = None
            if m_match:
                m_id = m_match.group(1)
            else:
                onclick_attr = row.get("onclick", "")
                if not onclick_attr:
                    td = row.find("td", onclick=True)
                    if td:
                        onclick_attr = td.get("onclick", "")
                sub_match = re.search(r'analysis\((\d+)', onclick_attr)
                if sub_match:
                    m_id = sub_match.group(1)
            
            if m_id:
                match_targets.append({
                    "id": m_id,
                    "league": current_league
                })

        print(f"⚽ 주요 리그 대상 수집된 경기 후보: {len(match_targets)}개")
        
        match_counter = 1
        for target in match_targets:
            m_id = target["id"]
            league_name = target["league"]
            detail_url = f"https://www.scoreman123.com/match/data-{m_id}"
            
            try:
                driver.get(detail_url)
                time.sleep(0.8) # 부하 방지 딜레이
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # 날짜 및 시간 추출
                date_str = today_kst.strftime("%m-%d")
                time_str = "00:00"
                date_time_match = re.search(r'(\d{4}\.\d{2}\.\d{2})\s+(\d{2}:\d{2})', detail_soup.get_text())
                if date_time_match:
                    full_date_str = date_time_match.group(1)
                    time_str = date_time_match.group(2)
                    try:
                        dt_obj = datetime.strptime(full_date_str, "%Y.%m.%d")
                        date_str = dt_obj.strftime("%m-%d")
                    except Exception:
                        pass
                
                # 오늘/내일 경기만 엄선
                if date_str not in target_dates_str:
                    continue
                
                # 홈/원정 팀명 추출
                header_el = detail_soup.find("h4")
                header_text = header_el.get_text(strip=True) if header_el else ""
                home_team = "홈팀"
                away_team = "원정팀"
                if header_text and ("vs" in header_text.lower() or "VS" in header_text):
                    parts = re.split(r'vs|VS', header_text)
                    if len(parts) >= 2:
                        home_team = parts[0].strip()
                        away_team = re.split(r'라이브스코어|경기분석', parts[1])[0].strip()

                # 1. 팀 순위 정보 수집 (순위, 경기수, 승, 무, 패, 득점, 실점, 득실, 승점)
                rankings_data = []
                try:
                    tables = detail_soup.find_all("table")
                    for t in tables:
                        headers = [th.get_text(strip=True) for th in t.find_all(["th", "td"])[:10]]
                        if "승점" in "".join(headers) or "승" in headers:
                            rows_list = t.find_all("tr")
                            if len(rows_list) > 1:
                                for r_row in rows_list[1:]:
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
                except Exception:
                    pass

                # 2. 최근전적 수집
                recent_form = {"matches": []}
                try:
                    recent_section = detail_soup.find(text=re.compile("최근전적"))
                    if recent_section:
                        parent_div = recent_section.find_parent("div")
                        if parent_div:
                            for r_row in parent_div.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in r_row.find_all(["th", "td"])]
                                if len(cols) >= 4:
                                    recent_form["matches"].append({
                                        "info": " | ".join(cols[:6])
                                    })
                except Exception:
                    pass

                # 3. 상대전적 수집
                h2h_data = {"matches": []}
                try:
                    h2h_section = detail_soup.find(text=re.compile("상대전적"))
                    if h2h_section:
                        h2h_parent = h2h_section.find_parent("div")
                        if h2h_parent:
                            for h_row in h2h_parent.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"])]
                                if len(cols) >= 4:
                                    h2h_data["matches"].append({
                                        "info": " | ".join(cols[:6])
                                    })
                except Exception:
                    pass

                # 4. 결장자 정보 수집
                absent_players = {"home": [], "away": []}
                try:
                    lineup_section = detail_soup.find(text=re.compile("라인업"))
                    if lineup_section:
                        l_parent = lineup_section.find_parent("div")
                        if l_parent:
                            for li_row in l_parent.find_all("tr"):
                                player_texts = [p.get_text(strip=True) for p in li_row.find_all("td") if p.get_text(strip=True)]
                                if len(player_texts) >= 1:
                                    absent_players["home"].append(player_texts[0])
                                if len(player_texts) >= 2:
                                    absent_players["away"].append(player_texts[-1])
                except Exception:
                    pass

                match_item = {
                    "id": match_counter,
                    "match_code": m_id,
                    "league": league_name,
                    "time": time_str,
                    "home": home_team,
                    "away": away_team,
                    "score": "-",
                    "meta_details": {
                        "rankings": rankings_data,
                        "recent_form": recent_form,
                        "h2h": h2h_data,
                        "absent_players": absent_players
                    }
                }
                
                daily_matches[date_str].append(match_item)
                match_counter += 1
                
            except Exception as e:
                print(f"  ⚠️ 상세 페이지 수집 실패 (ID: {m_id}): {e}")
                continue

        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 주요 리그 오늘/내일 총 {match_counter - 1}개 경기 상세 데이터가 match_details.json에 빌드되었습니다!")

    except Exception as e:
        print(f"❌ 크롤링 에러 발생: {e}")
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump({"last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"), "daily_matches": {}}, f, ensure_ascii=False, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_optimized_crawler()
