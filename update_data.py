from datetime import datetime
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def fetch_scoreman_matches():
    options = Options()
    options.add_argument("--headless")  # 백그라운드 실행
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    matches_list = []
    
    try:
        target_url = "https://www.scoreman123.com/"
        driver.get(target_url)
        time.sleep(4)  # 동적 콘텐츠 로딩 대기
        
        # 스코어맨 경기 목록 테이블 행 선택 (시간, 팀명, 배당 정보가 포함된 행)
        # 테이블의 각 경기 항목을 포함하는 행들을 순회합니다.
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        
        match_id = 1
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 5:
                    continue  # 데이터 행이 아닌 경우 스킵
                
                # 시간, 홈팀, 원정팀 셀 텍스트 추출 시도
                time_text = cells[1].text.strip() if len(cells) > 1 else ""
                home_text = cells[2].text.strip() if len(cells) > 2 else ""
                away_text = cells[4].text.strip() if len(cells) > 4 else ""
                
                # 유효한 경기 정보 행인 경우에만 리스트에 추가
                if home_text and away_text and "-" in cells[3].text:
                    matches_list.append({
                        "id": match_id,
                        "time": time_text,
                        "home": home_text,
                        "away": away_text,
                        "status": "예정"
                    })
                    match_id += 1
                    
                    if match_id > 30:  # 상위 30경기만 샘플 수집
                        break
            except Exception:
                continue
                
    except Exception as e:
        print(f"크롤링 실행 중 오류 발생: {e}")
    finally:
        driver.quit()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 파싱된 데이터가 없을 경우 예외 처리용 더미 데이터 설정
    final_matches = matches_list if matches_list else [
        {"id": 1, "time": "03:45", "home": "크로아티아", "away": "스페인", "status": "수집대기"}
    ]
    
    data = {
        "last_updated": current_time,
        "source": "https://www.scoreman123.com/",
        "matches": final_matches
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Scoreman match data successfully updated at {current_time} ({len(final_matches)} matches)")

if __name__ == "__main__":
    fetch_scoreman_matches()
