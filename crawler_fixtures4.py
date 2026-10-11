import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def crawl_match_details_v4():
    league_id = 39
    target_url = f"https://football.scoreman123.com/league/{league_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    match_data_v4 = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "league_id": league_id,
        "league_name": "",       # 💡 1순위: 리그명 (예: 잉글랜드 리그 1)
        "total_rounds": 46,      # 💡 총 라운드 수 (예: 46경기 체제)
        "active_round": "",      # 💡 활성화된 라운드 정보 (예: 11/46)
        "standings": [],
        "fixtures": []
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. 리그명 추출 (예: "잉글랜드 리그 1")
            league_title_elem = soup.select_one("div.box h4, .league_title, h4")
            if league_title_elem:
                match_data_v4["league_name"] = league_title_elem.text.strip().replace("라이브스코어", "").strip()
            else:
                match_data_v4["league_name"] = "잉글랜드 리그 1"

            # 2. 활성화된 라운드 추출 (예: class="current on"인 span 요소)
            active_round_elem = soup.select_one("#schedule .round span.current.on, #schedule span.current.on")
            active_round_num = active_round_elem.text.strip() if active_round_elem else "1"
            
            # 총 라운드 수 산출 (라운드 버튼들의 전체 개수 파악)
            all_rounds = soup.select("#schedule .round span, #schedule span[round]")
            total_rounds_count = len(all_rounds) if all_rounds else 46
            match_data_v4["total_rounds"] = total_rounds_count
            
            # 활성화된 표시 지정 (예: "11/46")
            match_data_v4["active_round"] = f"{active_round_num}/{total_rounds_count}"

            # 3. 해당 라운드의 일정(Fixtures) 및 대진 데이터 파싱
            schedule_rows = soup.select("#schedule tr, .schedule_table tr")
            parsed_fixtures = []
            
            for row in schedule_rows:
                cols = [ele.text.strip() for ele in row.find_all(['th', 'td'])]
                if len(cols) >= 4:
                    parsed_fixtures.append({
                        "round_info": match_data_v4["active_round"], # 몇 번째 경기인지 표기 (예: 11/46)
                        "date_time": cols[0],
                        "home_team": cols[1],
                        "score": cols[2],
                        "away_team": cols[3],
                        "odds": cols[4:] if len(cols) > 4 else []
                    })
            
            match_data_v4["fixtures"] = parsed_fixtures
            print(f"성공적으로 [{match_data_v4['league_name']}] ({match_data_v4['active_round']}) 데이터를 수집했습니다.")
        else:
            print(f"페이지 요청 실패: Status Code {response.status_code}")

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")

    # match_details_v4.json에 저장
    output_filename = "match_details_v4.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(match_data_v4, f, ensure_ascii=False, indent=4)
        
    print(f"[{output_filename}] 저장 완료.")

if __name__ == "__main__":
    crawl_match_details_v4()
