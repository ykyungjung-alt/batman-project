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
    time.sleep(6)  # 동적 데이터 렌더링 대기

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    current_league = "일반 리그"
    rows = soup.select("table tr")

    for row in rows:
      # 리그 헤더 또는 경기 Row 파싱 로직 분기
      league_header = row.select_one("span, td")
      if league_header and "베이카우스리가" in row.get_text():
        # 예시: 리그명 감지
        pass

      tds = row.select("td")
      if len(tds) >= 6:
        time_str = tds[1].get_text(strip=True)
        home_team = tds[3].get_text(strip=True)
        score = tds[4].get_text(strip=True)
        away_team = tds[5].get_text(strip=True)

        if home_team and away_team and home_team != "홈":
          matches.append({
              "tournament": current_league,
              "time": time_str if time_str else "00:00",
              "home_team": home_team,
              "away_team": away_team,
              "score": score,
          })

    if not matches:
      print(
          "⚠️ 수집된 데이터가 없어 기본 샘플 구조를 유지하거나 기존 파일을"
          " 보호합니다."
      )
      return

    data = {"matches": matches}
    with open("data.json", "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✨ 성공적으로 {len(matches)}개의 경기를 수집하여 저장했습니다.")

  except Exception as e:
    print(f"❌ 크롤링 중 오류 발생: {e}")
  finally:
    driver.quit()


if __name__ == "__main__":
  fetch_scoreman_data()
