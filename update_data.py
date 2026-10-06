from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup

# 스코어맨 실제 라이브스코어 및 경기 일정 페이지
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

      # 스코어맨 실시간 경기 리스트 컨테이너 및 아이템 셀렉터 (전체 통째로 파싱)
      match_rows = soup.select(
          ".row_item, .game-item, tr.match-row, .schedule_box"
      )

      if not match_rows:
        match_rows = soup.select("ul.game_list > li, table.score_table tr")

      for idx, el in enumerate(match_rows, 1):
        try:
          # 리그명 추출
          league_el = el.select_one(".league_name, .league, th, .s_league")
          league = league_el.get_text(strip=True) if league_el else "해외축구"

          # 경기 시간 추출
          time_el = el.select_one(".match_time, .time, .s_time")
          match_time = time_el.get_text(strip=True) if time_el else "진행중"

          # 홈팀 / 원정팀 추출
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
    print(f"스코어맨 데이터 크롤링 중 오류 발생: {e}")

  # 크롤링된 데이터가 비어있을 경우 대시보드 에러 방지를 위한 폴백 구조
  if not matches:
    matches = [{
        "id": 1,
        "league": "스코어맨 연동 대기중",
        "time": datetime.now().strftime("%H:%M"),
        "home": "데이터 수집 실패 또는",
        "away": "구조 변경 확인 필요",
        "status": "대기",
    }]

  data = {
      "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "source": TARGET_URL,
      "matches": matches,
  }

  with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

  print(
      f"data.json 업데이트 완료! (총 {len(matches)}개 경기 데이터 연동됨)"
  )


if __name__ == "__main__":
  fetch_scoreman_data()
