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
    match_codes = set()
    for s_file in SOURCE_FILES:
        if os.path.exists(s_file):
            try:
                with open(s_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    details = data.get("match_details", {})
                    for m_code in details.keys():
                        match_codes.add(str(m_code).strip())
                print(f"📁 [로드 성공] {s_file}에서 매치코드 {len(match_codes)}개 확보")
            except Exception as e:
                print(f"⚠️ [로드 오류] {s_file} 읽기 실패: {e}")
    return list(match_codes)

def crawl_match_lineups_v5():
    print("🚀 [Crawler V5] 선수 라인업 및 결장자 정보 수집 크롤러 가동...")
    
    match_codes = load_match_codes()
    if not match_codes:
        print("❌ 수집할 매치코드가 없습니다. 기존 match_details 파일을 확인해주세요.")
        return

    result_data = {
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lineup_details": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.scoreman123.com/"
    }

    session = requests.Session()

    for idx, m_code in enumerate(match_codes, 1):
        target_url = f"https://www.scoreman123.com/match/data-{m_code}"
        print(f"[{idx}/{len(match_codes)}] 크롤링 중 (Match Code: {m_code})...")

        home_absentees = []
        away_absentees = []

        try:
            resp = session.get(target_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 💡 핵심: 결장 탭 영역 (div#hurtLineup) 내부 파싱
                hurt_box = soup.select_one('div#hurtLineup')
                if hurt_box:
                    rows = hurt_box.select('ul.lineupbox li.lineuplis')
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

                result_data["lineup_details"][m_code] = {
                    "match_code": m_code,
                    "home_absentees": home_absentees,
                    "away_absentees": away_absentees
                }
            else:
                print(f"⚠️ 페이지 응답 실패 (Status: {resp.status_code})")

        except Exception as e:
            print(f"❌ 크롤링 중 예외 발생 ({m_code}): {e}")

        # 서버 부하 방지 및 차단 방지 딜레이
        time.sleep(0.5)

    # 최종 JSON 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)

    print(f"✅ [Crawler V5] 모든 작업 완료! 결과 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    crawl_match_lineups_v5()
