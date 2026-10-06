from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
import requests

TARGET_URL = "https://www.scoreman123.com/football/fixture"


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
      rows = soup.select("tr")

      for row in rows:
        # 1. 리그 타이틀 행 감지 (예: 메이저리그사커, 잉글랜드 FA 컵 등)
        league_header = row.select_one(
            "th span, .league_title, td[colspan] b, td[colspan]"
        )
        if league_header:
          text = league_header.get_text(strip=True)
          if text and len(text) > 1 and "스코어맨" not in text:
            # 국가 아이콘이나 불필요한 기호 제거 후 리그명 추출
            current_league = text.replace("+", "").strip()
          continue

        # 2. 경기 데이터 행 파싱
        try:
          tds = row.select("td")
          if len(tds) >= 5:
            time_el = tds[1].get_text(strip=True)
            match_time = time_el if time_el else "진행중"

            home_raw = tds[2].get_text(strip=True)
            away_raw = tds[4].get_text(strip=True)

            # 대괄호 속 순위 정보 정제 (예: [ENG RYM-14] 윈게이트&핀칠리 -> 윈게이트&핀칠리)
            home_team = re.sub(r"\[.*?\]", "", home_raw).strip()
            away_team = re.sub(r"\[.*?\]", "", away_raw).strip()

            row_text = row.get_text()
            # 스코어 셀이나 행 내에 '-' 기호가 포함된 실제 경기만 수집
            if home_team and away_team and "-" in row_text:
              matches.append({
                  "id": len(matches) + 1,
                  "league": current_league,
                  "time": match_time,
                  "home": home_team,
                  "away": away_team,
                  "home_team": home_team,
                  "away_team": away_team,
                  "tournament": current_league,
                  "home_recent_stats": "실시간 수집 체급 적용",
                  "away_recent_stats": "실시간 수집 체급 적용",
                  "match_name": (
                      f"[{current_league}] {home_team} vs {away_team}"
                      f" ({match_time})"
                  ),
              })
        except Exception:
          continue
  except Exception as e:
    print(f"스코어맨 파싱 중 오류: {e}")

  return matches


def main():
  matches = fetch_scoreman_data()

  output_data = {
      "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "source": TARGET_URL,
      "matches": matches,
  }

  with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

  print(f"총 {len(matches)}개의 실시간 경기가 data.json에 갱신되었습니다.")


if __name__ == "__main__":
  main()
