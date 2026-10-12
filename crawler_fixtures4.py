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

                # 2. Active Round & Total Rounds 정밀 추출
                round_elements = soup.select("div.round span[round]")
                active_text = "1"
                total_cnt = len(round_elements) if round_elements else (46 if league_id == 39 else 38)

                for el in round_elements:
                    span_str = str(el)
                    classes = el.get("class", [])
                    class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
                    
                    if "current" in class_str or "on" in class_str or "current" in span_str:
                        val = el.get("round", "").strip()
                        if not val.isdigit():
                            val = el.text.strip()
                        if val.isdigit():
                            active_text = val
                            break

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

                # 4. 💡 [순위표 정밀 파싱 수정] 부모 컨테이너 div 혼선을 막기 위해 li 및 tr 태그 위주로 개별 행 추출
                parsed_standings = []
                seen_teams = set()
                
                # 전체 문서의 개별 리스트 아이템(li)과 테이블 행(tr)을 후보로 지정
                candidate_rows = soup.select('li, tr')

                for row in candidate_rows:
                    # 내부에 하위 리스트/행이 또 포함된 대형 부모 컨테이너는 개별 행이 아니므로 스킵
                    if len(row.find_all(['li', 'tr'])) > 0:
                        continue

                    raw_tokens = [t.strip() for t in row.text.split() if t.strip()]
                    
                    # 유효성 검사: 첫 번째 토큰이 1~25 사이의 숫자(순위)이고, 전체 토큰 수가 8개 이상인 행
                    if raw_tokens and raw_tokens[0].isdigit():
                        rank_num = int(raw_tokens[0])
                        if 1 <= rank_num <= 25 and len(raw_tokens) >= 8:
                            team_val = raw_tokens[1]
                            
                            # 헤더나 불필요한 텍스트 필터링
                            if team_val in ["구단", "PTS", "순위", "승점", "R"] or any(kw in team_val for kw in ["승점", "득실", "승무패", "통계", "합계"]):
                                continue
                                
                            stat_slice = raw_tokens[-6:] # [경기수, 승, 무, 패, 득실, 승점]
                            
                            # 스탯 영역이 숫자인지 검증
                            if stat_slice[0].isdigit() and stat_slice[1].isdigit() and stat_slice[-1].isdigit():
                                if team_val not in seen_teams:
                                    seen_teams.add(team_val)

                                    style_attr = row.get("style", "")
                                    tag_color = ""
                                    if "--tagcolor:" in style_attr:
                                        try:
                                            tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                                        except:
                                            pass

                                    tag_label = color_to_label.get(tag_color, "일반")

                                    parsed_standings.append({
                                        "rank": str(rank_num),
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

                # 순위 오름차순 정렬 보장
                parsed_standings.sort(key=lambda x: int(x['rank']))

                league_match_data["standings"] = parsed_standings
                print(f"✅ 수집 성공: {league_match_data['league_name']} (라운드: {league_match_data['active_round']}, 팀 수: {len(parsed_standings)}개)")

            except Exception as e:
                print(f"⚠️ 예외 발생: {e}")

            all_leagues_data["leagues"][str(league_id)] = league_match_data

    # 결과 파일 저장
    with open("match_details_v4.json", "w", encoding="utf-8") as f:
        json.dump(all_leagues_data, f, ensure_ascii=False, indent=4)
    print("🎉 match_details_v4.json 저장 완료")

if __name__ == "__main__":
    run_crawler_v4()
