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
    time.sleep(7)  # 동적 렌더링 및 mintable 로딩 대기

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    current_league = "해외축구 실시간"

    # mintable 영역 안의 테이블 행들을 순회
    mintable = soup.select_one("#mintable")
    target_rows = mintable.select("tr") if mintable else soup.select("tr")

    for row in target_rows:
      text = row.get_text(strip=True)
      tds = row.select("td")

      # 1. 리그 헤더 행 판별 (셀이 적고 vs가 없는 텍스트, 예: 베이카우스리가, 세리에 A 베타노)
      if len(tds) <= 2 and text and " vs " not in text:
        clean_text = (
            text.replace("★", "")
            .replace("", "")
            .replace("", "")
            .strip()
        )
        if clean_text and len(clean_text) < 30:
          current_league = clean_text
          continue

      # 2. 경기 데이터 행 판별 (시간, 홈, 스코어, 원정 포맷 구조)
      if len(tds) >= 6:
        time_str = tds[1].get_text(strip=True)
        home_team = tds[3].get_text(strip=True)
        score = tds[4].get_text(strip=True)
        away_team = tds[5].get_text(strip=True)

        if home_team and away_team and home_team != "홈":
          matches.append({
              "tournament": current_league,
              "time": time_str if time_str else "00:00",
              "home_team": home_team.replace("[", "").replace("]", "").strip(),
              "away_team": away_team.replace("[", "").replace("]", "").strip(),
              "score": score if score else "-",
          })

    # 만약 위 조건에서 수집되지 않았다면 전체 행을 대상으로 유연한 백업 파싱 수행
    if not matches:
      print("⚠️ 1차 파싱 미달, 전체 행 대상 예비 탐색 시도...")
      for row in target_rows:
        cells = [td.get_text(strip=True) for td in row.select("td")]
        if len(cells) >= 6 and cells[3] != "홈" and cells[5]:
          matches.append({
              "tournament": current_league,
              "time": cells[1] if cells[1] else "00:00",
              "home_team": cells[3].replace("[", "").replace("]", "").strip(),
              "away_team": cells[5].replace("[", "").replace("]", "").strip(),
              "score": cells[4] if cells[4] else "-",
          })

    if not matches:
      print("❌ 유효한 경기를 찾지 못했습니다.")
      return

    data = {"matches": matches}
    with open("data.json", "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
    print(
        f"✨ 총 {len(matches)}개의 실시간 경기를 성공적으로 긁어와 저장했습니다."
    )

  except Exception as e:
    print(f"❌ 크롤링 중 오류 발생: {e}")
  finally:
    driver.quit()


if __name__ == "__main__":
  fetch_scoreman_data()
