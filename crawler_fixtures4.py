import json
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

    # 수집 대상 리그 주소 설정
    target_leagues = [
        {"id": 34, "url": "url?id=42league/34"},
        {"id": 39, "url": "url?id=42league/39"},
        {"id": 40, "url": "url?id=42league/40"}
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

            # 리그별 기본 총 라운드 설정 (기본값 38, 리그 39는 46)
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
                
                # 페이지 내 라운드 영역 로딩 대기
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
                active_elem = soup.select_one("div.round span.current.on, div.round span.on, span.current.on")
                active_text = "1"
                
                if active_elem:
                    active_text = active_elem.get("round", "").strip()
                    if not active_text.isdigit():
                        active_text = active_elem.text.strip()

                all_rounds = soup.select("div.round span[round]")
                total_cnt = len(all_rounds) if all_rounds else default_total_rounds
                
                league_match_data["total_rounds"] = total_cnt
                league_match_data["active_round"] = f"{active_text}/{total_cnt}"

                # 3. 💡 [팀순위 정밀 파싱] <table> 구조의 셀(td, th)을 직접 추출하여 팀명 공백 밀림 현상 원천 차단
                parsed_standings = []
                seen_teams = set()
                
                # '팀순위' 키워드 근처의 테이블을 우선 탐색 후, 전체 테이블 스캔
                target_table = None
                for tag in soup.find_all(['h3', 'h4', 'div', 'strong', 'th']):
                    if '팀순위' in tag.text:
                        nxt = tag.find_next('table')
                        if nxt:
                            target_table = nxt
                            break

                tables_to_check = [target_table] if target_table else []
                for tbl in soup.select('table'):
                    if tbl not in tables_to_check:
                        tables_to_check.append(tbl)

                for tbl in tables_to_check:
                    if not tbl:
                        continue
                    for row in tbl.select('tr'):
                        cells = [c.text.strip() for c in row.select('td, th') if c.text.strip()]
                        
                        # [순위, 구단, P, W, D, L, GD, PTS] 등 최소 8개 이상의 셀이 존재하고 첫 셀이 숫자인 행
                        if len(cells) >= 8 and cells[0].isdigit():
                            rank_val = cells[0]
                            if int(rank_val) > 25:
                                continue
                                
                            team_val = cells[1]
                            if team_val in ["구단", "PTS", "순위", "승점"] or any(k in team_val for k in ["승점", "득실"]):
                                continue
                                
                            # 뒤에서 6개 셀은 항상 [경기수, 승, 무, 패, 득실, 승점] 순서로 고정됨
                            stats = cells[-6:]
                            
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
                    if parsed_standings:
                        break # 순위 데이터를 성공적으로 추출했으면 탈출

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
