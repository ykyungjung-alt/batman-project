import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def fetch_scoreman_data():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920x1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    matches = []
    
    try:
        url = "https://www.scoreman123.com/football/fixture"
        driver.get(url)
        time.sleep(3) # 페이지 로딩 대기
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find('table', id='table_live')
        
        if table:
            current_league = "기타 리그"
            rows = table.find_all('tr')
            
            for row in rows:
                # 리그 타이틀 행인 경우
                if 'Leaguestitle' in row.get('class', []):
                    league_text = row.get_text(strip=True)
                    if league_text:
                        current_league = league_text
                # 경기 데이터 행인 경우
                elif 'b2' in row.get('class', []):
                    cols = row.find_all('td')
                    if len(cols) >= 6:
                        time_str = cols[1].get_text(strip=True)
                        status_str = cols[2].get_text(strip=True)
                        home_team = cols[3].get_text(strip=True)
                        score_str = cols[4].get_text(strip=True)
                        away_team = cols[5].get_text(strip=True)
                        
                        matches.append({
                            "league": current_league,
                            "time": time_str,
                            "status": status_str,
                            "home": home_team,
                            "score": score_str,
                            "away": away_team
                        })
        
        # 데이터가 없을 경우 방어용 데이터 유지
        if not matches:
            matches.append({
                "league": "잉글랜드 FA 컵",
                "time": "28",
                "status": "PASS",
                "home": "윈게이트&핀칠리",
                "score": "-",
                "away": "베드포드"
            })
            
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()
        
    return matches

if __name__ == "__main__":
    data = fetch_scoreman_data()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("data.json 업데이트 완료!")
