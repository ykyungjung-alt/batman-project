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

def run_independent_fixtures_crawler():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    kst = ZoneInfo("Asia/Seoul")
    
    today = datetime.now(kst)
    date_key = today.strftime("%m-%d") # 예: '10-10'
    
    try:
        target_url = "https://www.scoreman123.com/football/fixture?f=sc1"
        print(f"🌐 스코어맨 일정 페이지 직접 접속 중: {target_url}")
        driver.get(target_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3) # 초기 렌더링 및 동적 로딩 대기
        
        daily_matches = {date_key: []}
        match_id_counter = 1
        
        rows = driver.find_elements(By.TAG_NAME, "tr")
        current_league = "기타 리그"
        
        for row in rows:
            try:
                text_content = row.text
                # 리그 구분 행 처리 (VS나 -가 없고 td 개수가 적은 경우)
                if "VS" not in text_content and "-" not in text_content:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) <= 2:
                        league_text = row.text.strip()
                        if league_text:
                            current_league = league_text
                        continue
                
                # 데이터 서비스 아이콘()이 포함된 실제 경기 행 파싱
                if "" in text_content:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 6:
                        time_str = cols[1].text.strip()
                        home_team = cols[3].text.strip()
                        away_team = cols[5].text.strip()
                        
                        # 중복 수집 방지
                        if not any(m["home"] == home_team and m["away"] == away_team for m in daily_matches[date_key]):
                            match_item = {
                                "id": match_id_counter,
                                "league": current_league,
                                "time": time_str,
                                "home": home_team,
                                "away": away_team,
                                "meta_details": {
                                    "stadium": "",
                                    "rankings": [],
                                    "absent_players": {"home": [], "away": []}
                                }
                            }
                            
                            # 데이터 아이콘 클릭 및 상세 정보 파싱
                            try:
                                data_btn = row.find_element(By.XPATH, ".//*[contains(text(), '')]")
                                driver.execute_script("arguments[0].click();", data_btn)
                                time.sleep(1.2) # 상세 팝업/모달 로딩 대기
                                
                                modal_soup = BeautifulSoup(driver.page_source, "html.parser")
                                
                                # 구장 및 상세 메타 텍스트 정제 추출
                                stadium_found = ""
                                for el in modal_soup.find_all(text=True):
                                    txt = el.strip()
                                    if any(k in txt for k in ["Stadium", "Park", "Arena", "경기장", "구장"]):
                                        if len(txt) < 35 and len(txt) > 2:
                                            stadium_found = txt
                                            break
                                            
                                if stadium_found:
                                    match_item["meta_details"]["stadium"] = stadium_found
                                    
                            except Exception:
                                # 클릭 실패 시에도 기본 구조 유지
                                pass
                                
                            daily_matches[date_key].append(match_item)
                            match_id_counter += 1
                            
            except Exception:
                continue

        # 결과 데이터 빌드 및 저장
        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 match_details.json 독립 빌드 완료! (총 수집 경기: {match_id_counter - 1}개)")

    except Exception as e:
        print(f"❌ 크롤링 치명적 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_independent_fixtures_crawler()
