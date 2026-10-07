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
    time.sleep(6)  # 자바스크립트 렌더링 대기

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    current_league = "일반 리그"
    rows = soup.select("table tr")

    for row in rows:
      # 1. 리그 헤더 행 판별 (예: 베이카우스리가, 세리에 A 베타노 등)
      league_th = row.select_one("th, td")
      if league_th and ("베이카우스리가" in row.get_text() or "세리에" in row.get_text() or "리그" in row.get_text()):
        text_val = row.get_text(strip=True)
        if len(text_val) < 30 and not " vs " in text_val:
          current_league = text_val

      # 2. 경기 데이터 행 파싱
      tds = row.select("td")
      if len(tds) >= 6:
        time_str = tds[1].get_text(strip=True)
        home_team = tds[3].get_text(strip=True)
        score = tds[4].get_text(strip=True)
        away_team = tds[5].get_text(strip=True)

        # 유효한 팀명과 시간이 있는 경우에만 추가
        if home_team and away_team and home_team != "홈":
          matches.append({
              "tournament": current_league,
              "time": time_str if time_str else "00:00",
              "home_team": home_team,
              "away_team": away_team,
              "score": score,
          })

    if not matches:
      print("⚠️ 수집된 데이터가 없습니다. 기존 구조를 유지합니다.")
      return

    data = {"matches": matches}
    with open("data.json", "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✨ 총 {len(matches)}개의 실시간 경기를 수집했습니다.")

  except Exception as e:
    print(f"❌ 크롤링 중 오류 발생: {e}")
  finally:
    driver.quit()


if __name__ == "__main__":
  fetch_scoreman_data()

if __name__ == "__main__":
  fetch_scoreman_data()
