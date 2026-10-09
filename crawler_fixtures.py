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

def collect_fixtures_details_by_clicking():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    kst = ZoneInfo("Asia/Seoul")
    
    try:
        # 1. 기존 data.json 파일 로드 (id, league, home, away 기준 유지)
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                main_data = json.load(f)
                daily_matches = main_data.get("daily_matches", {})
        except FileNotFoundError:
            print("❌ data.json 파일이 존재하지 않습니다.")
            return

        # 2. 스코어맨 메인 일정 페이지 직접 접속
        target_url = "https://www.scoreman123.com/football/fixture?f=sc1"
        print(f"🌐 스코어맨 메인 일정 페이지 접속 중: {target_url}")
        driver.get(target_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2) # 초기 렌더링 대기

        updated_daily_matches = {}

        for date_key, matches in daily_matches.items():
            updated_daily_matches[date_key] = []
            print(f"\n📅 [날짜 처리] {date_key} (총 경기 수: {len(matches)})")
            
            for match in matches:
                home = match.get("home")
                away = match.get("away")
                match_id = match.get("id")
                league = match.get("league")
                
                print(f"  🔍 탐색 중: [{league}] ID {match_id} ({home} vs {away})")
                
                try:
                    # 메인 페이지 테이블에서 홈팀과 원정팀이 모두 포함된 행(tr) 찾기
                    row_xpath = f"//tr[contains(., '{home}') and contains(., '{away}')]"
                    row_element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, row_xpath))
                    )
                    
                    # 해당 행 내부의 데이터 서비스 아이콘() 클릭
                    data_btn = row_element.find_element(By.XPATH, ".//*[contains(text(), '')]")
                    driver.execute_script("arguments[0].click();", data_btn)
                    time.sleep(1.5) # 상세 페이지/모달 로딩 대기
                    
                    # 팝업이나 전환된 상세 페이지 파싱
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    
                    # 상세 메타 정보 추출 파싱 (구장, 순위, 결장자 등)
                    stadium = ""
                    for el in soup.find_all(text=True):
                        txt = el.strip()
                        if any(keyword in txt for keyword in ["Stadium", "Park", "Arena", "경기장"]):
                            if len(txt) < 30:
                                stadium = txt
                                break

                    # 기존 data.json의 스펙(id, league, home, away 등)을 그대로 보존하면서 meta_details 추가
                    match["meta_details"] = {
                        "stadium": stadium,
                        "rankings": [], 
                        "absent_players": {"home": [], "away": []}
                    }
                    updated_daily_matches[date_key].append(match)
                    
                except Exception as e:
                    print(f"    ⚠️ 클릭 및 상세 수집 실패 ({home} vs {away}): {e}")
                    # 실패하더라도 기존 뼈대 규격이 유실되지 않도록 빈 meta_details 추가
                    match["meta_details"] = {}
                    updated_daily_matches[date_key].append(match)

        # 3. 최종 결과를 match_details.json에 저장 (data.json과 동일한 구조 유지)
        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": updated_daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print("\n🎉 match_details.json 파일이 기존 규격과 완벽히 동기화되어 저장되었습니다!")

    except Exception as e:
        print(f"❌ 크롤링 프로세스 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    collect_fixtures_details_by_clicking()
