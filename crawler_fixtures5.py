import json
import os
import time
import requests
from bs4 import BeautifulSoup

# 설정 파일 경로
OUTPUT_FILE = "match_details_v5.json"
SOURCE_FILES = ["match_details.json", "match_details2.json"]

def load_match_master_info():
    """기존 match_details 파일들에서 match_code와 매칭되는 홈/원정 팀명 정보를 수집합니다."""
    print("📍 [1단계 진입] 기존 match_details 파일에서 매치 정보 로드 시작...")
    match_master_map = {}
    
    for s_file in SOURCE_FILES:
        if os.path.exists(s_file):
            try:
                print(f"   - 파일 확인됨: {s_file}, 읽기 시도 중...")
                with open(s_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    details = data.get("match_details", {})
                    for m_code, m_info in details.items():
                        m_code_str = str(m_code).strip()
                        if m_code_str not in match_master_map:
                            match_master_map[m_code_str] = {
                                "home": m_info.get("home", ""),
                                "away": m_info.get("away", "")
                            }
                print(f"📁 [1단계 완료] {s_file}에서 매치 정보 누적 확보 완료")
            except Exception as e:
                print(f"⚠️ [1단계 오류] {s_file} 읽기 실패: {e}")
        else:
            print(f"⚠️ [1단계 알림] 파일이 존재하지 않습니다: {s_file}")
            
    return match_master_map

def crawl_match_lineups_v5():
    print("\n🚀 [Crawler V5 - 팀명 연동 모드] 선수 라인업 및 결장자 정보 수집 시작...")
    
    # 1단계: 마스터 정보(매치코드 + 홈팀 + 원정팀) 로드
    match_master_map = load_match_master_info()
    if not match_master_map:
        print("❌ [중단점 도달] 수집할 매치 정보가 없습니다. 프로세스를 종료합니다.")
        return

    match_codes = list(match_master_map.keys())
    print(f"📍 [2단계 진입] 총 {len(match_codes)}개의 매치 확보 완료. 테스트 대상 선정 중...")
    
    result_data = {
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lineup_details": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.scoreman123.com/"
    }

    session = requests.Session()

    # 💡 [테스트용] 전체 목록 중 딱 1개의 매치코드만 가져오기
    test_target_codes = match_codes[:1]
    print(f"📍 [3단계 진입] 테스트 타겟 매치코드 선정 완료: {test_target_codes}")

    for idx, m_code in enumerate(test_target_codes, 1):
        target_url = f"https://www.scoreman123.com/match/data-{m_code}"
        teams = match_master_map.get(m_code, {"home": "", "away": ""})
        
        print(f"\n--------------------------------------------------")
        print(f"📍 [4단계 진입] 경기 요청 시도 ({idx}/{len(test_target_codes)})")
        print(f"   - Match Code: {m_code}")
        print(f"   - Match Info: {teams['home']} vs {teams['away']}")
        print(f"   - Target URL: {target_url}")

        home_absentees = []
        away_absentees = []

        try:
            print(f"📍 [5단계 진입] HTTP GET 요청 전송 중...")
            resp = session.get(target_url, headers=headers, timeout=10)
            print(f"   - 응답 상태 코드 (Status Code): {resp.status_code}")
            
            if resp.status_code == 200:
                print(f"📍 [6단계 진입] HTML 응답 수신 성공, BeautifulSoup 파싱 시작...")
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 결장 탭 영역 (div#hurtLineup) 내부 파싱
                hurt_box = soup.select_one('div#hurtLineup')
                if hurt_box:
                    print(f"   - 'div#hurtLineup' (결장 탭 박스) 탐색 성공!")
                    rows = hurt_box.select('ul.lineupbox li.lineuplis')
                    print(f"   - 탐색된 결장 선수 행(Row) 개수: {len(rows)}개")
                    
                    for row in rows:
                        # 홈팀 결장자 정보 추출
                        home_div = row.select_one('div.home')
                        if home_div:
                            num_tag = home_div.select_one('span.Nrank')
                            name_tag = home_div.select_one('div.player > a')
                            is_injured = home_div.select_one('span.icon-font-injured1') is not None
                            
                            if name_tag:
                                home_absentees.append({
                                    "number": num_tag.text.strip() if num_tag else "",
                                    "name": name_tag.text.strip(),
                                    "status": "결장" if is_injured else "출전의심/기타"
                                })

                        # 원정팀 결장자 정보 추출
                        guest_div = row.select_one('div.guest')
                        if guest_div:
                            num_tag = guest_div.select_one('span.Nrank')
                            name_tag = guest_div.select_one('div.player > a')
                            is_injured = guest_div.select_one('span.icon-font-injured1') is not None
                            
                            if name_tag:
                                away_absentees.append({
                                    "number": num_tag.text.strip() if num_tag else "",
                                    "name": name_tag.text.strip(),
                                    "status": "결장" if is_injured else "출전의심/기타"
                                })
                else:
                    print(f"⚠️ [경고] 페이지 내에서 'div#hurtLineup' 요소를 찾지 못했습니다.")

                # 💡 요구하신 대로 홈, 어웨이 팀명을 함께 저장하도록 구조 반영
                result_data["lineup_details"][m_code] = {
                    "match_code": m_code,
                    "home": teams["home"],
                    "away": teams["away"],
                    "home_absentees": home_absentees,
                    "away_absentees": away_absentees
                }
                print(f"✨ [7단계 완료] 파싱 성공! [{teams['home']} vs {teams['away']}] 홈 결장 {len(home_absentees)}명 / 원정 결장 {len(away_absentees)}명")
            else:
                print(f"⚠️ [중단점] 페이지 응답 실패 (Status Code: {resp.status_code})")

        except Exception as e:
            print(f"❌ [에러 발생 중단점] 크롤링 중 예외 발생 ({m_code}): {e}")

        # 테스트이므로 1경기 처리 후 강제 탈출
        break

    print(f"\n📍 [8단계 진입] 결과 JSON 파일 저장 시도 ({OUTPUT_FILE})...")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=4)
        print(f"✅ [최종 완료] 파일 저장 성공: {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ [에러 발생 중단점] JSON 파일 저장 실패: {e}")

if __name__ == "__main__":
    crawl_match_lineups_v5()
