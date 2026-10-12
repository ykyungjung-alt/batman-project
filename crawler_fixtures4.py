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

    # 수집 대상 리그 URL 설정
    target_leagues = [
        {"id": 34, "url": "https://football.scoreman123.com/league/34"},
        {"id": 39, "url": "https://football.scoreman123.com/league/39"},
        {"id": 40, "url": "https://football.scoreman123.com/league/40"}
    ]

    all_leagues_data = {
        "updated_at": now_kst,
        "leagues": {}
    }

    # 세션을 통한 TCP 연결 재사용 최적화
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

                # 1. 리그명 정밀 추출 (<div id="title" class="title">세리에 A</div>)
                title_elem = soup.select_one("div#title, div.title, .league_title")
                if title_elem:
                    txt = title_elem.text.strip()
                    if txt:
                        league_match_data["league_name"] = txt

                # 2. Active Round 정밀 추출 (div.round 내부에서 class="current on"인 항목 정확히 타격)
                active_elem = soup.select_one("div.round span.current.on")
                if not active_elem:
                    for span in soup.select("div.round span"):
                        classes = span.get("class", [])
                        if "current" in classes and "on" in classes:
                            active_elem = span
                            break

                active_text = active_elem.text.strip() if active_elem and active_elem.text.strip().isdigit() else "1"
                
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

                # 4. '팀순위' 헤더 기준 하위 테이블 정밀 타격
                team_ranking_header = None
                for tag in soup.find_all(['h3', 'h4', 'div', 'strong']):
                    if '팀순위' in tag.text:
                        team_ranking_header = tag
                        break

                target_table = team_ranking_header.find_next('table') if team_ranking_header else None
                if not target_table:
                    for tbl in soup.select('table'):
                        if '승점' in tbl.text and '득실' in tbl.text:
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

                            # 행 스타일에서 진출/강등 색상 태그 추출
                            style_attr = row.get("style", "")
                            tag_color = ""
                            if "--tagcolor:" in style_attr:
                                try:
                                    tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                                except:
                                    pass

                            tag_label = color_to_label.get(tag_color, "일반")

                            parsed_standings.append({
                                "rank": rank_val,
                                "team": team_val,
                                "tag_color": tag_color,
                                "tag_label": tag_label,
                                "경기수": stat_slice[0],
                                "승": stat_slice[1],
                                "무": stat_slice[2],
                                "패": stat_slice[3],
                                "득실": stat_slice[4],
                                "승점": stat_slice[5]
                            })

                league_match_data["standings"] = parsed_standings
                print(f"✅ 수집 성공: {league_match_data['league_name']} (총 {len(parsed_standings)}개 팀)")

            except Exception as e:
                print(f"⚠️ 예외 발생: {e}")

            all_leagues_data["leagues"][str(league_id)] = league_match_data

    # 결과 파일 저장
    with open("match_details_v4.json", "w", encoding="utf-8") as f:
        json.dump(all_leagues_data, f, ensure_ascii=False, indent=4)
    print("🎉 match_details_v4.json 저장 완료")

if __name__ == "__main__":
    run_crawler_v4()
