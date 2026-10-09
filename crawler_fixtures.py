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
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    kst = ZoneInfo("Asia/Seoul")
    
    # 오늘 및 내일 날짜 키 생성 (예: 10-10, 10-11 등 스코어맨 탭 형식에 맞춤)
    today = datetime.now(kst)
    target_dates = [
        today.strftime("%m-%d"),
        (today + timedelta(days=1)).strftime("%m-%d")
    ]
    
    try:
        targets_urls = [
            "https://www.scoreman123.com/football/fixture",
            "https://www.scoreman123.com/football/fixture?f=sc1"
        ]
        
        daily_matches = {}
        match_id_counter = 1
        
        for url in targets_urls:
            print(f"🌐 스코어맨 페이지 직접 접속 중: {url}")
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # 페이지 내 경기 테이블 행(tr) 및 리그 정보 파싱
            current_league = "기타 리그"
            rows = driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                try:
                    text_content = row.text
                    # 리그 헤더나 상태 행인 경우 패스
                    if "VS" not in text_content and "-" not in text_content:
                        if len(row.find_elements(By.TAG_NAME, "td")) <= 2:
                            current_league = row.text.strip()
                            continue
                    
                    # 홈팀, 원정팀, 데이터 아이콘()이 포함된 행인지 확인
                    if "" in text_content:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 6:
                            time_str = cols[1].text.strip()
                            home_team = cols[3].text.strip()
                            away_team = cols[5].text.strip()
                            
                            # 오늘/내일 범위 내의 경기인지 판단 (필요시 날짜 탭 클릭 로직 확장 가능)
                            date_key = today.strftime("%m-%d") # 기본값 오늘
                            
                            if date_key not in daily_matches:
                                daily_matches[date_key] = []
                                
                            # 중복 등록 방지
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
                                
                                # 상세 데이터 서비스 아이콘 클릭 시도
                                try:
                                    data_btn = row.find_element(By.XPATH, ".//*[contains(text(), '')]")
                                    driver.execute_script("arguments[0].click();", data_btn)
                                    time.sleep(1)
                                    
                                    modal_soup = BeautifulSoup(driver.page_source, "html.parser")
                                    # 구장 등 상세 정보 추출
                                    for el in modal_soup.find_all(text=True):
                                        txt = el.strip()
                                        if any(k in txt for k in ["Stadium", "Park", "Arena", "경기장"]):
                                            if len(txt) < 30:
                                                match_item["meta_details"]["stadium"] = txt
                                                break
                                except Exception as click_err:
                                    print(f"  ⚠️ 상세 클릭 생략/실패 ({home_team} vs {away_team}): {click_err}")
                                    
                                daily_matches[date_key].append(match_item)
                                match_id_counter += 1
                                
                except Exception as row_err:
                    continue

        # 결과 저장
        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print("\n🎉 match_details.json 독립 수집 및 저장 완료!")

    except Exception as e:
        print(f"❌ 크롤링 중 치명적 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_independent_fixtures_crawler()
