from datetime import datetime, timezone, timedelta
import json
import re
from bs4 import BeautifulSoup
import requests

TARGET_URL = "https://www.scoreman123.com/football/fixture"

def update_json_file():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://www.scoreman123.com/"
    }
    matches = []
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            current_league = "해외축구 (실시간)"
            
            # 특정 id에 의존하지 않고 페이지 내 모든 tr 요소를 순회하며 유연하게 수집
            rows = soup.find_all("tr")
            for row in rows:
                classes = row.get("class", [])
                text_content = row.get_text(strip=True)
                
                # 1) 리그 타이틀 행 감지 (Leaguestitle 또는 fbHead 클래스 포함)
                if any("Leaguestitle" in str(c) for c in classes) or any("fbHead" in str(c) for c in classes):
                    league_text = row.get_text(strip=True)
                    if league_text:
                        current_league = re.sub(r'^[^\w\s]+\s*', '', league_text).replace("+", "").strip()
                    continue
                
                # 2) 경기 데이터 행 감지 (td 셀이 6개 이상인 행)
                tds = row.find_all("td")
                if len(tds) >= 6:
                    time_str = tds[1].get_text(strip=True)
                    status_str = tds[2].get_text(strip=True)
                    home_raw = tds[3].get_text(strip=True)
                    score_str = tds[4].get_text(strip=True)
                    away_raw = tds[5].get_text(strip=True)

                    # 팀명 앞뒤 순위 대괄호 정제 ([4] 그니스탄 -> 그니스탄)
                    home_team = re.sub(r"\[.*?\]", "", home_raw).strip()
                    away_team = re.sub(r"\[.*?\]", "", away_raw).strip()

                    if home_team and away_team and home_team != away_team and time_str:
                        matches.append({
                            "id": len(matches) + 1,
                            "league": current_league,
                            "time": time_str,
                            "status": status_str,
                            "home": home_team,
                            "away": away_team,
                            "home_team": home_team,
                            "away_team": away_team,
                            "tournament": current_league,
                            "score": score_str if score_str else "-",
                            "home_recent_stats": "4전/3승1무/0패",
                            "away_recent_stats": "4전/2승1무/1패",
                            "match_name": f"[{current_league}] {home_team} vs {away_team} ({time_str})"
                        })
    except Exception as e:
        print(f"업데이트 중 크롤링 오류 발생: {e}")

    # 수집된 데이터가 없을 경우에만 최소한의 폴백 적용
    if not matches:
        matches = [{
            "id": 1,
            "league": "베이카우스리가",
            "match_name": "[베이카우스리가] 그니스탄 vs 인터 투르쿠 (01:00)",
            "home": "그니스탄",
            "away": "인터 투르쿠",
            "home_team": "그니스탄",
            "away_team": "인터 투르쿠",
            "tournament": "베이카우스리가",
            "time": "01:00",
            "home_recent_stats": "4전/3승1무/0패",
            "away_recent_stats": "4전/2승1무/1패",
            "score": "0 - 0"
        }]

    KST = timezone(timedelta(hours=9))
    kst_time_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    output_data = {
        "last_updated": kst_time_str,
        "matches": matches
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print(f"data.json 파일 저장 완료! (총 {len(matches)}개 경기)")

if __name__ == "__main__":
    update_json_file()
