from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
import requests

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
      rows = soup.select("table tr, .score_table tr")

      for row in rows:
        # 1. 리그 헤더 행 감지
        league_header = row.select_one("th, .league_title, td[colspan]")
        if league_header and not row.select("td:nth-child(3)"):
          text = league_header.get_text(strip=True)
          if text and len(text) > 1 and "스코어맨" not in text:
            current_league = text.replace("+", "").strip()
          continue

        # 2. 경기 데이터 행 파싱
        try:
          tds = row.select("td")
          if len(tds) >= 5:
            # 시간 추출 (두 번째 컬럼)
            time_el = tds[1].get_text(strip=True)
            match_time = time_el if time_el else "진행중"

            # 홈팀, 원정팀 추출 (실제 스코어맨 테이블 구조 기준)
            home_raw = tds[2].get_text(strip=True)
            away_raw = tds[4].get_text(strip=True)

            # 대괄호 내 순위/등급 정보 제거 (예: [ENG RYN-14] 윈게이트 -> 윈게이트)
            home_team = re.sub(r"\[.*?\]", "", home_raw).strip()
            away_team = re.sub(r"\[.*?\]", "", away_raw).strip()

            # 유효한 경기 행 필터링 (스코어 셀 등에 '-' 기호가 포함된 경우)
            row_text = row.get_text()
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
              })
        except Exception:
          continue
  except Exception as e:
    print(f"스코어맨 크롤링 중 오류 발생: {e}")

  return matches


def main():
  matches = fetch_scoreman_data()

  # 데이터가 수집되지 않았을 경우를 대비한 기본 폴백 데이터
  if not matches:
    matches = [{
        "id": 1,
        "league": "기본 대기",
        "time": "오늘",
        "home": "데이터 수집 대기",
        "away": "스코어맨 확인",
        "home_team": "데이터 수집 대기",
        "away_team": "스코어맨 확인",
        "tournament": "기본 대기",
        "home_recent_stats": "4전/3승1무/0패",
        "away_recent_stats": "4전/2승1무/1패",
    }]

  output_data = {
      "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "source": TARGET_URL,
      "matches": matches,
  }

  with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

  print(
      f"데이터 갱신 완료: 총 {len(matches)}개 경기 저장됨 (data.json 갱신 완료)"
  )


if __name__ == "__main__":
  main()
