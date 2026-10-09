from datetime import datetime
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from zoneinfo import ZoneInfo

def collect_and_build_details():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    kst = ZoneInfo("Asia/Seoul")
    
    try:
        # 1. 기존에 성공적으로 수집된 data.json 로드 (id, league, home, away 기준 유지)
        with open("data.json", "r", encoding="utf-8") as f:
            data_content = json.load(f)
            
        daily_matches = data_content.get("daily_matches", {})
        
        # 2. 스코어맨 메인 일정 페이지 직접 접속
        driver.get("https://www.scoreman123.com/football/fixture?f=sc1")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        updated_daily_matches = {}

        for date_key, matches in daily_matches.items():
            updated_daily_matches[date_key] = []
            print(f"📅 처리 중인 날짜: {date_key}")
            
            for match in matches:
                match_id = match.get("id")
                league = match.get("league")
                home = match.get("home")
                away = match.get("away")
                
                print(f"  - [{league}] ID {match_id}: {home} vs {away} 상세 수집 시도")
                
                try:
                    # 메인 페이지에서 해당 팀들이 포함된 행(tr)을 찾아 데이터 아이콘() 클릭
                    row_xpath = f"//tr[contains(., '{home}') and contains(., '{away}')]"
                    row_element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, row_xpath))
                    )
                    
                    # 데이터 서비스 버튼 클릭
                    data_btn = row_element.find_element(By.XPATH, ".//*[contains(text(), '')]")
                    driver.execute_script("arguments[0].click();", data_btn)
                    time.sleep(1.5) # 상세 모달 또는 페이지 로딩 대기
                    
                    # 상세 페이지/팝업 파싱
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    
                    # 필요한 메타 정보 추출 (구장, 순위, 결장자 등)
                    # 기존 data의 필드구조는 그대로 유지하고 meta_details만 추가
                    match["meta_details"] = {
                        "stadium": "", # 파싱 로직 적용
                        "rankings": [],
                        "absent_players": {"home": [], "away": []}
                    }
                    
                    updated_daily_matches[date_key].append(match)
                    
                    # 필요시 모달 닫기 또는 목록 복귀 작업 수행
                    
                except Exception as e:
                    print(f"    ⚠️ 수집 실패 (ID {match_id}): {e}")
                    # 실패하더라도 기존 데이터 구조 틀은 깨지지 않도록 원본 match 그대로 보존
                    match["meta_details"] = {}
                    updated_daily_matches[date_key].append(match)

        # 3. match_details.json에 저장 (data.json과 동일한 뼈대 유지)
        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": updated_daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print("\n🎉 match_details.json 동기화 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    collect_and_build_details()
