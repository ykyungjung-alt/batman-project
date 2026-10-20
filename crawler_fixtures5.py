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

def find_target_match_code(match_master_map, keyword="파리생제르맹"):
    """기존 마스터 데이터 안에서 특정 팀 이름이 포함된 경기의 매치코드를 자동으로 찾습니다."""
    print(f"📍 [검색 단계] 마스터 데이터에서 '{keyword}' 포함된 경기 탐색 중...")
    found_codes = []
    
    for m_code, info in match_master_map.items():
        home = info.get("home", "")
        away = info.get("away", "")
        if keyword in home or keyword in away:
            found_codes.append((m_code, home, away))
            
    return found_codes

def crawl_player_details(session, headers, player_id):
    """선수 고유 ID를 받아 해당 선수의 상세 페이지에 접속하여 스탯 정보를 파싱합니다."""
    player_url = f"https://football.scoreman123.com/team/player/{player_id}"
    player_stats = {
        "player_id": player_id,
        "offensive": {},
        "passing": {},
        "defensive": {}
    }
    
    try:
        resp = session.get(player_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 💡 첨부해주신 이미지 구조 기반 파싱 (div#techPlates 내부 statbox 탐색)
            stat_boxes = soup.select('ul.statbox > li.tecstatbox')
            for box in stat_boxes:
                box_id = box.get('id', '') # 예: techOffensive, techPassing, techDefensive 등
                stats_list = {}
                
                rows = box.select('div.tecstatlis')
                for row in rows:
                    spans = row.select('span')
                    if len(spans) >= 2:
                        label = spans[0].text.strip()
                        val = spans[1].text.strip()
                        stats_list[label] = val
                
                if box_id == "techOffensive":
                    player_stats["offensive"] = stats_list
                elif box_id == "techPassing":
                    player_stats["passing"] = stats_list
                elif box_id == "techDefensive":
                    player_stats["defensive"] = stats_list
                    
    except Exception as e:
        print(f"⚠️ [선수 스탯 파싱 오류 - ID: {player_id}]: {e}")
        
    return player_stats

def crawl_match_lineups_v5():
    print("\n🚀 [Crawler V5 - 선수 상세 스탯 연동 통합 모드] 수집 시작...")
    
    match_master_map = load_match_master_info()
    if not match_master_map:
        print("❌ [중단점 도달] 수집할 매치 정보가 없습니다. 프로세스를 종료합니다.")
        return

    search_keyword = "파리생제르맹" 
    matched_games = find_target_match_code(match_master_map, keyword=search_keyword)

    test_target_codes = []
    if matched_games:
        test_target_codes.append(matched_games[0][0])
    else:
        test_target_codes.append("3073077")

    print(f"📍 [3단계 진입] 최종 테스트 타겟 매치코드 확정: {test_target_codes}")
    
    result_data = {
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lineup_details": {}
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.scoreman123.com/"
    }

    session = requests.Session()

    for idx, m_code in enumerate(test_target_codes, 1):
        target_url = f"https://www.scoreman123.com/match/data-{m_code}"
        teams = match_master_map.get(m_code, {"home": "파리생제르맹", "away": "바르셀로나"})
        
        print(f"\n--------------------------------------------------")
        print(f"📍 [4단계 진입] 경기 요청 시도 ({idx}/{len(test_target_codes)}) -> Match Code: {m_code} ({teams['home']} vs {teams['away']})")

        home_absentees = []
        away_absentees = []

        try:
            resp = session.get(target_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                hurt_box = soup.select_one('div#hurtLineup')
                if hurt_box:
                    rows = hurt_box.select('ul.lineupbox li.lineuplis')
                    
                    for row in rows:
                        # 1) 홈팀 결장자 및 선수 ID 추출
                        home_div = row.select_one('div.home')
                        if home_div:
                            num_tag = home_div.select_one('span.Nrank')
                            name_tag = home_div.select_one('div.player > a')
                            is_injured = home_div.select_one('span.icon-font-injured1') is not None
                            
                            if name_tag and name_tag.text.strip():
                                name = name_tag.text.strip()
                                href = name_tag.get('href', '')
                                # URL에서 player_id 추출 (예: /team/player/189372 -> 189372)
                                player_id = href.split('/')[-1] if 'player/' in href else ""
                                
                                # 선수 상세 페이지 스탯 연동 수집
                                p_stats = {}
                                if player_id:
                                    print(f"   ㄴ [홈 선수 스탯 수집] {name} (ID: {player_id}) 접속 중...")
                                    p_stats = crawl_player_details(session, headers, player_id)
                                    time.sleep(0.3) # 서버 부하 방지 딜레이

                                home_absentees.append({
                                    "number": num_tag.text.strip() if num_tag else "",
                                    "name": name,
                                    "player_id": player_id,
                                    "status": "결장" if is_injured else "출전의심/기타",
                                    "stats": p_stats
                                })

                        # 2) 원정팀 결장자 및 선수 ID 추출
                        guest_div = row.select_one('div.guest')
                        if guest_div:
                            num_tag = guest_div.select_one('span.Nrank')
                            name_tag = guest_div.select_one('div.player > a')
                            is_injured = guest_div.select_one('span.icon-font-injured1') is not None
                            
                            if name_tag and name_tag.text.strip():
                                name = name_tag.text.strip()
                                href = name_tag.get('href', '')
                                player_id = href.split('/')[-1] if 'player/' in href else ""
                                
                                p_stats = {}
                                if player_id:
                                    print(f"   ㄴ [원정 선수 스탯 수집] {name} (ID: {player_id}) 접속 중...")
                                    p_stats = crawl_player_details(session, headers, player_id)
                                    time.sleep(0.3)

                                away_absentees.append({
                                    "number": num_tag.text.strip() if num_tag else "",
                                    "name": name,
                                    "player_id": player_id,
                                    "status": "결장" if is_injured else "출전의심/기타",
                                    "stats": p_stats
                                })

                result_data["lineup_details"][m_code] = {
                    "match_code": m_code,
                    "home": teams["home"],
                    "away": teams["away"],
                    "home_absentees": home_absentees,
                    "away_absentees": away_absentees
                }
                print(f"✨ [7단계 완료] 빈 행 필터링 및 선수 개인 스탯 연동 완료!")
            else:
                print(f"⚠️ [중단점] 페이지 응답 실패 (Status Code: {resp.status_code})")

        except Exception as e:
            print(f"❌ [에러 발생 중단점] 크롤링 중 예외 발생 ({m_code}): {e}")

        break

    print(f"\n📍 [8단계 진입] 결과 JSON 파일 저장 시도 ({OUTPUT_FILE})...")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_async=False if "ensure_async" in locals() else False, indent=4) # 파이썬 기본 표준 문법 준수
        print(f"✅ [최종 완료] 파일 저장 성공: {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ [에러 발생 중단점] JSON 파일 저장 실패: {e}")

if __name__ == "__main__":
    crawl_match_lineups_v5()
