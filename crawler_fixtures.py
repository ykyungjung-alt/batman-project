from datetime import datetime, timedelta
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from zoneinfo import ZoneInfo

def collect_fixtures_and_details_by_click():
    options = Options()
    options.add_argument("--headless") # 필요시 화면을 보려면 주석 처리
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    kst = ZoneInfo("Asia/Seoul")
    
    try:
        # 1. 메인 일정 데이터(data.json) 로드
        with open("data.json", "r", encoding="utf-8") as f:
            main_data = json.load(f)
            
        daily_matches = main_data.get("daily_matches", {})
        
        # 2. 메인 페이지 접속 (예: 스코어맨 메인 일정 페이지 URL 입력 필요)
        main_url = "https://www.scoreman123.com/" # 실제 메인 일정 페이지 주소
        driver.get(main_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        updated_daily_matches = {}

        for date_key, matches in daily_matches.items():
            updated_daily_matches[date_key] = []
            
            for match in matches:
                home_team = match.get("home")
                away_team = match.get("away")
                print(f"🎯 경기 탐색 및 클릭 시도: {home_team} vs {away_team}")
                
                try:
                    # 메인 페이지에서 해당 홈/원정 팀 이름이 포함된 요소 찾기
                    # (사이트 구조에 따라 XPath나 CSS 셀렉터는 조정이 필요할 수 있습니다)
                    match_element = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), '{home_team}')]/ancestor::tr | //*[contains(text(), '{home_team}')]/.."))
                    )
                    
                    # 클릭하여 상세 페이지로 진입
                    driver.execute_script("arguments[0].click();", match_element)
                    time.sleep(2) # 페이지 전환 또는 팝업 로딩 대기
                    
                    # 상세 페이지 진입 후 소스 파싱
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    
                    # --- 여기서부터 상세 내용 발췌 로직 ---
                    stadium = ""
                    round_info = ""
                    # 예: 구장, 라운드, 순위, 결장자 파싱 로직 수행
                    # ... (기존 파싱 코드 적용)
                    
                    match["meta_details"] = {
                        "stadium": stadium,
                        "round_info": round_info,
                        # 기타 수집 데이터...
                    }
                    updated_daily_matches[date_key].append(match)
                    
                    # 상세 페이지에서 다시 메인 목록으로 돌아오기 (뒤로 가기)
                    driver.back()
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"    ⚠️ 클릭 또는 상세 수집 실패 ({home_team} vs {away_team}): {e}")
                    updated_daily_matches[date_key].append(match)

        # 3. 최종 결과를 match_details.json에 저장
        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": updated_daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print("\n🎉 클릭 기반 상세 메타 정보 수집 및 `match_details.json` 저장 완료!")

    except Exception as e:
        print(f"❌ 전체 프로세스 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    collect_fixtures_and_details_by_click()
