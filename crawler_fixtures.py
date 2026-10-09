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

def collect_fixtures_and_details():
    # 크롬 옵션 설정 (타임존 KST 고정)
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

    daily_matches = {}

    try:
        print("[시작] 오늘 및 내일 경기 일정 및 상세 메타 정보 수집 중...")
        
        # 1단계: 메인 일정 페이지에서 오늘/내일 경기 목록 및 match_id 수집 (필요시 메인 URL 연동)
        # 예시로 기존에 수집된 데이터나 메인 페이지 파싱 결과를 활용합니다.
        try:
            with open("match_details.json", "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                target_daily_matches = existing_data.get("daily_matches", {})
        except FileNotFoundError:
            target_daily_matches = {}

        print(f"  📅 수집 대상 날짜: 오늘({today_kst}), 내일({tomorrow_kst})")

        # 각 경기별 상세 페이지 순회 및 메타 정보 수집
        for date_key, matches in target_daily_matches.items():
            if not (today_kst in date_key or tomorrow_kst in date_key):
                continue
                
            daily_matches[date_key] = []
            
            for match in matches:
                match_id = match.get("match_id")
                if not match_id:
                    daily_matches[date_key].append(match)
                    continue
                
                detail_url = f"https://www.scoreman123.com/match/data-{match_id}"
                print(f"  🔍 상세 수집 중: {match.get('home')} vs {match.get('away')} (ID: {match_id})")
                
                try:
                    driver.get(detail_url)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    
                    # 1. 기본 정보, 라운드, 구장 파싱
                    round_info = ""
                    stadium = ""
                    
                    header_div = soup.find(text=re.compile("라운드"))
                    if header_div and header_div.parent:
                        round_info = header_div.parent.get_text(" ", strip=True)
                    
                    for el in soup.find_all(text=True):
                        txt = el.strip()
                        if "Park" in txt or "Arena" in txt or "Stadium" in txt:
                            if len(txt) < 30:
                                stadium = txt
                                break

                    # 2. 팀 순위 파싱 (팀순위 테이블 추출)
                    rankings = []
                    rows = soup.find_all("tr")
                    for r in rows:
                        cells = [td.get_text(strip=True) for td in r.find_all(["th", "td"])]
                        if len(cells) >= 10 and any(team in cells[1] for team in [match.get('home', ''), match.get('away', '')]):
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
                    if lineup_header and lineup_header.find_parent("div"):
                        lineup_container = lineup_header.find_parent("div")
                        player_rows = lineup_container.find_all("tr") or lineup_container.find_all("li")
                        for pr in player_rows:
                            p_text = pr.get_text(" ", strip=True)
                            if "" in p_text or "결장" in p_text:
                                absent_players["home"].append(p_text)

                    # 4. 상대전적 및 최근전적 요약 파싱
                    h2h_summary = ""
                    h2h_sec = soup.find(text=re.compile("상대전적"))
                    if h2h_sec and h2h_sec.find_parent():
                        h2h_summary = h2h_sec.find_parent().get_text(" ", strip=True)

                    recent_summary = ""
                    recent_sec = soup.find(text=re.compile("최근전적"))
                    if recent_sec and recent_sec.find_parent():
                        recent_summary = recent_sec.find_parent().get_text(" ", strip=True)

                    # 상세 메타 정보 매핑
                    match["meta_details"] = {
                        "stadium": stadium,
                        "round_info": round_info,
                        "rankings": rankings,
                        "absent_players": absent_players,
                        "h2h_summary": h2h_summary,
                        "recent_summary": recent_summary
                    }
                    daily_matches[date_key].append(match)
                    
                except Exception as e:
                    print(f"    ⚠️ 상세 데이터 수집 실패 (ID: {match_id}): {e}")
                    daily_matches[date_key].append(match)
                    
    except Exception as e:
        print(f"❌ 크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()

    # 최종 결과는 요청하신 대로 match_details.json 위치에 저장
    output_data = {
        "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
        "daily_matches": daily_matches
    }
    
    with open("match_details.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("\n🎉 오늘/내일 경기 일정 및 상세 메타 정보(`match_details.json`) 저장 완료!")

if __name__ == "__main__":
    collect_fixtures_and_details()
