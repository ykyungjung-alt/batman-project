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

    # 실제 수집 대상 리그 주소 설정
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

                # 2. 현재 라운드(Active Round) 추출
                active_elem = soup.select_one("div.round span.current.on")
                active_text = "1"
                
                if active_elem:
                    active_text = active_elem.get("round", "").strip()
                    if not active_text.isdigit():
                        active_text = active_elem.text.strip()

                if not active_text.isdigit():
                    for span in soup.select("div.round span"):
                        if "current" in span.get("class", []) and span.text.strip().isdigit():
                            active_text = span.text.strip()
                            break

                all_rounds = soup.select("div.round span[round]")
                total_cnt = len(all_rounds) if all_rounds else (46 if league_id == 39 else 38)
                
                league_match_data["total_rounds"] = total_cnt
                league_match_data["active_round"] = f"{active_text}/{total_cnt}"

                # 3. 팀순위 데이터 추출
                parsed_standings = []
                seen_teams = set()
                
                for row in soup.select('tr, li'):
                    if row.find_all(['tr', 'li']):
                        continue
                        
                    tokens = [t.strip() for t in row.text.split() if t.strip()]
                    
                    if tokens and tokens[0].isdigit():
                        rank = int(tokens[0])
                        if 1 <= rank <= 25 and len(tokens) >= 8:
                            team = tokens[1]
                            
                            if team in ["구단", "PTS", "순위", "승점"] or any(k in team for k in ["승점", "득실"]):
                                continue
                                
                            stats = tokens[-6:] # [경기수, 승, 무, 패, 득실, 승점]
                            
                            if stats[0].isdigit() and stats[-1].isdigit():
                                if team not in seen_teams:
                                    seen_teams.add(team)
                                    parsed_standings.append({
                                        "rank": str(rank),
                                        "team": team,
                                        "경기수": stats[0],
                                        "승": stats[1],
                                        "무": stats[2],
                                        "패": stats[3],
                                        "득실": stats[4],
                                        "승점": stats[5]
                                    })

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
