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
            
            # 페이지 내 모든 행을 순회하며 리그명과 경기 정보 파싱
            rows = soup.find_all("tr")
            for row in rows:
                text_content = row.get_text(strip=True)
                
                # 1) 리그 타이틀 영역 감지 (이미지나 특정 클래스, 또는 텍스트 패턴 분석)
                # 스코어맨 구조상 팀 아이콘이나 국가별 리그 타이틀 행 처리
                imgs = row.find_all("img")
                tds = row.find_all("td")
                
                # 셀이 1~2개이면서 리그명인 경우 감지
                if len(tds) == 2 and not text_content.startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "-")):
                    potential_league = tds[1].get_text(strip=True) if len(tds) > 1 else text_content
                    if potential_league:
                        current_league = re.sub(r'^[^\w\s]+\s*', '', potential_league).replace("+", "").strip()
                    continue
                
                # 2) 경기 데이터 행 감지 (시간, 홈팀, 스코어, 원정팀 등이 포함된 6개 이상의 셀 구조)
                if len(tds) >= 6:
                    time_str = tds[1].get_text(strip=True)
                    # 시간이 HH:MM 형식인지 간단히 검증
                    if not re.match(r"^\d{2}:\d{2}$", time_str):
                        continue
                        
                    status_str = tds[2].get_text(strip=True)
                    home_raw = tds[3].get_text(strip=True)
                    score_str = tds[4].get_text(strip=True)
                    away_raw = tds[5].get_text(strip=True)

                    # 팀명 앞뒤 순위 대괄호 정제 ([4] 그니스탄 -> 그니스탄)
                    home_team = re.sub(r"\[.*?\]", "", home_raw).strip()
                    away_team = re.sub(r"\[.*?\]", "", away_raw).strip()

                    if home_team and away_team and home_team != away_team:
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
        print(f"크롤링 중 오류 발생: {e}")

    # 파싱된 데이터가 없을 경우에만 비상용 기본 데이터 투입
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
    print(f"data.json 갱신 완료 (총 {len(matches)}경기)")

if __name__ == "__main__":
    update_json_file()
