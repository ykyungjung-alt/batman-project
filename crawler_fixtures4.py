import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def run_crawler_v4():
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    
    # 💡 헤드리스 크롬 옵션 설정
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    # 실제 스코어맨 리그별 URL 주소 설정
    target_leagues = [
        {"id": 34, "url": "https://football.scoreman123.com/league/34"},
        {"id": 39, "url": "https://football.scoreman123.com/league/39"},
        {"id": 40, "url": "https://football.scoreman123.com/league/40"}
    ]

    all_leagues_data = {
        "updated_at": now_kst,
        "leagues": {}
    }

    driver = None
    try:
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception:
            driver = webdriver.Chrome(options=options)

        for league in target_leagues:
            league_id = league["id"]
            url = league["url"]
            print(f"🔄 [수집 중] 리그 ID {league_id} ({url})")

            default_total_rounds = 46 if league_id == 39 else 38

            league_match_data = {
                "league_id": league_id,
                "league_name": f"리그 ID {league_id}",
                "active_round": f"1/{default_total_rounds}",
                "total_rounds": default_total_rounds,
                "standings": []
            }

            try:
                driver.get(url)
                
                # 💡 페이지 재접속 및 렌더링 안정화를 위한 타임슬립 (3초)
                time.sleep(3)
                
                # 라운드 영역이 렌더링될 때까지 대기
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.round"))
                )

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # 1. 리그명 추출
                title_elem = soup.select_one("div#title, div.title, .league_title, h4, strong")
                if title_elem:
                    txt = title_elem.text.strip()
                    if txt:
                        league_match_data["league_name"] = txt.replace("라이브스코어", "").replace("시즌", "").strip()

                # 2. 현재 라운드(Active Round) 및 총 라운드 수 추출
                active_elem = soup.select_one("div.round span.current.on, div.round span.on")
                active_text = "1"
                
                if active_elem:
                    active_text = active_elem.get("round", "").strip()
                    if not active_text.isdigit():
                        active_text = active_elem.text.strip()

                all_rounds = soup.select("div.round span[round]")
                total_cnt = len(all_rounds) if all_rounds else default_total_rounds
                
                league_match_data["total_rounds"] = total_cnt
                league_match_data["active_round"] = f"{active_text}/{total_cnt}"

                # 3. 팀순위 데이터 추출 (테이블 셀 방식 + 행 토큰 방식 이중 검증)
                parsed_standings = []
                seen_teams = set()
                
                # 1차 시도: 표준 테이블(table -> tr -> td/th) 구조 정밀 파싱
                for tbl in soup.select('table'):
                    for row in tbl.select('tr'):
                        cells = [c.text.strip() for c in row.select('td, th') if c.text.strip()]
                        
                        if len(cells) >= 8 and cells[0].isdigit():
                            rank_val = cells[0]
                            rank_int = int(rank_val)
                            if 1 <= rank_int <= 25:
                                team_val = cells[1]
                                if team_val in ["구단", "PTS", "순위", "승점"] or any(k in team_val for k in ["승점", "득실"]):
                                    continue
                                
                                stats = cells[-6:] # [경기수, 승, 무, 패, 득실, 승점]
                                if stats[0].isdigit() and stats[-1].isdigit():
                                    if team_val not in seen_teams:
                                        seen_teams.add(team_val)
                                        parsed_standings.append({
                                            "rank": rank_val,
                                            "team": team_val,
                                            "경기수": stats[0],
                                            "승": stats[1],
                                            "무": stats[2],
                                            "패": stats[3],
                                            "득실": stats[4],
                                            "승점": stats[5]
                                        })

                # 2차 시도: 테이블에서 못 찾았을 경우 tr, li 요소 토큰 스캔 방식으로 백업 수집
                if not parsed_standings:
                    for row in soup.select('tr, li'):
                        if row.find_all(['tr', 'li']):
                            continue
                            
                        tokens = [t.strip() for t in row.text.split() if t.strip()]
                        
                        if tokens and tokens[0].isdigit():
                            rank = int(tokens[0])
                            if 1 <= rank <= 25 and len(tokens) >= 8:
                                team = tokens[1]
                                
                                if team in ["구단", "PTS", "순위", "승점"] or any(k in team for k in ["승점", "득실"]):
                                    continue
                                    
                                stats = tokens[-6:]
                                
                                if stats[0].isdigit() and stats[-1].isdigit():
                                    if team not in seen_teams:
                                        seen_teams.add(team)
                                        parsed_standings.append({
                                            "rank": str(rank),
                                            "team": team,
                                            "경기수": stats[0],
                                            "승": stats[1],
                                            "무": stats[2],
                                            "패": stats[3],
                                            "득실": stats[4],
                                            "승점": stats[5]
                                        })

                parsed_standings.sort(key=lambda x: int(x['rank']))
                league_match_data["standings"] = parsed_standings
                print(f"✅ 수집 성공: {league_match_data['league_name']} (라운드: {league_match_data['active_round']}, 팀 수: {len(parsed_standings)}개)")

            except Exception as e:
                print(f"⚠️ 리그 ID {league_id} 수집 중 예외 발생: {e}")

            all_leagues_data["leagues"][str(league_id)] = league_match_data

    finally:
        if driver:
            driver.quit()

    # 결과 파일 저장
    with open("match_details_v4.json", "w", encoding="utf-8") as f:
        json.dump(all_leagues_data, f, ensure_ascii=False, indent=4)
    print("🎉 match_details_v4.json 저장 완료")

if __name__ == "__main__":
    run_crawler_v4()
