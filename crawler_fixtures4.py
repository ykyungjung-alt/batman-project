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
            print(f"\n🔄 [수집 중] 리그 ID {league_id}")

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

                # 1. 리그명 추출
                title_elem = soup.select_one("div#title, div.title, .league_title, h4")
                if title_elem:
                    txt = title_elem.text.strip()
                    if txt:
                        league_match_data["league_name"] = txt.replace("라이브스코어", "").strip()

                # ==========================================
                # 💡 [핵심] 영역별 1, 2, 3번 목록으로 나누어 수집
                # ==========================================

                # [목록 1] 상위 인포 및 스테이지 영역 후보군 (div.stage)
                list1_stages = []
                for el in soup.select("div.stage span, div.stage div"):
                    list1_stages.append({
                        "text": el.text.strip(),
                        "class": el.get("class", []),
                        "stage_attr": el.get("stage", "")
                    })
                print(f"  👉 [목록 1: Stage 영역] 총 {len(list1_stages)}개 수집됨")

                # [목록 2] 레프트사이드 하위 라운드 영역 후보군 (div.round 내부의 모든 span)
                list2_rounds = []
                for el in soup.select("div.round span"):
                    list2_rounds.append({
                        "round_attr": el.get("round", ""),
                        "stage_attr": el.get("stage", ""),
                        "text": el.text.strip(),
                        "class": el.get("class", [])
                    })
                print(f"  👉 [목록 2: Round 영역] 총 {len(list2_rounds)}개 수집됨")

                # [목록 3] 팀순위 테이블 행 데이터 후보군
                list3_tables = []
                target_table = None
                for tag in soup.find_all(['h3', 'h4', 'div', 'strong']):
                    if '팀순위' in tag.text:
                        nxt = tag.find_next('table')
                        if nxt:
                            target_table = nxt
                            break
                if not target_table:
                    for tbl in soup.select('table'):
                        if 'PTS' in tbl.text and '구단' in tbl.text:
                            target_table = tbl
                            break

                if target_table:
                    for row in target_table.select('tr'):
                        cells = [c.text.strip() for c in row.select('td, th') if c.text.strip()]
                        if cells:
                            list3_tables.append(cells)
                print(f"  👉 [목록 3: 팀순위 테이블] 총 {len(list3_tables)}개 행 수집됨")

                # ==========================================
                # 🔄 [재배열 및 선택 단계] 목록들을 분석하여 최종 값 추출
                # ==========================================

                # [재배열 1] 목록 2(Round 영역)에서 'current'와 'on' 클래스를 모두 가진 진짜 활성 라운드 골라내기
                active_text = "1"
                for item in list2_rounds:
                    classes = item["class"]
                    class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
                    
                    if "current" in class_str and "on" in class_str:
                        # round 속성이 숫지면 우선 사용, 아니면 텍스트 사용
                        val = item["round_attr"] if item["round_attr"].isdigit() else item["text"]
                        if val.isdigit():
                            active_text = val
                            break

                total_cnt = len(list2_rounds) if list2_rounds else (46 if league_id == 39 else 38)
                league_match_data["total_rounds"] = total_cnt
                league_match_data["active_round"] = f"{active_text}/{total_cnt}"

                # 하단 색상 범례 수집
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

                # [재배열 2] 목록 3(테이블 행 데이터)을 순회하며 정제된 순위표 완성
                parsed_standings = []
                for cell_texts in list3_tables:
                    # [순위, 구단, P, W, D, L, GD, PTS] 구조 검증 (첫 셀이 1~25 사이의 숫자)
                    if len(cell_texts) >= 8 and cell_texts[0].isdigit():
                        rank_val = cell_texts[0]
                        if int(rank_val) > 25:
                            continue
                            
                        team_val = cell_texts[1]
                        stat_slice = cell_texts[-6:] # [경기수, 승, 무, 패, 득실, 승점]

                        parsed_standings.append({
                            "rank": rank_val,
                            "team": team_val,
                            "tag_color": "",
                            "tag_label": "일반",
                            "경기수": stat_slice[0],
                            "승": stat_slice[1],
                            "무": stat_slice[2],
                            "패": stat_slice[3],
                            "득실": stat_slice[4],
                            "승점": stat_slice[5]
                        })

                league_match_data["standings"] = parsed_standings
                print(f"✅ 수집 완료: {league_match_data['league_name']} (현재 라운드: {league_match_data['active_round']}, 팀 수: {len(parsed_standings)}개)")

            except Exception as e:
                print(f"⚠️ 예외 발생: {e}")

            all_leagues_data["leagues"][str(league_id)] = league_match_data

    # 결과 파일 저장
    with open("match_details_v4.json", "w", encoding="utf-8") as f:
        json.dump(all_leagues_data, f, ensure_ascii=False, indent=4)
    print("🎉 match_details_v4.json 저장 완료")

if __name__ == "__main__":
    run_crawler_v4()
