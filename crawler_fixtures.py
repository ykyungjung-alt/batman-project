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
import re

def run_js_click_fixtures_crawler():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    kst = ZoneInfo("Asia/Seoul")
    today = datetime.now(kst)
    date_key = today.strftime("%m-%d") # 예: '10-10'
    
    driver = webdriver.Chrome(options=options)
    
    try:
        target_url = "https://github.com/ykyungjung-alt7football/fixture?f=sc1"
        print(f"🌐 스코어맨 페이지 접속 중: {target_url}")
        driver.get(target_url)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        daily_matches = {date_key: []}
        match_id_counter = 1
        
        # 1. 전체 행 스캔하여 경기 정보 추출 준비
        rows = driver.find_elements(By.TAG_NAME, "tr")
        print(f"🔍 총 탐색 대상 행(tr) 수: {len(rows)}개")
        
        current_league = "기타 리그"
        matches_to_process = []
        
        for row in rows:
            try:
                text_content = row.text
                # 리그 헤더 행 판별
                if "VS" not in text_content and "-" not in text_content:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) <= 2 and len(row.text.strip()) > 2:
                        current_league = row.text.strip()
                        continue
                
                # 데이터 아이콘이 포함된 경기 행 판별
                if "" in text_content:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 6:
                        time_str = cols[1].text.strip()
                        home_raw = cols[3].text.strip()
                        away_raw = cols[5].text.strip()
                        
                        home_clean = re.sub(r'\[.*?\]', '', home_raw).strip()
                        away_clean = re.sub(r'\[.*?\]', '', away_raw).strip()
                        
                        if home_clean and away_clean:
                            matches_to_process.append({
                                "row_element": row,
                                "league": current_league,
                                "time": time_str,
                                "home": home_clean,
                                "away": away_clean
                            })
            except Exception:
                continue

        print(f"⚽ 수집 대상 경기 발견: 총 {len(matches_to_process)}개")

        # 2. 각 경기 행 내부의 데이터 아이콘 셀을 찾아 JavaScript로 강제 클릭 수행
        for match_info in matches_to_process:
            home = match_info["home"]
            away = match_info["away"]
            
            match_item = {
                "id": match_id_counter,
                "league": match_info["league"],
                "time": match_info["time"],
                "home": home,
                "away": away,
                "meta_details": {
                    "stadium": "",
                    "rankings": [],
                    "absent_players": {"home": [], "away": []}
                }
            }
            
            try:
                row_el = match_info["row_element"]
                # 마지막 열(데이터 아이콘 셀) 찾기
                data_cell = row_el.find_elements(By.TAG_NAME, "td")[-1]
                
                # JavaScript를 이용해 마우스 이벤트 및 클릭을 강제로 발생시킴
                driver.execute_script("""
                    arguments[0].scrollIntoView(true);
                    var evt = document.createEvent('MouseEvents');
                    evt.initEvent('click', true, true);
                    arguments[0].dispatchEvent(evt);
                """, data_cell)
                
                time.sleep(1.0) # 팝업 로딩 대기
                
                # 상세 팝업/모달 페이지 파싱
                modal_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                stadium_found = ""
                for el in modal_soup.find_all(text=True):
                    txt = el.strip()
                    if any(k in txt for k in ["Stadium", "Park", "Arena", "경기장", "구장"]):
                        if 2 < len(txt) < 35:
                            stadium_found = txt
                            break
                if stadium_found:
                    match_item["meta_details"]["stadium"] = stadium_found
                
            except Exception as e:
                # 클릭 미스가 나더라도 프로세스가 멈추지 않고 기본 데이터로 채워짐
                pass
                
            daily_matches[date_key].append(match_item)
            match_id_counter += 1

        # 3. 결과 저장
        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 총 {match_id_counter - 1}개 경기의 상세 정보가 성공적으로 정제되었습니다!")

    except Exception as e:
        print(f"❌ 크롤링 치명적 오류: {e}")
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump({"last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"), "daily_matches": {}}, f, ensure_ascii=False, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_js_click_fixtures_crawler()
