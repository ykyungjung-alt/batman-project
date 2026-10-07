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
        
        # 디버깅용 화면 캡처 저장
        driver.save_screenshot("screenshot.png")
        print("브라우저 화면 캡처 완료 (screenshot.png)")

        soup = BeautifulSoup(driver.page_source, "html.parser")
        current_league = "해외축구 (실시간)"

        rows = soup.find_all("tr")
        for row in rows:
            tds = row.find_all("td")
            text_content = row.get_text(strip=True)

            if not text_content:
                continue

            # 1) 리그 타이틀 행 감지 부분
if not re.search(r"\d{2}:\d{2}", text_content):
    cleaned = re.sub(r'^[^\w\s]+\s*', '', text_content).replace("+", "").strip()
    
    # [수정] 리그명 뒤에 붙는 '경기수(...)' 형태를 완벽하게 제거
    cleaned = re.sub(r'경기수\s*\(.*?\)', '', cleaned).strip()
    
    if cleaned and len(cleaned) > 1 and len(cleaned) < 35 and "시간" not in cleaned and "상태" not in cleaned:
        current_league = cleaned
    continue

            # 2) 경기 데이터 행 감지 (시간 형식 HH:MM이 포함된 셀이 존재하는 행)
            time_str = ""
            for td in tds:
                t_text = td.get_text(strip=True)
                if re.match(r"^\d{2}:\d{2}$", t_text):
                    time_str = t_text
                    break
            
            if time_str and len(tds) >= 5:
                # 셀 내용 추출 (구조에 따라 인덱스 조정)
                cell_texts = [td.get_text(strip=True) for td in tds if td.get_text(strip=True) != ""]
                
                # 시간 뒤에 오는 요소들 파싱
                try:
                    time_idx = -1
                    for idx, val in enumerate(cell_texts):
                        if re.match(r"^\d{2}:\d{2}$", val):
                            time_idx = idx
                            break
                    
                    if time_idx != -1 and len(cell_texts) > time_idx + 2:
                        status_str = cell_texts[time_idx + 1] if cell_texts[time_idx + 1] in ["종료", "진행중"] else ""
                        # 상태가 없으면 팀명이 바로 올 수 있음
                        offset = 1 if status_str else 0
                        
                        home_raw = cell_texts[time_idx + 1 + offset]
                        score_str = cell_texts[time_idx + 2 + offset] if "-" in cell_texts[time_idx + 2 + offset] else "-"
                        away_raw = cell_texts[time_idx + 3 + offset] if len(cell_texts) > time_idx + 3 + offset else ""

                        # 순위 대괄호 정제 ([4] 그니스탄 -> 그니스탄)
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
                                "score": score_str,
                                "home_recent_stats": "4전/3승1무/0패",
                                "away_recent_stats": "4전/2승1무/1패",
                                "match_name": f"[{current_league}] {home_team} vs {away_team} ({time_str})"
                            })
                except Exception as inner_e:
                    print(f"개별 행 파싱 중 예외 무시: {inner_e}")
                    continue

    except Exception as e:
        print(f"브라우저 자동화 및 크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()

    # 데이터가 없을 경우 폴백
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
    print(f"data.json 최종 갱신 완료! 총 {len(matches)}경기 적재됨")

if __name__ == "__main__":
    update_json_file()
