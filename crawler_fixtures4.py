import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def crawl_match_details_v4(league_ids=None):
    if league_ids is None:
        league_ids = [75, 39, 11]  # 탐색할 리그 ID 목록
        
    for league_id in league_ids:
        target_url = f"https://football.scoreman123.com/league/{league_id}"
        
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
            if response.status_code != 200:
                print(f"[ID: {league_id}] 페이지 요청 실패 (Status: {response.status_code}) -> 다음 리그로 넘어갑니다.")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. 리그명 정밀 추출 (A OR B 병합)
            league_title_elem = soup.select_one("div#title.title, div.box h4, .league_title, h4, h2, div.header div.title")
            if league_title_elem:
                txt = league_title_elem.text.strip()
                if txt and txt not in ["일정", "대진표", "팀순위", "정보", "오즈통계", "베스트11"]:
                    match_data_v4["league_name"] = txt.replace("라이브스코어", "").strip()

            if not match_data_v4["league_name"]:
                print(f"[ID: {league_id}] 유효한 리그 정보를 찾을 수 없음 -> 다음 리그로 넘어갑니다.")
                continue

            # 2. 스테이지 탐색 목록 및 활성 상태 정밀 추출 (결승전, 그룹 스테이지 등 무조건 타격)
            stage_buttons = soup.select("div.stage span, .stage span, div#schedule.plates.schedule div.stage span")
            if stage_buttons:
                match_data_v4["total_stages"] = len(stage_buttons)
                active_stage_elem = soup.select_one("span.current.on, span.on, div.stage span.current.on, .stage span.current.on")
                if active_stage_elem and active_stage_elem.text.strip():
                    match_data_v4["active_stage"] = active_stage_elem.text.strip()
                else:
                    match_data_v4["active_stage"] = stage_buttons[0].text.strip()
            else:
                match_data_v4["total_stages"] = 1
                match_data_v4["active_stage"] = match_data_v4["league_name"]

            # 3. 라운드 탐색 목록 및 활성 상태 추출
            all_rounds = soup.select("div.round span[round], .round span[round], div.round span")
            if all_rounds:
                match_data_v4["total_rounds"] = len(all_rounds)
                active_round_elem = soup.select_one("div.round span.current.on, .round span.current.on, span.current.on")
                if active_round_elem and active_round_elem.text.strip():
                    match_data_v4["active_round"] = active_round_elem.text.strip()
                else:
                    match_data_v4["active_round"] = all_rounds[0].text.strip()
            else:
                match_data_v4["total_rounds"] = 0
                match_data_v4["active_round"] = ""

            # 4. 하단 범례 색상 및 설명 동적 추출
            legend_items = soup.select("#standingColor span.explain, .explain, .legend span, div.box span.explain, div#info span")
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
                    if bg_color and desc_text:
                        color_to_label[bg_color] = desc_text
                        parsed_legends.append({
                            "color": bg_color,
                            "description": desc_text
                        })
            
            match_data_v4["standing_legends"] = parsed_legends

            # 5. 💡 월드컵 등 그룹형 토너먼트 랭킹표 정밀 파싱 (ul#standingList 내의 li.group 및 li.standis 완벽 대응)
            standings_items = soup.select("ul#standingList li, #standingList li.standis, .standings_list li, tbody tr, div.standis")
            parsed_standings = []
            current_group = ""  # 그룹 스테이지명 (예: "그룹 스테이지 A", "그룹 스테이지 B" 등)
            
            for item in standings_items:
                classes = item.get("class", [])
                
                # 그룹 타이틀 항목일 경우 그룹명 갱신
                if "group" in classes:
                    current_group = item.text.strip()
                    continue
                
                # 타이틀 행(R, 구단, P, W 등 헤더)은 건너뜀
                if "title" in classes:
                    continue

                style_attr = item.get("style", "")
                tag_color = ""
                if "--tagcolor:" in style_attr:
                    try:
                        tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                    except Exception:
                        tag_color = ""

                tag_label = color_to_label.get(tag_color, "일반")

                rank_elem = item.select_one(".rank em, .rank, span.rank")
                name_elem = item.select_one(".team .name, span.name, .name")
                all_spans = [s.text.strip() for s in item.select("span") if s.text.strip()]
                
                rank_val = rank_elem.text.strip() if rank_elem else ""
                team_val = name_elem.text.strip() if name_elem else ""
                
                if not team_val and len(all_spans) > 1:
                    team_val = all_spans[1]

                # 순위와 구단명이 존재하고 헤더문구가 아닐 때만 수집
                if rank_val and team_val and rank_val.lower() != 'r':
                    stat_slice = all_spans[-6:] if len(all_spans) >= 6 else []
                    parsed_standings.append({
                        "group": current_group,
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
            print(f"[{match_data_v4['league_name']}] 수집 성공 (Stage: {match_data_v4['active_stage']}, 총 {len(parsed_standings)}개 팀 파싱 완료)")

            # 파일 저장 후 성공 종료
            output_filename = "match_details_v4.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(match_data_v4, f, ensure_ascii=False, indent=4)
            print(f"[{output_filename}] 저장 완료.")
            break

        except Exception as e:
            print(f"[ID: {league_id}] 크롤링 중 오류 발생: {e} -> 다음 리그로 넘어갑니다.")
            continue

if __name__ == "__main__":
    crawl_match_details_v4(league_ids=[75, 39, 11])
