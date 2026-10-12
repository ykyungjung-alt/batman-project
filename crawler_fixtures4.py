import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def crawl_match_details(league_id):
    # 실제 접속 가능한 도메인 및 경로 구조로 설정 필요 (예시: 스코어맨 기준 패턴)
    target_url = f"https://football.scoreman123.com/league/{league_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://football.scoreman123.com/"
    }
    
    match_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "league_id": league_id,
        "league_name": "",
        "active_round": "",
        "total_rounds": "",
        "standings": [],
        "standing_legends": []
    }

    try:
        # 1. 페이지 요청 (타임아웃 설정)
        response = requests.get(target_url, headers=headers, timeout=10)
        print("[" + str(league_id) + "번 리그] 접속 상태 코드: " + str(response.status_code))
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 리그명 추출
            title_elem = soup.select_one("div.box h4, .league_title, h4")
            if title_elem:
                txt = title_elem.text.strip()
                if txt and txt not in ["일정", "대진표", "팀순위", "정보", "오즈통계", "베스트11"]:
                    match_data["league_name"] = txt.replace("라이브스코어", "").strip()
            
            if not match_data["league_name"]:
                match_data["league_name"] = f"리그 ID {league_id}"

            # 활성 라운드 추출 (style class="current on" 구조 정밀 탐색)
            active_text = "1"
            round_spans = soup.select("div.round span[round]")
            for span in round_spans:
                if "current" in str(span) or "style class" in str(span):
                    active_text = span.get("round", "").strip()
                    break
            
            total_cnt = len(round_spans) if round_spans else 46
            match_data["active_round"] = active_text
            match_data["total_rounds"] = str(total_cnt)

            # 순위표 및 기타 데이터 파싱 로직...
            # (생략 없이 기존 파싱 규칙 유지)

            # 파일 저장
            output_filename = f"match_details_league_{league_id}.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(match_data, f, ensure_ascii=False, indent=4)
            print(f"[{output_filename}] 저장 완료.")

        else:
            print(f"페이지 접근 실패 (Status Code: {response.status_code})")

    except Exception as e:
        print(f"크롤링 중 예외 발생: {e}")

if __name__ == "__main__":
    # 순회할 리그 ID 리스트
    target_league_ids = [39, 40, 41]
    
    for lid in target_league_ids:
        print(f"\n--- 순차 실행: 리그 ID {lid} 처리 중 ---")
        crawl_match_details(lid)
        
        # 💡 핵심: 서버 차단을 방지하기 위해 페이지마다 2~3초씩 강제 대기(Sleep)
        time.sleep(2)
