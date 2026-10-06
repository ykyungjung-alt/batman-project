from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup

TARGET_URL = "https://www.scoreman123.com/"


def fetch_scoreman_data():
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Referer": "https://www.scoreman123.com/",
  }

  matches = []
  try:
    response = requests.get(TARGET_URL, headers=headers, timeout=10)
    if response.status_code == 200:
      soup = BeautifulSoup(response.text, "html.parser")

      # 스코어맨 실시간 경기 행(Row) 선택자 탐색
      match_rows = soup.select(
          "tr.match-row, .row_item, .game-item, table.score_table tr"
      )

      for idx, el in enumerate(match_rows, 1):
        try:
          league_el = el.select_one(".league_name, .league, th, .s_league")
          league = league_el.get_text(strip=True) if league_el else "해외축구"

          time_el = el.select_one(".match_time, .time, .s_time")
          match_time = time_el.get_text(strip=True) if time_el else "진행중"

          home_el = el.select_one(".home_team, .team_home, .home")
          away_el = el.select_one(".away_team, .team_away, .away")

          home = home_el.get_text(strip=True) if home_el else ""
          away = away_el.get_text(strip=True) if away_el else ""

          if home and away:
            status_el = el.select_one(".match_status, .status, .s_state")
            status = (
                status_el.get_text(strip=True) if status_el else "라이브"
            )

            matches.append({
                "id": len(matches) + 1,
                "league": league,
                "time": match_time,
                "home": home,
                "away": away,
                "status": status,
            })
        except Exception:
          continue
  except Exception as e:
    print(f"크롤링 오류 발생: {e}")

  # 데이터가 없을 경우 앱 깨짐 방지용 안전 기본 구조
  if not matches:
    matches = [{
        "id": 1,
        "league": "연동 대기중",
        "time": datetime.now().strftime("%H:%M"),
        "home": "데이터 수집 대기",
        "away": "스코어맨 연결 확인",
        "status": "대기",
    }]

  data = {
      "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "source": TARGET_URL,
      "matches": matches,
  }

  with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

  print(f"data.json 갱신 완료 (총 {len(matches)}경기)")


if __name__ == "__main__":
  fetch_scoreman_data()
