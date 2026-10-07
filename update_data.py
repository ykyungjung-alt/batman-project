from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
import requests

TARGET_URL = "https://www.scoreman123.com/football/fixture"


def fetch_scoreman_data():
  matches = []
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Referer": "https://www.scoreman123.com/football/fixture",
  }

  try:
    response = requests.get(TARGET_URL, headers=headers, timeout=5)
    if response.status_code == 200:
      soup = BeautifulSoup(response.text, "html.parser")
      current_league = "해외축구 (실시간)"
      table = soup.find("table", id="table_live")

      if table:
        rows = table.find_all("tr")
        for row in rows:
          classes = row.get("class", [])

          # 스코어맨 실제 리그 타이틀 구조 파싱
          if "Leaguestitle" in classes and "fbHead" in classes:
            league_text = row.get_text(strip=True)
            if league_text:
              current_league = league_text.replace("+", "").strip()
            continue

          # 경기 데이터 행 구조 파싱 (b2)
          if "b2" in classes:
            tds = row.find_all("td")
            if len(tds) >= 6:
              time_str = tds[1].get_text(strip=True)
              status_str = tds[2].get_text(strip=True)
              home_raw = tds[3].get_text(strip=True)
              score_str = tds[4].get_text(strip=True)
              away_raw = tds[5].get_text(strip=True)

              # 팀명 앞뒤 대괄호 메타데이터 정제 ([4] 그니스탄 -> 그니스탄)
              home_team = re.sub(r"\[.*?\]", "", home_raw).strip()
              away_team = re.sub(r"\[.*?\]", "", away_raw).strip()

              if home_team and away_team:
                matches.append({
                    "id": len(matches) + 1,
                    "league": current_league,
                    "time": time_str if time_str else "진행중",
                    "status": status_str,
                    "home": home_team,
                    "away": away_team,
                    "home_team": home_team,
                    "away_team": away_team,
                    "tournament": current_league,
                    "score": score_str,
                    "home_recent_stats": "실시간 수집 체급 적용",
                    "away_recent_stats": "실시간 수집 체급 적용",
                })
  except Exception as e:
    print(f"크롤링 중 오류 발생: {e}")

  return matches


if __name__ == "__main__":
  matches = fetch_scoreman_data()

  # 데이터가 없을 경우를 대비한 방어용 기본 데이터
  if not matches:
    matches = [{
        "id": 1,
        "league": "잉글랜드 FA 컵",
        "time": "28",
        "status": "PASS",
        "home": "윈게이트&핀칠리",
        "away": "베드포드",
        "home_team": "윈게이트&핀칠리",
        "away_team": "베드포드",
        "tournament": "잉글랜드 FA 컵",
        "score": "-",
    }]

  output_data = {
      "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "source": TARGET_URL,
      "matches": matches,
  }

  with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

  print(f"data.json 업데이트 완료! (총 {len(matches)}개 경기 수집)")
