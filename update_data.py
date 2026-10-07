from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
import requests

TARGET_URL = "https://www.scoreman123.com/football/fixture"

def fetch_scoreman_data():
    matches = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.scoreman123.com/"
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            current_league = "해외축구 (실시간)"
            table = soup.find('table', id='table_live')
            
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    classes = row.get('class', [])
                    
                    # 리그 타이틀 행 감지 (Leaguestitle fbHead)
                    if 'Leaguestitle' in classes and 'fbHead' in classes:
                        league_text = row.get_text(strip=True)
                        if league_text:
                            current_league = league_text.replace("+", "").strip()
                        continue
                        
                    # 경기 데이터 행 감지 (b2)
                    if 'b2' in classes:
                        tds = row.find_all('td')
                        if len(tds) >= 6:
                            time_str = tds[1].get_text(strip=True)
                            status_str = tds[2].get_text(strip=True)
                            home_raw = tds[3].get_text(strip=True)
                            score_str = tds[4].get_text(strip=True)
                            away_raw = tds[5].get_text(strip=True)
                            
                            # 팀명 대괄호 메타데이터 정제 ([4] 그니스탄 -> 그니스탄)
                            home_team = re.sub(r'\[.*?\]', '', home_raw).strip()
                            away_team = re.sub(r'\[.*?\]', '', away_raw).strip()
                            
                            if home_team and away_team:
                                matches.append({
                                    "id": len(matches) + 1,
                                    "league": current_league,
                                    "time": time_str if time_str else "진행중",
                                    "status": status_str,
                                    "home": home_team,
                                    "away": away_team,
                                    "home_team": home_team,
                                    "away_team": away_team,
                                    "tournament": current_league,
                                    "score": score_str,
                                    "home_recent_stats": "실시간 수집 체급 적용",
                                    "away_recent_stats": "실시간 수집 체급 적용",
                                    "match_name": f"[{current_league}] {home_team} vs {away_team} ({time_str})"
                                })
    except Exception as e:
        print(f"크롤링 오류: {e}")
        
    return matches

if __name__ == "__main__":
    matches = fetch_scoreman_data()
    
    # 수집 실패 시 방어 데이터
    if not matches:
        matches = [{
            "id": 1,
            "league": "테스트 리그",
            "time": "03:45",
            "home": "레알 마드리드",
            "away": "FC 바르셀로나",
            "home_team": "레알 마드리드",
            "away_team": "FC 바르셀로나",
            "tournament": "테스트 리그",
            "score": "-",
            "match_name": "[테스트 리그] 레알 마드리드 vs FC 바르셀로나 (03:45)"
        }]
        
    output_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": TARGET_URL,
        "matches": matches
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print(f"data.json 업데이트 완료! (총 {len(matches)}개 경기 수집)")
