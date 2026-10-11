import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def crawl_match_details_v4():
    # 💡 대상 리그 페이지 URL (필요에 따라 리그 번호 동적 변경 가능)
    league_id = 39
    target_url = f"https://football.scoreman123.com/league/{league_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    match_data_v4 = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "league_id": league_id,
        "standings": []
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 💡 '팀순위' 섹션의 테이블 행(tr) 파싱
            # 스코어맨 페이지 구조상 팀 순위 테이블의 각 행을 직접 타겟팅
            rank_rows = soup.select(".team_rank table tr")
            
            parsed_standings = []
            for row in rank_rows:
                cols = [ele.text.strip() for ele in row.find_all(['th', 'td'])]
                # 유효한 순위 데이터 행만 추출 (예: 순위, 구단명, 경기수, 승, 무, 패, 득실, 승점)
                if len(cols) >= 8:
                    parsed_standings.append({
                        "rank": cols[0],
                        "team": cols[1],
                        "played": cols[2],
                        "won": cols[3],
                        "drawn": cols[4],
                        "lost": cols[5],
                        "gd": cols[6],
                        "pts": cols[7]
                    })
            
            match_data_v4["standings"] = parsed_standings
            print(f"성공적으로 리그 {league_id} 순위 데이터를 파싱했습니다.")
        else:
            print(f"페이지 요청 실패: Status Code {response.status_code}")

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")

    # 💡 match_details_v4.json에 필요한 데이터만 저장
    output_filename = "match_details_v4.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(match_data_v4, f, ensure_ascii=False, indent=4)
        
    print(f"[{output_filename}] 파일 저장 완료.")

if __name__ == "__main__":
    crawl_match_details_v4()
