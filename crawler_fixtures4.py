import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def crawl_match_details_v4():
    league_id = 39
    target_url = f"https://football.scoreman123.com/league/{league_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    match_data_v4 = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "league_id": league_id,
        "league_name": "잉글랜드 리그 1",
        "total_rounds": 46,
        "active_round": "1/46",
        "standings": [],
        "standing_legends": []
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. 리그명 정밀 추출
            league_title_elem = soup.select_one("div.box h4, .league_title, h4, h2")
            if league_title_elem:
                title_text = league_title_elem.text.strip()
                if "리그" in title_text or "잉글랜드" in title_text:
                    match_data_v4["league_name"] = title_text.replace("라이브스코어", "").strip()

            # 2. 활성화된 라운드 정밀 추출
            active_round_elem = soup.select_one("#schedule div.round span.current.on, #schedule span.current.on, span.current.on")
            active_num = active_round_elem.text.strip() if active_round_elem else "1"
            
            all_rounds = soup.select("#schedule div.round span[round], #schedule span[round]")
            total_cnt = len(all_rounds) if all_rounds else 46
            match_data_v4["total_rounds"] = total_cnt
            match_data_v4["active_round"] = f"{active_num}/{total_cnt}"

            # 3. 하단 범례 색상별 의미 매핑 딕셔너리 생성 (예: {"#CCCCFF": "승격팀", "#00CCCC": "승격 플레이오프", "#B1A7A7": "강등팀"})
            legend_items = soup.select("#standingColor span.explain")
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
            
            match_data_v4["standing_legends"] = parsed_legends

            # 4. 💡 팀 순위(Standings) 정밀 타격 파싱 및 색상 꼬리표(tag_label) 부여
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

                # 해당 색상에 대응되는 범례 꼬리표 할당 (없으면 일반 팀 또는 빈 값)
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
                        "tag_label": tag_label,  # 💡 해당 색상의 범례 설명 꼬리표 추가 (승격팀, 승격 플레이오프, 강등팀 등)
                        "경기수": stat_slice[0] if len(stat_slice) > 0 else "",
                        "승": stat_slice[1] if len(stat_slice) > 1 else "",
                        "무": stat_slice[2] if len(stat_slice) > 2 else "",
                        "패": stat_slice[3] if len(stat_slice) > 3 else "",
                        "득실": stat_slice[4] if len(stat_slice) > 4 else "",
                        "승점": stat_slice[5] if len(stat_slice) > 5 else ""
                    })
            
            match_data_v4["standings"] = parsed_standings
            print(f"성공적으로 총 {len(parsed_standings)}개 팀 순위 및 색상 꼬리표 매핑을 완료했습니다.")
        else:
            print(f"페이지 요청 실패: Status Code {response.status_code}")

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")

    # match_details_v4.json에 저장
    output_filename = "match_details_v4.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(match_data_v4, f, ensure_ascii=False, indent=4)
        
    print(f"[{output_filename}] 저장 완료.")

if __name__ == "__main__":
    crawl_match_details_v4()
