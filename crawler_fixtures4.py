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
        "league_name": "",       # 리그명 (예: 잉글랜드 리그 1)
        "total_rounds": 46,      # 총 라운드 수
        "active_round": "",      # 활성화된 라운드 정보 (예: 11/46)
        "standings": [],         # 팀 순위 및 태그 컬러 정보
        "standing_legends": []   # 하단 색상별 범례 정보 (승격팀, 플레이오프, 강등팀)
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. 리그명 추출
            league_title_elem = soup.select_one("div.box h4, .league_title, h4")
            if league_title_elem:
                match_data_v4["league_name"] = league_title_elem.text.strip().replace("라이브스코어", "").strip()
            else:
                match_data_v4["league_name"] = "잉글랜드 리그 1"

            # 2. 활성화된 라운드 추출 (예: 11/46)
            active_round_elem = soup.select_one("#schedule .round span.current.on, #schedule span.current.on")
            active_round_num = active_round_elem.text.strip() if active_round_elem else "1"
            
            all_rounds = soup.select("#schedule .round span, #schedule span[round]")
            total_rounds_count = len(all_rounds) if all_rounds else 46
            match_data_v4["total_rounds"] = total_rounds_count
            match_data_v4["active_round"] = f"{active_round_num}/{total_rounds_count}"

            # 3. 팀 순위(Standings) 및 태그 컬러(tag_color) 파싱
            standings_items = soup.select("#standingList li.standis")
            parsed_standings = []
            
            for item in standings_items:
                # 인라인 스타일에서 각 팀별 구역 태그 컬러(--tagcolor) 추출 (예: #CCCCFF, #00CCCC, #B1A7A7 등)
                style_attr = item.get("style", "")
                tag_color = ""
                if "--tagcolor:" in style_attr:
                    try:
                        tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip()
                    except Exception:
                        tag_color = ""

                rank_elem = item.select_one(".rank em")
                name_elem = item.select_one(".team .name")
                
                # 해당 행에 있는 모든 텍스트 요소를 순서대로 추출
                all_texts = [span.text.strip() for span in item.select("span") if span.text.strip()]
                
                if rank_elem and name_elem:
                    rank = rank_elem.text.strip()
                    team_name = name_elem.text.strip()
                    
                    parsed_standings.append({
                        "rank": rank,
                        "team": team_name,
                        "tag_color": tag_color,
                        "stats": all_texts[2:] if len(all_texts) > 2 else all_texts
                    })
            
            match_data_v4["standings"] = parsed_standings

            # 4. 순위표 하단 색상별 범례(#standingColor span.explain) 파싱
            legend_items = soup.select("#standingColor span.explain")
            parsed_legends = []
            for lg in legend_items:
                color_i = lg.select_one("i")
                desc_span = lg.select_one("span")
                if color_i and desc_span:
                    bg_style = color_i.get("style", "")
                    bg_color = ""
                    if "background-color:" in bg_style:
                        try:
                            bg_color = bg_style.split("background-color:")[1].split(";")[0].strip()
                        except Exception:
                            bg_color = ""
                    parsed_legends.append({
                        "color": bg_color,
                        "description": desc_span.text.strip()
                    })
            
            match_data_v4["standing_legends"] = parsed_legends
            print(f"성공적으로 [{match_data_v4['league_name']}] ({match_data_v4['active_round']}) 순위 및 범례 데이터를 수집했습니다.")
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
