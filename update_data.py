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

      current_league = "해외축구"
      # 스코어맨 페이지의 전체 본문 행(리그 헤더와 경기 row 모두 포함) 순회
      rows = soup.select("table tr, .score_table tr")

      for row in rows:
        # 리그 헤더 행인 경우
        league_header = row.select_one("th, .league_title, td[colspan]")
        if league_header and not row.select(".home_team, .home"):
          text = league_header.get_text(strip=True)
          if text and len(text) > 1:
            current_league = text
          continue

        # 경기 데이터 행 파싱
        try:
          # 시간 추출
          time_el = row.select_one("td:nth-child(2), .match_time, .time")
          match_time = time_el.get_text(strip=True) if time_el else "진행중"

          # 홈팀, 원정팀 추출 (스코어맨 테이블 구조 기준)
          tds = row.select("td")
          if len(tds) >= 5:
            # 보통 홈팀과 원정팀이 특정 셀에 위치
            home_text = ""
            away_text = ""

            # 텍스트 구조 분석을 통한 팀명 추출
            for td in tds:
              text = td.get_text(strip=True)
              if " - " in text and not home_text:
                parts = text.split(" - ")
                if len(parts) == 2:
                  home_text = parts[0].strip()
                  away_text = parts[1].strip()

            if not home_text:
              # 대체 셀렉터 시도
              home_el = row.select_one(
                  ".home_team, .team_home, td:nth-child(3)"
              )
              away_el = row.select_one(
                  ".away_team, .team_away, td:nth-child(5)"
              )
              home_text = home_el.get_text(strip=True) if home_el else ""
              away_text = away_el.get_text(strip=True) if away_el else ""

            # 스코어, 상태 등 정제
            if home_text and away_text and len(home_text) > 1:
              matches.append({
                  "id": len(matches) + 1,
                  "league": current_league,
                  "time": match_time,
                  "home": home_text.replace("[", "").split("]")[-1].strip(),
                  "away": away_text.replace("[", "").split("]")[-1].strip(),
                  "status": "라이브",
              })
        except Exception:
          continue
  except Exception as e:
    print(f"크롤링 오류 발생: {e}")

  # 데이터가 없을 경우 방어 코드
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

  print(f"data.json 업데이트 완료 (총 {len(matches)}개 경기)")


if __name__ == "__main__":
  fetch_scoreman_data()
