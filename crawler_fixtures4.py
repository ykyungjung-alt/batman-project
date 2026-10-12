import json
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

def run_crawler_v4():
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }

    target_leagues = [
        {"id": 34, "url": "https://football.scoreman123.com/league/34"},
        {"id": 39, "url": "https://football.scoreman123.com/league/39"},
        {"id": 40, "url": "https://football.scoreman123.com/league/40"}
    ]

    all_leagues_data = {
        "updated_at": now_kst,
        "leagues": {}
    }

    with requests.Session() as session:
        session.headers.update(headers)

        for league in target_leagues:
            league_id = league["id"]
            url = league["url"]
            print(f"🔄 [수집 중] 리그 ID {league_id}")

            league_match_data = {
                "league_id": league_id,
                "league_name": f"리그 ID {league_id}",
                "active_round": "1/38",
                "total_rounds": 38,
                "standing_legends": [],
                "standings": []
            }

            try:
                res = session.get(url, timeout=10)
                if res.status_code != 200:
                    print(f"⚠️ 요청 실패 (Status Code: {res.status_code})")
                    all_leagues_data["leagues"][str(league_id)] = league_match_data
                    continue

                soup = BeautifulSoup(res.text, 'html.parser')

                # 1. 리그명 정밀 추출
                title_elem = soup.select_one("div#title, div.title, .league_title, h4")
                if title_elem:
                    txt = title_elem.text.strip()
                    if txt:
                        league_match_data["league_name"] = txt.replace("라이브스코어", "").strip()

                # 2. 💡 [이중 방어 Fallback 적용] Active Round 정밀 추출
                active_elem = soup.select_one("div.round span.current.on, span.current.on")
                active_text = "1"
                
                if active_elem:
                    # 1차 시도: round 속성값 가져오기
                    active_text = active_elem.get("round", "").strip()
                    
                    # 2차 시도: 속성값이 없거나 숫자가 아니면 태그 내부 텍스트(예: "6")로 변환 추출
                    if not active_text.isdigit():
                        active_text = active_elem.text.strip()

                # 최종 안전장치: 숫자가 아닐 경우 강제로 "1" 처리
                if not active_text.isdigit():
                    active_text = "1"

                all_rounds = soup.select("div.round span[round]")
                total_cnt = len(all_rounds) if all_rounds else (46 if league_id == 39 else 38)
                
                league_match_data["total_rounds"] = total_cnt
                league_match_data["active_round"] = f"{active_text}/{total_cnt}"

                # 3. 하단 색상 범례(Standing Legends) 수집
                legend_items = soup.select("#standingColor span.explain, .explain")
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
                
                league_match_data["standing_legends"] = parsed_legends

                # 4. '팀순위' 테이블 정밀 타격
                target_table = None
                for tag in soup.find_all(['h3', 'h4', 'div', 'strong']):
                    if '팀순위' in tag.text:
                        nxt = tag.find_next('table')
                        if nxt:
                            target_table = nxt
                            break
                
                if not target_table:
                    for tbl in soup.select('table'):
                        tbl_text = tbl.text
                        if 'PTS' in tbl_text and '구단' in tbl_text:
                            target_table = tbl
                            break

                parsed_standings = []
                if target_table:
                    for row in target_table.select('tr'):
                        cells = row.select('td, th')
                        cell_texts = [c.text.strip() for c in cells if c.text.strip()]
                        
                        # [순위, 구단, P, W, D, L, GD, PTS] (최소 8개 셀, 첫 셀이 숫자)
                        if len(cell_texts) >= 8 and cell_texts[0].isdigit():
                            rank_val = cell_texts[0]
                            team_val = cell_texts[1]
                            stat_slice = cell_texts[-6:] # 경기수, 승, 무, 패, 득실, 승점

                            style_attr = row.get("style", "")
                            tag_color =
