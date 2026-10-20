import json
import os
import time
import requests
from bs4 import BeautifulSoup

# 설정 파일 경로
OUTPUT_FILE = "match_details_v5.json"
SOURCE_FILES = ["match_details.json", "match_details2.json"]

def load_match_codes():
    """기존 match_details 파일들에서 match_code 목록을 수집합니다."""
    print("📍 [1단계 진입] 기존 match_details 파일 로드 시작...")
    match_codes = set()
    
    for s_file in SOURCE_FILES:
        if os.path.exists(s_file):
            try:
                print(f"   - 파일 확인됨: {s_file}, 읽기 시도 중...")
                with open(s_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    details = data.get("match_details", {})
                    for m_code in details.keys():
                        match_codes.add(str(m_code).strip())
                print(f"📁 [1단계 완료] {s_file}에서 매치코드 {len(match_codes)}개 누적 확보")
            except Exception as e:
                print(f"⚠️ [1단계 오류] {s_file} 읽기 실패: {e}")
        else:
            print(f"⚠️ [1단계 알림] 파일이 존재하지 않습니다: {s_file}")
            
    return list(match_codes)

def crawl_match_lineups_v5():
    print("\n🚀 [Crawler V5 - 디버깅 모드] 선수 라인업 및 결장자 정보 수집 시작...")
    
    # 1단계: 매치코드 로드
    match_codes = load_match_codes()
    if not match_codes:
        print("❌ [중단점 도달] 수집할 매치코드가 없습니다. 프로세스를 종료합니다.")
        return

    print(f"📍 [2단계 진입] 총 {len(match_codes)}개의 매치코드 확보 완료. 테스트 대상 선정 중...")
    
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
        print(f"\n--------------------------------------------------")
        print(f"📍 [4단계 진입] 경기 요청 시도 ({idx}/{len(test_target_codes)})")
        print(f"   - Match Code: {m_code}")
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
                    print(f"⚠️ [경고] 페이지 내에서 'div#hurtLineup' 요소를 찾지 못했습니다. 구조가 다를 수 있습니다.")

                # 💡 기본 인포 구조에 맞춘 저장 형태
                result_data["lineup_details"][m_code] = {
                    "match_code": m_code,
                    "home_absentees": home_absentees,
                    "away_absentees": away_absentees
                }
                print(f"✨ [7단계 완료] 파싱 성공! 홈 결장자 {len(home_absentees)}명 / 원정 결장자 {len(away_absentees)}명 수집 완료")
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
