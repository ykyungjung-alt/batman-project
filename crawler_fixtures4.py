import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def crawl_match_details_v4():
    # 💡 대회 랭킹 및 상세 매치 데이터를 수집하는 대상 엔드포인트 설정
    # (필요에 따라 스코어맨 또는 타겟 리그 순위/일정 페이지 URL을 지정하세요)
    target_url = "https://www.scoreman123.com/football/fixture"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    match_data_v4 = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "standings": {},
        "meta_details": {
            "fixtures": {
                "home": [],
                "away": []
            }
        }
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 💡 [예시] 팀 순위(Standings) 테이블 파싱 로직
            # 스코어맨 등의 팀순위 테이블 구조(.team_rank 또는 관련 태그)에 맞춰 추출
            standings_table = soup.select(".team_rank table tr, table")
            
            parsed_standings = []
            for row in standings_table:
                cols = [ele.text.strip() for ele in row.find_all(['th', 'td'])]
                if cols:
                    parsed_standings.append(cols)
            
            match_data_v4["standings"]["league_table"] = parsed_standings
            print("성공적으로 대회 랭킹 및 매치 데이터를 파싱했습니다.")
        else:
            print(f"페이지 요청 실패: Status Code {response.status_code}")

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")

    # 💡 결과를 match_details_v4.json에 저장
    output_filename = "match_details_v4.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(match_data_v4, f, ensure_ascii=False, indent=4)
        
    print(f"[{output_filename}] 파일 저장 완료.")

if __name__ == "__main__":
    crawl_match_details_v4()
