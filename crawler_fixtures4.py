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

# 1. 리그명 추출 모듈
def extract_league_name(soup, league_id):
    title_elem = soup.select_one("div#title, div.title, .league_title, h4, strong")
    if title_elem:
        txt = title_elem.text.strip()
        if txt:
            return txt.replace("라이브스코어", "").replace("시즌", "").strip()
    return f"리그 ID {league_id}"

# 2. 활성 라운드 및 총 라운드 추출 모듈
def extract_rounds(soup, league_id):
    default_total = 46 if league_id == 39 else 38
    active_elem = soup.select_one("div.round span.current.on, div.round span.on")
    active_text = "1"
    
    if active_elem:
        active_text = active_elem.get("round", "").strip()
        if not active_text.isdigit():
            active_text = active_elem.text.strip()

    all_rounds = soup.select("div.round span[round]")
    total_cnt = len(all_rounds) if all_rounds else default_total
    return f"{active_text}/{total_cnt}", total_cnt

# 3. 하단 컬러 범례(Standing Legends) 추출 모듈
def extract_legends(soup):
    legend_items = soup.select("#standingColor span.explain, div#standingColor span.explain")
    color_to_label = {}
    parsed_legends = []
    
    for lg in legend_items:
        color_i = lg.select_one("i")
        desc_span = lg.select_one("span")
        if color_i:
            bg_style = color_i.get("style", "")
            bg_color = ""
            if "background-color:" in bg_style:
                try:
                    bg_color = bg_style.split("background-color:")[1].split(";")[0].strip().upper()
                except:
                    pass
            desc_text = desc_span.text.strip() if desc_span else lg.text.strip()
            if bg_color:
                color_to_label[bg_color] = desc_text
            parsed_legends.append({"color": bg_color, "description": desc_text})
            
    return parsed_legends, color_to_label

# 4. 랭킹표 및 컬러 꼬리표(tag_color, tag_label) 매핑 모듈
def extract_standings(soup, color_to_label):
    parsed_standings = []
    seen_teams = set()
    
    # li.standis 구조 기반 파싱 (동적 생성된 랭킹 리스트 타격)
    standing_rows = soup.select('li.standis')
    
    for row in standing_rows:
        style_attr = row.get("style", "")
        tag_color = ""
        if "--tagcolor:" in style_attr:
            try:
                tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
            except:
                pass

        tokens = [t.strip() for t in row.text.split() if t.strip()]
        
        if tokens and tokens[0].isdigit():
            rank_val = tokens[0]
            rank_int = int(rank_val)
            
            if 1 <= rank_int <= 25 and len(tokens) >= 8:
                team_val = tokens[1]
                
                if team_val in ["구단", "PTS", "순위", "승점"] or any(k in team_val for k in ["승점", "득실"]):
                    continue
                    
                stats = tokens[-6:] # [경기수, 승, 무, 패, 득실, 승점]
                
                if stats[0].isdigit() and stats[-1].isdigit():
                    if team_val not in seen_teams:
                        seen_teams.add(team_val)
                        tag_label = color_to_label.get(tag_color, "일반")

                        parsed_standings.append({
                            "rank": rank_val,
                            "team": team_val,
                            "tag_color": tag_color,
                            "tag_label": tag_label,
                            "경기수": stats[0],
                            "승": stats[1],
                            "무": stats[2],
                            "패": stats[3],
                            "득실": stats[4],
                            "승점": stats[5]
                        })

    # 백업: 혹시 li 구조가 안 잡힐 경우 table 구조 탐색
    if not parsed_standings:
        for tbl in soup.select('table'):
            for row in tbl.select('tr'):
                cells = [c.text.strip() for c in row.select('td, th') if c.text.strip()]
                if len(cells) >= 8 and cells[0].isdigit():
                    rank_val = cells[0]
                    if 1 <= int(rank_val) <= 25:
                        team_val = cells[1]
                        if team_val in ["구단", "PTS", "순위", "승점"]:
                            continue
                        stats = cells[-6:]
                        if stats[0].isdigit() and stats[-1].isdigit():
                            if team_val not in seen_teams:
                                seen_teams.add(team_val)
                                parsed_standings.append({
                                    "rank": rank_val,
                                    "team": team_val,
                                    "tag_color": "",
                                    "tag_label": color_to_label.get("", "일반"),
                                    "경기수": stats[0],
                                    "승": stats[1],
                                    "무": stats[2],
                                    "패": stats[3],
                                    "득실": stats[4],
                                    "승점": stats[5]
                                })

    parsed_standings.sort(key=lambda x: int(x['rank']))
    return parsed_standings

# 5. 메인 실행 및 제어 함수
def run_crawler_v4():
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    # 실제 스코어맨 도메인 URL 설정
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

            league_match_data = {
                "league_id": league_id,
                "league_name": f"리그 ID {league_id}",
                "active_round": "1/38",
                "total_rounds": 38,
                "standing_legends": [],
                "standings": []
            }

            try:
                driver.get(url)
                
                # 💡 동적 렌더링되는 랭킹 리스트(li.standis)가 나타날 때까지 확실하게 대기
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.standis"))
                )
                time.sleep(2)

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # 모듈 함수들을 순서대로 호출하여 데이터 적재
                league_match_data["league_name"] = extract_league_name(soup, league_id)
                
                active_str, total_cnt = extract_rounds(soup, league_id)
                league_match_data["active_round"] = active_str
                league_match_data["total_rounds"] = total_cnt
                
                legends, color_map = extract_legends(soup)
                league_match_data["standing_legends"] = legends
                
                league_match_data["standings"] = extract_standings(soup, color_map)

                print(f"✅ 수집 성공: {league_match_data['league_name']} (라운드: {league_match_data['active_round']}, 범례: {len(legends)}개, 순위 팀: {len(league_match_data['standings'])}개)")

            except Exception as e:
                print(f"⚠️ 리그 ID {league_id} 수집 중 예외 발생: {e}")

            all_leagues_data["leagues"][str(league_id)] = league_match_data

    finally:
        if driver:
            driver.quit()

    with open("match_details_v4.json", "w", encoding="utf-8") as f:
        json.dump(all_leagues_data, f, ensure_ascii=False, indent=4)
    print("🎉 match_details_v4.json 저장 완료")

if __name__ == "__main__":
    run_crawler_v4()
