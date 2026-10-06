from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
import requests

TARGET_URL = "https://www.scoreman123.com/football/fixture"


def fetch_scoreman_matches():
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Referer": TARGET_URL,
  }
  matches = []
  try:
    response = requests.get(TARGET_URL, headers=headers, timeout=10)
    if response.status_code == 200:
      soup = BeautifulSoup(response.text, "html.parser")
      current_league = "해외축구"
      rows = soup.select("tr")

      for row in rows:
        # 리그 타이틀 및 헤더 감지
        league_el = row.select_one("th, td[colspan], .league_title")
        if league_el and not row.select("td:nth-child(3)"):
          text = league_el.get_text(strip=True)
          if text and len(text) > 1 and "스코어맨" not in text:
            current_league = text.replace("+", "").strip()
          continue

        # 실시간 경기 데이터 행 파싱
        try:
          tds = row.select("td")
          if len(tds) >= 5:
            time_str = tds[1].get_text(strip=True)
            home_raw = tds[2].get_text(strip=True)
            score_str = tds[3].get_text(strip=True)
            away_raw = tds[4].get_text(strip=True)

            # 대괄호 메타데이터 정제 (예: [5] 시카고 파이어 -> 시카고 파이어)
            home_team = re.sub(r"\[.*?\]", "", home_raw).strip()
            away_team = re.sub(r"\[.*?\]", "", away_raw).strip()

            # 유효한 경기 행만 추출
            if home_team and away_team and("-" in score_str or ":" in time_str):
              matches.append({
                  "id": len(matches) + 1,
                  "league": current_league,
                  "time": time_str if time_str else "진행중",
                  "home": home_team,
                  "away": away_team,
                  "home_team": home_team,
                  "away_team": away_team,
                  "tournament": current_league,
                  "score": score_str,
                  "status": (
                      tds[1].get_text(strip=True)
                      if "전반" in row.get_text() or "후반" in row.get_text()
                      else "대기"
                  ),
                  "match_name": (
                      f"[{current_league}] {home_team} vs {away_team}"
                      f" ({time_str})"
                  ),
              })
        except Exception:
          continue
  except Exception as e:
    print(f"크롤링 중 오류 발생: {e}")

  return matches


def main():
  matches = fetch_scoreman_matches()

  output_data = {
      "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "source": TARGET_URL,
      "matches": matches,
  }

  with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

  print(
      f"총 {len(matches)}개의 실시간 경기가 data.json에 성공적으로 갱신되었습니다."
  )


if __name__ == "__main__":
  main()
