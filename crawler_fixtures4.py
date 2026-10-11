import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def crawl_match_details_v4(league_ids=None):
    # 탐색할 리그 ID 목록 (원하시는 번호들을 리스트로 지정하여 순회)
    if league_ids is None:
        league_ids = [39, 75, 11] # 예시로 탐색할 리그 ID 목록
        
    for league_id in league_ids:
        target_url = f"url?id=42league/{league_id}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        match_data_v4 = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "league_id": league_id,
            "league_name": "",
            "total_stages": 0,
            "active_stage": "",
            "total_rounds": 0,
            "active_round": "",
            "standings": [],
            "standing_legends": []
        }

        try:
            response = requests.get(target_url, headers=headers, timeout=10)
            
            # 💡 페이지가 정상적이지 않거나(404 등) 데이터가 없으면 이 ID는 건너뛰고 다음 페이지로 이동
            if response.status_code != 200:
                print(f"[ID: {league_id}] 페이지 요청 실패 (Status: {response.status_code}) -> 다음 리그로 넘어갑니다.")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 리그명 추출
            league_title_elem = soup.select_one("div.box h4, .league_title, h4, h2")
            if league_title_elem:
                txt = league_title_elem.text.strip()
                if txt and txt not in ["일정", "대진표", "팀순위", "정보", "오즈통계", "베스트11"]:
                    match_data_v4["league_name"] = txt.replace("라이브스코어", "").strip()

            # 리그명이 없거나 빈 페이지 형태라면 데이터가 없는 것이므로 건너뜀
            if not match_data_v4["league_name"]:
                print(f"[ID: {league_id}] 유효한 리그 정보를 찾을 수 없음 -> 다음 리그로 넘어갑니다.")
                continue

            # 스테이지 탐색 목록 및 활성 상태 추출
            stage_buttons = soup.select("div.stage span, .stage span")
            if stage_buttons:
                match_data_v4["total_stages"] = len(stage_buttons)
                active_stage_elem = soup.select_one("div.stage span.current.on, .stage span.current.on")
                if active_stage_elem:
                    match_data_v4["active_stage"] = active_stage_elem.text.strip()
                else:
                    match_data_v4["active_stage"] = stage_buttons[0].text.strip()
            else:
                match_data_v4["total_stages"] = 1
                match_data_v4["active_stage"] = match_data_v4["league_name"]

            # 라운드 탐색 목록 및 활성 상태 추출
            all_rounds = soup.select("div.round span[round], .round span[round], .round span")
            if all_rounds:
                match_data_v4["total_rounds"] = len(all_rounds)
                active_round_elem = soup.select_one("div.round span.current.on, .round span.current.on")
                if active_round_elem:
                    match_data_v4["active_round"] = active_round_elem.text.strip()
                else:
                    match_data_v4["active_round"] = all_rounds[0].text.strip()
            else:
                match_data_v4["total_rounds"] = 0
                match_data_v4["active_round"] = ""

            # 하단 범례 색상 및 의미 동적 추출
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
                        except Exception:
                            bg_color = ""
                    desc_text = desc_span.text.strip() if desc_span else lg.text.strip()
                    if bg_color:
                        color_to_label[bg_color] = desc_text
                    parsed_legends.append({
                        "color": bg_color,
                        "description": desc_text
                    })
            
            if not parsed_legends:
                color_to_label = {"#CCCCFF": "승격팀", "#00CCCC": "승격 플레이오프", "#B1A7A7": "강등팀"}
                parsed_legends = [
                    {"color": "#CCCCFF", "description": "승격팀"},
                    {"color": "#00CCCC", "description": "승격 플레이오프"},
                    {"color": "#B1A7A7", "description": "강등팀"}
                ]
            
            match_data_v4["standing_legends"] = parsed_legends

            # 팀 순위 동적 파싱
            standings_items = soup.select("#standingList li.standis, .standings_list li, tbody tr")
            parsed_standings = []
            
            for item in standings_items:
                style_attr = item.get("style", "")
                tag_color = ""
                if "--tagcolor:" in style_attr:
                    try:
                        tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                    except Exception:
                        tag_color = ""

                tag_label = color_to_label.get(tag_color, "일반")

                rank_elem = item.select_one(".rank em, .rank")
                name_elem = item.select_one(".team .name, span.name")
                all_spans = [s.text.strip() for s in item.select("span") if s.text.strip()]
                
                rank_val = rank_elem.text.strip() if rank_elem else ""
                team_val = name_elem.text.strip() if name_elem else ""
                
                if not team_val and len(all_spans) > 1:
                    team_val = all_spans[1]

                if rank_val and team_val:
                    stat_slice = all_spans[-6:] if len(all_spans) >= 6 else []
                    parsed_standings.append({
                        "rank": rank_val.replace("\n", "").strip(),
                        "team": team_val,
                        "tag_color": tag_color,
                        "tag_label": tag_label,
                        "경기수": stat_slice[0] if len(stat_slice) > 0 else "",
                        "승": stat_slice[1] if len(stat_slice) > 1 else "",
                        "무": stat_slice[2] if len(stat_slice) > 2 else "",
                        "패": stat_slice[3] if len(stat_slice) > 3 else "",
                        "득실": stat_slice[4] if len(stat_slice) > 4 else "",
                        "승점": stat_slice[5] if len(stat_slice) > 5 else ""
                    })

            match_data_v4["standings"] = parsed_standings
            print(f"[{match_data_v4['league_name']}] 수집 성공 (총 {len(parsed_standings)}개 팀)")

            # 유효한 데이터가 성공적으로 수집되었을 때만 파일로 저장 후 종료 (또는 계속 순회)
            output_filename = "match_details_v4.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(match_data_v4, f, ensure_ascii=False, indent=4)
            print(f"[{output_filename}] 저장 완료.")
            break # 성공적으로 수집했으므로 순회 종료 (계속 탐색하려면 break 제거)

        except Exception as e:
            print(f"[ID: {league_id}] 크롤링 중 오류 발생: {e} -> 다음 리그로 넘어갑니다.")
            continue

if __name__ == "__main__":
    # 탐색할 리그 ID 목록을 순서대로 지정 (예: 75가 없거나 실패하면 다음 ID 탐색)
    crawl_match_details_v4(league_ids=[75, 39, 11])
