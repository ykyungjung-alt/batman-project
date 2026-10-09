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

def run_detailed_click_crawler():
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
        target_url = "https://www.scoreman123.com/football/fixture?f=sc1"
        print(f"🌐 메인 일정 페이지 접속 중: {target_url}")
        driver.get(target_url)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        daily_matches = {date_key: []}
        match_id_counter = 1
        
        # 1차 스캔: 메인 페이지의 모든 행(tr) 파악
        rows = driver.find_elements(By.TAG_NAME, "tr")
        print(f"🔍 총 탐색 대상 행(tr) 수: {len(rows)}개")
        
        current_league = "기타 리그"
        valid_matches_info = []
        
        # 순회하며 리그명 및 데이터 아이콘()이 있는 경기 행 추출
        for row in rows:
            try:
                text_content = row.text
                if "VS" not in text_content and "-" not in text_content:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) <= 2 and len(row.text.strip()) > 2:
                        current_league = row.text.strip()
                        continue
                
                if "" in text_content:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 6:
                        time_str = cols[1].text.strip()
                        home_raw = cols[3].text.strip()
                        away_raw = cols[5].text.strip()
                        
                        home_clean = re.sub(r'\[.*?\]', '', home_raw).strip()
                        away_clean = re.sub(r'\[.*?\]', '', away_raw).strip()
                        
                        if home_clean and away_clean:
                            valid_matches_info.append({
                                "row_element": row,
                                "league": current_league,
                                "time": time_str,
                                "home": home_clean,
                                "away": away_clean
                            })
            except Exception:
                continue

        print(f"⚽ 유효한 경기 발견: 총 {len(valid_matches_info)}개. 상세 정보 수집(클릭)을 시작합니다.")

        # 2차 순회: 각 경기의 데이터 아이콘을 직접 클릭하여 상세 정보 파싱
        for idx, match_info in enumerate(valid_matches_info):
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
                # DOM이 변경될 수 있으므로 매번 해당 행을 다시 찾거나 안전하게 참조
                row_el = match_info["row_element"]
                data_btn = row_el.find_element(By.XPATH, ".//*[contains(text(), '')]")
                
                # 자바스크립트로 강제 클릭 이벤트 실행 (가려짐 방지)
                driver.execute_script("arguments[0].click();", data_btn)
                time.sleep(1.2) # 상세 모달/페이지 로딩 대기
                
                # 상세 팝업 내부 파싱
                modal_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # 구장 정보 탐색
                stadium_found = ""
                for el in modal_soup.find_all(text=True):
                    txt = el.strip()
                    if any(k in txt for k in ["Stadium", "Park", "Arena", "경기장", "구장"]):
                        if 2 < len(txt) < 35:
                            stadium_found = txt
                            break
                if stadium_found:
                    match_item["meta_details"]["stadium"] = stadium_found
                
                # 필요시 뒤로 가기 혹은 모달 닫기 (메인 페이지 유지)
                # 만약 새 창이나 팝업 레이어라면 esc나 닫기 버튼 처리 필요할 수 있음
                
            except Exception as e:
                # 클릭 또는 상세 파싱 실패 시 로그를 남기고 기본 뼈대 유지
                print(f"  ⚠️ 상세 수집 실패 [{home} vs {away}]: {e}")
            
            daily_matches[date_key].append(match_item)
            match_id_counter += 1

        # 결과 저장
        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 총 {match_id_counter - 1}개 경기의 상세 정보(클릭 추출) 연동 완료!")

    except Exception as e:
        print(f"❌ 치명적 오류 발생: {e}")
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump({"last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"), "daily_matches": {}}, f, ensure_ascii=False, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_detailed_click_crawler()
