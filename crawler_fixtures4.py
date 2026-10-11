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

            # 2. 활성화된 라운드 정밀 추출 (current on 클래스 기준)
            active_round_elem = soup.select_one("#schedule span.current.on, .schedule span.current, span.current")
            if active_round_elem:
                active_num = active_round_elem.text.strip()
                all_rounds = soup.select("#schedule span[round], .schedule span[round]")
                total_cnt = len(all_rounds) if all_rounds else 46
                match_data_v4["total_rounds"] = total_cnt
                match_data_v4["active_round"] = f"{active_num}/{total_cnt}"

            # 3. 💡 팀 순위(Standings) 전체 24개 팀 정밀 타격 파싱
            standings_items = soup.select("#standingList li.standis")
            parsed_standings = []
            
            for item in standings_items:
                # 인라인 스타일에서 태그 컬러(--tagcolor) 추출
                style_attr = item.get("style", "")
                tag_color = ""
                if "--tagcolor:" in style_attr:
                    try:
                        tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip()
                    except Exception:
                        tag_color = ""

                # 순위 및 팀명 추출
                rank_elem = item.select_one(".rank")
                name_elem = item.select_one(".team .name, span.name")
                
                all_spans = [s.text.strip() for s in item.select("span") if s.text.strip()]
                
                rank_val = rank_elem.text.strip() if rank_elem else ""
                team_val = name_elem.text.strip() if name_elem else ""
                
                if not team_val and len(all_spans) > 1:
                    team_val = all_spans[1]

                if rank_val and team_val:
                    # 뒤에서부터 순서대로 6개 통계 (경기수, 승, 무, 패, 득실, 승점) 매칭
                    stat_slice = all_spans[-6:] if len(all_spans) >= 6 else []
                    
                    parsed_standings.append({
                        "rank": rank_val.replace("\n", "").strip(),
                        "team": team_val,
                        "tag_color": tag_color,
                        "경기수": stat_slice[0] if len(stat_slice) > 0 else "",
                        "승": stat_slice[1] if len(stat_slice) > 1 else "",
                        "무": stat_slice[2] if len(stat_slice) > 2 else "",
                        "패": stat_slice[3] if len(stat_slice) > 3 else "",
                        "득실": stat_slice[4] if len(stat_slice) > 4 else "",
                        "승점": stat_slice[5] if len(stat_slice) > 5 else ""
                    })
            
            match_data_v4["standings"] = parsed_standings

            # 4. 💡 순위표 하단 색상별 범례 파싱 (#standingColor span.explain)
            legend_items = soup.select("#standingColor span.explain, .explain")
            parsed_legends = []
            for lg in legend_items:
                color_i = lg.select_one("i")
                desc_span = lg.select_one("span")
                if color_i:
                    bg_style = color_i.get("style", "")
                    bg_color = ""
                    if "background-color:" in bg_style:
                        try:
                            bg_color = bg_style.split("background-color:")[1].split(";")[0].strip()
                        except Exception:
                            bg_color = ""
                    desc_text = desc_span.text.strip() if desc_span else lg.text.strip()
                    parsed_legends.append({
                        "color": bg_color,
                        "description": desc_text
                    })
            
            match_data_v4["standing_legends"] = parsed_legends
            print(f"성공적으로 총 {len(parsed_standings)}개 팀의 순위 데이터를 수집했습니다.")
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
