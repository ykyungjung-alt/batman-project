from datetime import datetime
import json
import os
from bs4 import BeautifulSoup
import requests

def fetch_data_from_site():
    # TODO: 타겟으로 삼을 스포츠 정보 사이트 URL 입력
    target_url = "https://example.com/matches" # 예시 URL
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    matches_list = []
    
    try:
        # 사이트 요청 (필요시 requests 또는 selenium 사용)
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # [예시] 사이트의 HTML 구조에 맞춰 데이터 추출 로직 작성
            # 예: for item in soup.select(".match-item"): ...
            
            # 임시로 파싱 성공 시뮬레이션 데이터 삽입 (실제 크롤링 코드로 대체 필요)
            matches_list = [
                {"id": 1, "home": "크롤링홈팀A", "away": "크롤링원정팀B", "status": "수집완료"}
            ]
        else:
            print(f"사이트 접속 실패: {response.status_code}")
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
        
    # 만약 크롤링 실패 시 기존 데이터를 유지하거나 빈 값 방지 처리
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data = {
        "last_updated": current_time,
        "matches": matches_list if matches_list else [{"id": 0, "home": "데이터 없음", "away": "확인 필요", "status": "대기"}]
    }
    
    # data.json으로 저장 -> GitHub Actions가 이를 감지하고 커밋함
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Crawler updated data.json at {current_time}")

if __name__ == "__main__":
    fetch_data_from_site()
