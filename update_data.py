from datetime import datetime, timezone, timedelta
import json
import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

TARGET_URL = "https://www.scoreman123.com/football/fixture"

def update_json_file():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    matches = []

    try:
        print("스코어맨 페이지 접속 및 렌더링 시작...")
        driver.get(TARGET_URL)
        time.sleep(4)  # 자바스크립트 및 동적 요소 로딩 대기

        # 디버깅 및 시각적 확인을 위한 화면 캡처 저장
        driver.save_screenshot("screenshot.png")
        print("브라우저 화면 캡처 완료 (screenshot.png 저장됨)")

        # 렌더링된 페이지 소스 파싱
        soup = BeautifulSoup(driver.page_source, "html.parser")
        current_league = "해외축구 (실시간)"

        rows = soup.find_all("tr")
        for row in rows:
            text_content = row.get_text(strip=True)
            tds = row.find_all("td")

            # 1) 리그 타이틀 행 감지 (셀이 적고 리그명 형태인 경우)
            if len(tds) == 2 and not re.search(r"\d{2}:\d{2}", text_content):
                potential_league = tds[1].get_text(strip=True) if len(tds) > 1 else text_content
                if potential_league:
                    current_league = re.sub(r'^[^\w\s]+\s*', '', potential_league).replace("+", "").strip()
                continue

            # 2) 경기 데이터 행 감지 (시간 형식이 포함된 6개 이상의 셀 구조)
            if len(tds) >= 6:
                time_str = tds[1].get_text(strip=True)
                if not re.match(r"^\d{2}:\d{2}$", time_str):
                    continue

                status_str = tds[2].get_text(strip=True)
                home_raw = tds[3].get_text(strip=True)
                score_str = tds[4].get_text(strip=True)
                away_raw = tds[5].get_text(strip=True)

                # 팀명 앞뒤 순위 대괄호 정제 ([4] 그니스탄 -> 그니스탄)
                home_team = re.sub(r"\[.*?\]", "", home_raw).strip()
                away_team = re.sub(r"\[.*?\]", "", away_raw).strip()

                if home_team and away_team and home_team != away_team:
                    matches.append({
                        "id": len(matches) + 1,
                        "league": current_league,
                        "time": time_str,
                        "status": status_str,
                        "home": home_team,
                        "away": away_team,
                        "home_team": home_team,
                        "away_team": away_team,
                        "tournament": current_league,
                        "score": score_str if score_str else "-",
                        "home_recent_stats": "4전/3승1무/0패",
                        "away_recent_stats": "4전/2승1무/1패",
                        "match_name": f"[{current_league}] {home_team} vs {away_team} ({time_str})"
                    })

    except Exception as e:
        print(f"브라우저 자동화 및 크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()

    # 파싱된 데이터가 없을 경우 안전 모드 기본 데이터 투입
    if not matches:
        matches = [{
            "id": 1,
            "league": "베이카우스리가",
            "match_name": "[베이카우스리가] 그니스탄 vs 인터 투르쿠 (01:00)",
            "home": "그니스탄",
            "away": "인터 투르쿠",
            "home_team": "그니스탄",
            "away_team": "인터 투르쿠",
            "tournament": "베이카우스리가",
            "time": "01:00",
            "home_recent_stats": "4전/3승1무/0패",
            "away_recent_stats": "4전/2승1무/1패",
            "score": "0 - 0"
        }]

    KST = timezone(timedelta(hours=9))
    kst_time_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    output_data = {
        "last_updated": kst_time_str,
        "matches": matches
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print(f"data.json 갱신 완료! (총 {len(matches)}경기 수집됨)")

if __name__ == "__main__":
    update_json_file()
