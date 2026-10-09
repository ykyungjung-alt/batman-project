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

def run_independent_fixtures_crawler():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    kst = ZoneInfo("Asia/Seoul")
    today = datetime.now(kst)
    date_key = today.strftime("%m-%d") # 예: '10-10' 형식
    
    driver = webdriver.Chrome(options=options)
    
    try:
        target_url = "https://www.scoreman123.com/football/fixture?f=sc1"
        print(f"🌐 접속 중: {target_url}")
        driver.get(target_url)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        daily_matches = {date_key: []}
        match_id_counter = 1
        
        # BeautifulSoup을 이용해 전체 페이지 구조 한 번에 파싱
        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.find_all("tr")
        
        current_league = "기타 리그"
        
        for row in rows:
            try:
                text_content = row.get_text()
                
                # 1. 리그 헤더 행 판별 (일반적으로 데이터 아이콘 이 없고 셀이 적음)
                if "" not in text_content and "VS" not in text_content:
                    tds = row.find_all("td")
                    if len(tds) <= 2 and len(row.get_text(strip=True)) > 2:
                        current_league = row.get_text(strip=True)
                        continue
                
                # 2. 경기 대진 행 판별 ('' 아이콘이 포함된 행)
                if "" in text_content:
                    cols = row.find_all("td")
                    if len(cols) >= 6:
                        time_str = cols[1].get_text(strip=True)
                        home_team = cols[3].get_text(strip=True)
                        away_team = cols[5].get_text(strip=True)
                        
                        # [랭킹 정보 등 불순물 제거 정제 작업]
                        # 예: "[1] 도르트문트" 형태에서 팀명만 깔끔하게 추출
                        import re
                        home_clean = re.sub(r'\[.*?\]', '', home_team).strip()
                        away_clean = re.sub(r'\[.*?\]', '', away_team).strip()
                        
                        if home_clean and away_clean:
                            # 중복 수집 방지
                            if not any(m["home"] == home_clean and m["away"] == away_clean for m in daily_matches[date_key]):
                                match_item = {
                                    "id": match_id_counter,
                                    "league": current_league,
                                    "time": time_str,
                                    "home": home_clean,
                                    "away": away_clean,
                                    "meta_details": {
                                        "stadium": "",
                                        "rankings": [],
                                        "absent_players": {"home": [], "away": []}
                                    }
                                }
                                daily_matches[date_key].append(match_item)
                                match_id_counter += 1
            except Exception:
                continue

        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_matches": daily_matches
        }
        
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 총 {match_id_counter - 1}개의 경기가 정상적으로 수집 및 정제되었습니다!")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump({"last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"), "daily_matches": {}}, f, ensure_ascii=False, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_independent_fixtures_crawler()
