from datetime import datetime
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def fetch_scoreman_data():
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
        time.sleep(4)  # 동적 데이터 로딩 대기
        
        # 스코어맨 경기 목록 테이블의 행들을 셀렉터로 수집
        # (사이트 구조에 맞춘 행 추출 예시)
        match_rows = driver.find_elements(By.CSS_SELECTOR, "table tr, .match-row-class")
        
        count = 0
        for row in match_rows:
            try:
                text_content = row.text.strip()
                if not text_content:
                    continue
                
                # 예시 파싱 구조: 홈팀 / 원정팀 / 시간 등의 텍스트가 포함된 행을 필터링
                # 실제 DOM 구조에 맞추어 세부 클래스명(.home, .away 등)을 튜닝할 수 있습니다.
                matches_list.append({
                    "id": count + 1,
                    "raw_info": text_content,
                    "status": "수집완료"
                })
                count += 1
                if count >= 20:  # 상위 20경기만 샘플 수집
                    break
            except Exception:
                continue
                
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data = {
        "last_updated": current_time,
        "source": "https://www.scoreman123.com/",
        "matches": matches_list if matches_list else [{"id": 0, "raw_info": "수집된 데이터 없음", "status": "대기"}]
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Scoreman data updated at {current_time}")

if __name__ == "__main__":
    fetch_scoreman_data()
