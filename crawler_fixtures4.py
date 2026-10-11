import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

def crawl_match_details_v4(league_ids=None):
    if league_ids is None:
        league_ids = [39, 11]  # 지정된 리그 ID 순차 탐색
        
    for league_id in league_ids:
        target_url = f"https://football.scoreman123.com/league/{league_id}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://football.scoreman123.com/"
        }
        
        match_data_v4 = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "league_id": league_id,
            "league_name": "",
            "total_stages": 1,
            "active_stage": "",
            "total_rounds": 0,
            "active_round": "",
            "standings": [],
            "standing_legends": []
        }

        try:
            print(f"[ID: {league_id}] 페이지 요청 중: {target_url}")
            response = requests.get(target_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"[ID: {league_id}] 페이지 요청 실패 (Status: {response.status_code}) -> 다음 리그로 넘어갑니다.")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. [상단 구조 탐색] 스크립트 내 const _className = escapeChar("...") 정밀 추출
            for script in soup.find_all("script"):
                if script.string and "_className = escapeChar" in script.string:
                    match = re.search(r'_className\s*=\s*escapeChar\("([^"]+)"\)', script.string)
                    if match:
                        match_data_v4["league_name"] = match.group(1).strip()
                        break
            
            if not match_data_v4["league_name"]:
                title_elem = soup.select_one("div.header div.title, div#title, .league_title, h4")
                if title_elem:
                    match_data_v4["league_name"] = title_elem.text.strip().replace("라이브스코어", "").strip()

            if not match_data_v4["league_name"]:
                print(f"[ID: {league_id}] 유효한 리그 이름을 찾을 수 없음 -> 다음 리그로 넘어갑니다.")
                continue

            match_data_v4["active_stage"] = match_data_v4["league_name"]

            # 2. [상단 일정/라운드 구조 탐색] div#schedule ➔ div.round 내부 span 탐색
            all_rounds = soup.select("div#schedule div.round span[round], div.round span[round]")
            if all_rounds:
                match_data_v4["total_rounds"] = len(all_rounds)
                active_round_elem = soup.select_one("div#schedule div.round span.current.on, div.round span.current.on, span.current.on")
                if active_round_elem and active_round_elem.text.strip():
                    match_data_v4["active_round"] = active_round_elem.text.strip()
                else:
                    match_data_v4["active_round"] = all_rounds[0].text.strip()
            else:
                match_data_v4["total_rounds"] = 0
                match_data_v4["active_round"] = ""

            # 3. [하단 정보 구조 탐색] div#standingColor ➔ span.explain 내부의 i태그(색상)와 span태그(설명) 매칭
            legend_items = soup.select("div#standingColor span.explain, #standingColor span.explain")
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

            # 4. [우측 팀순위 구조 탐색] div#standingPlates ➔ ul#standingList ➔ 각 팀 행(li) 순차 파싱
            standings_items = soup.select("ul#standingList > li")
            parsed_standings = []
            
            for item in standings_items:
                classes = item.get("class", [])
                
                # 상단 헤더 행(R, 구단, P, W, D, L, GD, PTS)은 건너뜀
                if "title" in classes:
                    continue

                style_attr = item.get("style", "")
                tag_color = ""
                if "--tagcolor:" in style_attr:
                    try:
                        tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                    except Exception:
                        tag_color = ""

                # 스탠딩 컬러와 하단 범례 설명 실시간 매칭 (없으면 "일반")
                tag_label = color_to_label.get(tag_color, "일반")

                rank_elem = item.select_one("span.rank em, .rank em, span.rank")
                name_elem = item.select_one("span.team span.name, .team .name, span.name")
                
                # 행 내부에 있는 모든 span 태그 텍스트 추출
                all_spans = [s.text.strip() for s in item.select("span") if s.text.strip()]
                
                rank_val = rank_elem.text.strip() if rank_elem else ""
                team_val = name_elem.text.strip() if name_elem else ""
                
                if not team_val and len(all_spans) > 1:
                    team_val = all_spans[1]

                if rank_val and team_val and rank_val.lower() != 'r':
                    # 스크린샷 구조상 뒤쪽의 6개 스탯 (경기수, 승, 무, 패, 득실, 승점) 추출
                    stat_slice = all_spans[-6:] if len(all_spans) >= 6 else []
                    parsed_standings.append({
                        "순위": rank_val.replace("\n", "").strip(),
                        "구단": team_val,
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
            print(f"[{match_data_v4['league_name']}] 수집 성공 (총 {len(parsed_standings)}개 팀 파싱 완료)")

            # 파일 저장 후 정상 종료
            output_filename = "match_details_v4.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(match_data_v4, f, ensure_ascii=False, indent=4)
            print(f"[{output_filename}] 저장 완료.")
            break

        except Exception as e:
            print(f"[ID: {league_id}] 크롤링 중 오류 발생: {e} -> 다음 리그로 넘어갑니다.")
            continue

if __name__ == "__main__":
    crawl_match_details_v4(league_ids=[39, 11])
