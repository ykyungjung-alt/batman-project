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
        
        # 실제 브라우저와 동일한 헤더 및 세션 설정
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.9,en;q=0.9",
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
            response = session.get(target_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                print(f"[ID: {league_id}] 페이지 요청 실패 (Status: {response.status_code}) -> 다음 리그로 넘어갑니다.")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. 리그명 정밀 추출
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
                match_data_v4["league_name"] = f"League_{league_id}"

            match_data_v4["active_stage"] = match_data_v4["league_name"]

            # 2. 라운드(Round) 정보 추출
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

            # 3. 하단 범례(색상 및 설명) 수집
            legend_items = soup.select("div#standingColor span.explain, #standingColor span.explain, div#standingColor span")
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

            # 4. 💡 팀순위(#standingList 또는 전체 문서 내 순위표 구조) 완벽 수집 복구 로직
            standings_items = soup.select("ul#standingList > li")
            if not standings_items:
                # 만약 셀렉터가 걸리지 않으면 문서 전체의 .standis 또는 순위 행 탐색
                standings_items = soup.select("li.standis")

            parsed_standings = []
            
            for item in standings_items:
                classes = item.get("class", [])
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

                rank_elem = item.select_one("span.rank em, .rank em, span.rank")
                name_elem = item.select_one("span.team span.name, .team .name, span.name, span.team")
                
                rank_val = rank_elem.text.strip() if rank_elem else ""
                team_val = name_elem.text.strip() if name_elem else ""
                if team_val.startswith("img") or not team_val:
                    # 이미지 태그나 불순물이 낄 경우 텍스트만 추출
                    name_sub = item.select_one("span.name")
                    if name_sub:
                        team_val = name_sub.text.strip()

                # 모든 span 텍스트 추출 후 뒤쪽 6개 정량 스탯(경기수, 승, 무, 패, 득실, 승점) 매칭
                all_spans = [s.get_text(strip=True) for s in item.select("span") if s.get_text(strip=True)]
                
                if rank_val and team_val and rank_val.lower() != 'r':
                    stat_slice = all_spans[-6:] if len(all_spans) >= 6 else []
                    parsed_standings.append({
                        "순위": rank_val.replace("\n", "").strip(),
                        "구단": team_val.replace("\n", "").strip(),
                        "tag_color": tag_color,
                        "tag_label": tag_label,
                        "경기수": stat_slice[0] if len(stat_slice) > 0 else "",
                        "승": stat_slice[1] if len(stat_slice) > 1 else "",
                        "무": stat_slice[2] if len(stat_slice) > 2 else "",
                        "패": stat_slice[3] if len(stat_slice) > 3 else "",
                        "득실": stat_slice[4] if len(stat_slice) > 4 else "",
                        "승점": stat_slice[5] if len(stat_slice) > 5 else ""
                    })

            # 💡 혹시라도 위 셀렉터로 안 잡힐 경우를 대비한 안전 장치 (텍스트 패턴 기반 백업 파싱)
            if not parsed_standings:
                print(f"[ID: {league_id}] 기본 셀렉터 탐지 실패 -> 백업 텍스트 파싱 엔진 가동")
                for li in soup.select("li"):
                    txts = [s.get_text(strip=True) for s in li.select("span") if s.get_text(strip=True)]
                    if len(txts) >= 8:  # 순위, 팀명, 스탯 6개 이상인 행 조건
                        if txts[0].isdigit():
                            parsed_standings.append({
                                "순위": txts[0],
                                "구단": txts[1],
                                "tag_color": "",
                                "tag_label": "일반",
                                "경기수": txts[2] if len(txts) > 2 else "",
                                "승": txts[3] if len(txts) > 3 else "",
                                "무": txts[4] if len(txts) > 4 else "",
                                "패": txts[5] if len(txts) > 5 else "",
                                "득실": txts[6] if len(txts) > 6 else "",
                                "승점": txts[7] if len(txts) > 7 else ""
                            })

            match_data_v4["standings"] = parsed_standings
            print(f"[{match_data_v4['league_name']}] 수집 성공 (총 {len(parsed_standings)}개 팀 파싱 완료)")

            # 파일 저장
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
