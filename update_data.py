import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def fetch_scoreman_data():
  options = Options()
  options.add_argument("--headless")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--disable-gpu")
  options.add_argument("window-size=1920x1080")
  options.add_argument(
      "User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  )

  driver = webdriver.Chrome(
      service=Service(ChromeDriverManager().install()), options=options
  )

  matches = []
  try:
    url = "https://www.scoreman123.com/football/fixture"
    driver.get(url)
    time.sleep(7)  # 동적 렌더링 대기 시간 충분히 확보

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    current_league = "해외축구 실시간"
    rows = soup.select("table tr")

    for row in rows:
      text = row.get_text(strip=True)
      tds = row.select("td")

      # 1. 리그 헤더 행 감지 (스코어맨 구조상 리그명은 셀이 적고 별도 표기됨)
      # 예: [핀란드] 베이카우스리가, [브라질] 세리에 A 베타노 등
      if len(tds) <= 2 and text and " vs " not in text:
        clean_text = text.replace("★", "").replace("", "").strip()
        if clean_text and len(clean_text) < 30:
          current_league = clean_text
          continue

      # 2. 실제 경기 데이터 행 추출 (시간, 홈, 스코어, 원정 포맷 검증)
      if len(tds) >= 6:
        time_str = tds[1].get_text(strip=True)
        home_team = tds[3].get_text(strip=True)
        score = tds[4].get_text(strip=True)
        away_team = tds[5].get_text(strip=True)

        # 팀명과 스코어 구분이 명확한 실전 경기만 수집
        if home_team and away_team and home_team != "홈" and ("-" in score or score == "-"):
          matches.append({
              "tournament": current_league,
              "time": time_str if time_str else "00:00",
              "home_team": home_team.replace("[", "").replace("]", "").strip(),
              "away_team": away_team.replace("[", "").replace("]", "").strip(),
              "score": score,
          })

    # 만약 위 조건에 안 걸렸을 경우를 대비한 유연한 2차 폴백 파싱
    if not matches:
      print("⚠️ 1차 파싱 실패, 2차 전체 셀 순회 파싱 시도...")
      for row in rows:
        cells = [td.get_text(strip=True) for td in row.select("td")]
        if len(cells) >= 6 and ("-" in cells[4] or cells[4] == "-"):
          if cells[3] != "홈" and cells[5]:
            matches.append({
                "tournament": current_league,
                "time": cells[1] if cells[1] else "00:00",
                "home_team": cells[3].replace("[", "").replace("]", "").strip(),
                "away_team": cells[5].replace("[", "").replace("]", "").strip(),
                "score": cells[4],
            })

    # 데이터가 아예 안 긁혀도 비상용 샘플 대신 현재 시점의 기본 경기라도 넣어 대시보드가 안 죽게 방어
    if not matches:
      print("❌ 실시간 수집 경기 없음. 기본 비상 데이터 삽입")
      matches = [{
          "tournament": "실시간 수집 대기중",
          "time": "00:00",
          "home_team": "데이터 수집 대기",
          "away_team": "잠시 후 갱신",
          "score": "- - -"
      }]

    data = {"matches": matches}
    with open("data.json", "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✨ 총 {len(matches)}개의 경기가 data.json에 반영되었습니다.")

  except Exception as e:
    print(f"❌ 크롤링 중 오류 발생: {e}")
  finally:
    driver.quit()


if __name__ == "__main__":
  fetch_scoreman_data()
