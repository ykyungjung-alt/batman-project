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
    date_key = today.strftime("%m-%d")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        target_url = "https://www.scoreman123.com/football/fixture?f=sc1"
        print(f"🌐 접속 중: {target_url}")
        driver.get(target_url)
        
        # 페이지 바디가 로드될 때까지 최대 15초 대기
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        daily_matches = {date_key: []}
        match_id_counter = 1
        
        rows = driver.find_elements(By.TAG_NAME, "tr")
        current_league = "기타 리그"
        
        for row in rows:
            try:
                text_content = row.text
                if "VS" not in text_content and "-" not in text_content:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) <= 2:
                        league_text = row.text.strip()
                        if league_text:
                            current_league = league_text
                        continue
                
                if "" in text_content:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 6:
                        time_str = cols[1].text.strip()
                        home_team = cols[3].text.strip()
                        away_team = cols[5].text.strip()
                        
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
            
        print(f"\n🎉 성공: {match_id_counter - 1}개 경기 수집 완료")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        # 에러가 나더라도 빈 JSON 파일을 만들어 워크플로우 비정상 종료(exit code 1) 방지
        with open("match_details.json", "w", encoding="utf-8") as f:
            json.dump({"last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"), "daily_matches": {}}, f, ensure_ascii=False, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_independent_fixtures_crawler()
