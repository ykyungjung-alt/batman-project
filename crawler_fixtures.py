from datetime import datetime, timedelta
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from zoneinfo import ZoneInfo

def collect_match_details():
    # 1. 기존 메인 일정 파일 로드
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            main_data = json.load(f)
    except FileNotFoundError:
        print("❌ data.json 파일이 없습니다. 메인 일정 수집기(crawler_fixtures.py)를 먼저 실행해주세요.")
        return

    # 2. 크롬 옵션 설정 (타임존 KST 고정)
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    options.add_argument("--lang=ko_KR")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "Asia/Seoul"})
    except Exception as e:
        print(f"⚠️ 타임존 에뮬레이션 설정 경고: {e}")

    kst = ZoneInfo("Asia/Seoul")
    today_kst = datetime.now(kst).strftime("%m-%d")
    tomorrow_kst = (datetime.now(kst) + timedelta(days=1)).strftime("%m-%d")

    detailed_matches = {}

    try:
        print("[시작] 오늘 및 내일 경기 상세 메타 정보 수집 중...")
        
        for date_key, matches in main_data.get("daily_matches", {}).items():
            # 오늘 또는 내일 날짜 키만 선별
            if not (today_kst in date_key or tomorrow_kst in date_key):
                continue
                
            detailed_matches[date_key] = []
            
            for match in matches:
                match_id = match.get("match_id")
                if not match_id:
                    detailed_matches[date_key].append(match)
                    continue
                
                detail_url = f"https://www.scoreman123.com/match/data-{match_id}"
                print(f"  🔍 상세 수집 중: {match['home']} vs {match['away']} (ID: {match_id})")
                
                try:
                    driver.get(detail_url)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    
                    # 1. 기본 정보, 라운드, 일시, 구장 파싱
                    round_info = ""
                    match_datetime = ""
                    stadium = ""
                    
                    # 상단 헤더 영역 탐색 (예: 라운드 5, 2026.10.10 03:30, Signal Iduna Park)
                    header_div = soup.find(text=re.compile("라운드"))
                    if header_div:
                        parent_text = header_div.parent.get_text(" ", strip=True)
                        round_info = parent_text
                    
                    # 구장명은 보통  아이콘 뒤나 특정 클래스/텍스트에 위치
                    for el in soup.find_all(text=True):
                        txt = el.strip()
                        if "Park" in txt or "Arena" in txt or "Stadium" in txt:
                            if len(txt) < 30:
                                stadium = txt
                                break

                    # 2. 팀 순위 파싱 (팀순위 테이블 추출)
                    rankings = []
                    ranking_table = soup.find("div", id=lambda x: x and "팀순위" in str(x)) or soup.find(text=re.compile("팀순위"))
                    if ranking_table:
                        # 테이블 행(tr)을 찾아 홈/원정 순위 정보 추출
                        table = soup.find("table") # 실제 구조에 맞춰 테이블 탐색
                        rows = soup.find_all("tr")
                        for r in rows:
                            cells = [td.get_text(strip=True) for td in r.find_all(["th", "td"])]
                            if len(cells) >= 10 and (match['home'] in cells[1] or match['away'] in cells[1]):
                                rankings.append({
                                    "rank": cells[0],
                                    "team": cells[1],
                                    "played": cells[2],
                                    "win": cells[3],
                                    "draw": cells[4],
                                    "lose": cells[5],
                                    "gf": cells[6],
                                    "ga": cells[7],
                                    "gd": cells[8],
                                    "pts": cells[9]
                                })

                    # 3. 라인업 (결장자 정보) 파싱
                    absent_players = {"home": [], "away": []}
                    lineup_header = soup.find(text=re.compile("라인업"))
                    if lineup_header:
                        # 결장자 마크( 등)가 포함된 부근의 선수 행 추출
                        lineup_container = lineup_header.find_parent("div")
                        if lineup_container:
                            player_rows = lineup_container.find_all("tr") or lineup_container.find_all("li")
                            for pr in player_rows:
                                p_text = pr.get_text(" ", strip=True)
                                if "" in p_text or "결장" in p_text:
                                    # 홈/원정 구분하여 적재
                                    absent_players["home"].append(p_text)

                    # 4. 상대전적 및 최근전적 요약 파싱
                    h2h_summary = ""
                    h2h_sec = soup.find(text=re.compile("상대전적"))
                    if h2h_sec:
                        parent_el = h2h_sec.find_parent()
                        if parent_el:
                            h2h_summary = parent_el.get_text(" ", strip=True)

                    recent_summary = ""
                    recent_sec = soup.find(text=re.compile("최근전적"))
                    if recent_sec:
                        parent_el = recent_sec.find_parent()
                        if parent_el:
                            recent_summary = parent_el.get_text(" ", strip=True)

                    # 최종 메타 데이터 딕셔너리 병합
                    meta_info = {
                        "stadium": stadium,
                        "round_info": round_info,
                        "rankings": rankings,
                        "absent_players": absent_players,
                        "h2h_summary": h2h_summary,
                        "recent_summary": recent_summary
                    }
                    
                    match["meta_details"] = meta_info
                    detailed_matches[date_key].append(match)
                    
                except Exception as e:
                    print(f"    ⚠️ 상세 데이터 수집 실패 (ID: {match_id}): {e}")
                    detailed_matches[date_key].append(match)
                    
    except Exception as e:
        print(f"❌ 상세 크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()

    # 결과 저장 (match_details.json 파일로 분리 저장)
    output_data = {
        "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
        "daily_matches": detailed_matches
    }
    
    with open("match_details.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("\n🎉 오늘/내일 경기 심층 메타 정보(`match_details.json`) 저장 완료!")

if __name__ == "__main__":
    collect_match_details()
