import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# 스코어맨 실제 데이터 크롤링 및 data.json 업데이트 스크립트
TARGET_URL = "https://www.scoreman123.com/"


def fetch_scoreman_data():
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  matches = []
  try:
    response = requests.get(TARGET_URL, headers=headers, timeout=10)
    if response.status_code == 200:
      soup = BeautifulSoup(response.text, "html.parser")

      # TODO: 스코어맨 사이트의 실제 HTML 구조(리그명, 시간, 팀명 클래스 등)에 맞춰 파싱 셀렉터 지정
      # 예시 구조 파싱 (사이트 구조에 맞게 셀렉터 조정 필요)
      match_elements = soup.select(
          ".match-item"
      )  # 스코어맨 실제 경기 아이템 클래스 명으로 변경

      if match_elements:
        for idx, el in enumerate(match_elements, 1):
          league = (
              el.select_one(".league-name").text.strip()
              if el.select_one(".league-name")
              else "기본 리그"
          )
          time = (
              el.select_one(".match-time").text.strip()
              if el.select_one(".match-time")
              else "00:00"
          )
          home = (
              el.select_one(".home-team").text.strip()
              if el.select_one(".home-team")
              else "홈 팀"
          )
          away = (
              el.select_one(".away-team").text.strip()
              if el.select_one(".away-team")
              else "원정 팀"
          )
          status = (
              el.select_one(".match-status").text.strip()
              if el.select_one(".match-status")
              else "진행중"
          )

          matches.append({
              "id": idx,
              "league": league,
              "time": time,
              "home": home,
              "away": away,
              "status": status,
          })
  except Exception as e:
    print(f"크롤링 중 오류 발생: {e}")

  # 크롤링된 데이터가 없거나 테스트 유지 시 기존 구조 유지 방어 코드
  if not matches:
    matches = [{
        "id": 1,
        "league": "실시간 연동 대기중",
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

  print("data.json 업데이트 완료")


if __name__ == "__main__":
  fetch_scoreman_data()
