from datetime import datetime
import json
from bs4 import BeautifulSoup
import requests

def fetch_scoreman_fast():
    target_url = "https://www.scoreman123.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    matches_list = []
    
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 스코어맨 페이지의 경기 행 파싱
        rows = soup.select("table tr")
        
        match_id = 1
        current_league = "일반 리그"
        
        for row in rows:
            text_all = row.get_text(strip=True)
            if not text_all:
                continue
                
            # 리그 타이틀 행 감지
            if "리그" in text_all or "컵" in text_all or "UEFA" in text_all:
                cells_check = row.find_all("td")
                if len(cells_check) <= 2:
                    current_league = text_all
                    continue
            
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            
            time_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            home_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            away_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            
            if home_text and away_text and (":" in time_text or "종료" in time_text or "-" in cells[3].get_text(strip=True)):
                matches_list.append({
                    "id": match_id,
                    "league": current_league,
                    "time": time_text,
                    "home": home_text,
                    "away": away_text,
                    "status": "라이브수집완료"
                })
                match_id += 1
                
                if match_id > 50:
                    break
                    
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 수집 데이터가 없을 경우 방어용 데이터
    final_matches = matches_list if matches_list else [
        {"id": 1, "league": "테스트 리그", "time": "03:45", "home": "레알 마드리드", "away": "FC 바르셀로나", "status": "기본대기"}
    ]
    
    data = {
        "last_updated": current_time,
        "source": "https://www.scoreman123.com/",
        "matches": final_matches
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Data successfully updated at {current_time} ({len(final_matches)} matches)")

if __name__ == "__main__":
    fetch_scoreman_fast()
