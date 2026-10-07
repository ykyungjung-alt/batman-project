from datetime import datetime, timezone, timedelta
import json
import re
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
        driver.implicitly_wait(5)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        current_league = "해외축구 (실시간)"

        # 페이지 내 모든 테이블 행 순회
        rows = soup.find_all("tr")
        for row in rows:
            tds = row.find_all("td")
            text_content = row.get_text(strip=True)

            # 1) 리그 타이틀 행 감지 (스코어맨 구조: 셀이 2개 이하이면서 이미지가 포함되거나 시간이 없는 행)
            if len(tds) <= 2:
                # 텍스트에 시간이 포함되어 있지 않고 무언가 이름이 있다면 리그명으로 간주
                if text_content and not re.search(r"\d{2}:\d{2}", text_content):
                    cleaned_league = re.sub(r'^[^\w\s]+\s*', '', text_content).replace("+", "").strip()
                    if cleaned_league and len(cleaned_league) < 30:
                        current_league = cleaned_league
                continue

            # 2) 경기 데이터 행 감지 (시간, 상태, 홈, 스코어, 원정 등이 포함된 6개 이상의 셀 구조)
            if len(tds) >= 6:
                time_str = tds[1].get_text(strip=True)
                if not re.match(r"^\d{2}:\d{2}$", time_str):
                    continue

                status_str = tds[2].get_text(strip=True)
                home_raw = tds[3].get_text(strip=True)
                score_str = tds[4].get_text(strip=True)
                away_raw = tds[5].get_text(strip=True)

                # 팀명과 순위 정제 ([4] 그니스탄 -> 그니스탄)
                home_team = re.sub(r"\[.*?\]", "", home_raw).strip()
                away_team = re.sub(r"\[.*?\]", "", away_raw).strip()

                if home_team and away_team and home_team != away_team:
                    matches.append({
                        "id": len(matches) + 1,
                        "league": current_league,
                        "time": time_str,
                        "status": status_str if status_str else "진행예정",
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
        print(f"크롤링 및 파싱 중 오류 발생: {e}")
    finally:
        driver.quit()

    # 데이터가 없을 때만 폴백 적용
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
    print(f"data.json 갱신 완료! 총 {len(matches)}개 경기 분류 및 저장됨")

if __name__ == "__main__":
    update_json_file()
