import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def crawl_match_details(league_id):
    target_url = f"https://football.scoreman123.com/league/{league_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    match_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "league_id": league_id,
        "league_name": "",
        "active_round": "",   # 현재 활성 라운드
        "total_rounds": "",   # 총 라운드 수
        "standings": [],
        "standing_legends": []
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. League name
            title_elem = soup.select_one("div.box h4, .league_title, h4")
            if title_elem:
                txt = title_elem.text.strip()
                if txt and txt not in ["일정", "대진표", "팀순위", "정보", "오즈통계", "베스트11"]:
                    match_data["league_name"] = txt.replace("라이브스코어", "").strip()
            
            if not match_data["league_name"]:
                match_data["league_name"] = f"리그 ID {league_id}"

            # 2. stage 속성이 존재하는 영역을 먼저 확인한 후, 그 하위의 round 및 style class="current on"을 정확히 매칭하여 추출
            active_text = "1"
            
            # stage와 round 속성을 모두 가진 span 태그들을 대상으로 탐색
            round_spans = soup.select("div.round span[stage][round]")
            
            if not round_spans:
                # 일반적인 경우의 대비책
                round_spans = soup.select("div.round span[round]")

            for span in round_spans:
                # stage 값이 유효하게 존재하는지 확인하고, 동시에 태그 문자열에 "style class" 또는 "current"가 포함된 항목 타격
                stage_val = span.get("stage", "").strip()
                if stage_val and ("style class" in str(span) or "current" in str(span)):
                    active_text = span.get("round", "").strip()
                    break
            
            total_cnt = len(round_spans) if round_spans else 46
            
            match_data["active_round"] = active_text
            match_data["total_rounds"] = str(total_cnt)

            # 3. Legends (Standing colors)
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
            
            match_data["standing_legends"] = parsed_legends

            # 4. Standings
            standings_items = soup.select("#standingList li.standis")
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

            match_data["standings"] = parsed_standings
            print(f"[{match_data['league_name']}] 수집 성공 (Round: {match_data['active_round']} / Total: {match_data['total_rounds']})")
        else:
            print(f"페이지 요청 실패 (League ID: {league_id}): Status Code {response.status_code}")

    except Exception as e:
        print(f"리그 ID {league_id} 크롤링 중 오류 발생: {e}")

    output_filename = f"match_details_league_{league_id}.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(match_data, f, ensure_ascii=False, indent=4)
        
    print(f"[{output_filename}] 저장 완료.")

if __name__ == "__main__":
    target_league_ids = [39, 40]
    for lid in target_league_ids:
        print(f"\n--- 리그 ID {lid} 크롤링 시작 ---")
        crawl_match_details(lid)
