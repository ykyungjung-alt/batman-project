from datetime import datetime
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def fetch_matches_with_selenium():
    options = Options()
    options.add_argument("--headless")  # 화면 없이 백그라운드 실행
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    matches_list = []
    
    try:
        # 예시로 타겟팅할 스포츠 정보 페이지 주소 (필요한 사이트 주소로 변경 가능)
        target_url = "https://www.livescore.co.kr" # 또는 플래시스코어 등
        driver.get(target_url)
        time.sleep(3) # 페이지 로딩 대기
        
        # [예시] 해당 페이지의 경기 항목 CSS 셀렉터에 맞춰 데이터 추출
        # elements = driver.find_elements(By.CSS_SELECTOR, ".match-row-class")
        # for el in elements:
        #     home_team = el.find_element(By.CSS_SELECTOR, ".home-team").text
        #     away_team = el.find_element(By.CSS_SELECTOR, ".away-team").text
        #     matches_list.append({"home": home_team, "away": away_team, "status": "예정"})
        
        # 임시 테스트용 데이터 (실제 파싱 로직이 안착되기 전 테스트용)
        matches_list = [
            {"id": 1, "home": "셀레니움홈A", "away": "셀레니움원정B", "status": "크롤링수집됨"}
        ]
        
    except Exception as e:
        print(f"크롤링 실행 중 오류 발생: {e}")
    finally:
        driver.quit()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data = {
        "last_updated": current_time,
        "matches": matches_list if matches_list else [{"id": 0, "home": "수집 실패", "away": "확인 요망", "status": "대기"}]
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Selenium crawler updated data.json at {current_time}")

if __name__ == "__main__":
    fetch_matches_with_selenium()
