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
    """선수 고유 ID를 받아 핵심 요약 지표 및 세부 스탯 정보를 파싱하고 출전 시간 기준 등급(A~D)을 부여합니다."""
    player_url = f"https://football.scoreman123.com/team/player/{player_id}"
    
    # 기본 데이터 구조 초기화 (선수 정보가 없거나 실패 시 기본값 설정용)
    player_stats = {
        "player_id": player_id,
        "matches_played": 0,
        "total_play_time": 0,
        "avg_play_time": 0.0,
        "grade": "D",  # 기본값 D 고정
        "important_stats": {},
        "offensive": {},
        "passing": {},
        "defensive": {}
    }
    
    try:
        resp = session.get(player_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 💡 1) 상단 핵심 요약 지표 파싱 (경기 수, 출전시간 등) -> image_2.png 참조
            important_items = soup.select('ul#techImportant > li')
            matches = 0
            play_time = 0
            
            imp_stats = {}
            for item in important_items:
                text_val = item.select_one('text')
                span_val = item.select_one('span')
                if text_val and span_val:
                    label = span_val.text.strip()
                    val = text_val.text.strip()
                    imp_stats[label] = val
                    
                    if "경기" in label:
                        try: matches = int(val)
                        except: pass
                    elif "출전시간" in label:
                        try: play_time = int(val)
                        except: pass
            
            player_stats["important_stats"] = imp_stats
            player_stats["matches_played"] = matches
            player_stats["total_play_time"] = play_time
            
            # 💡 2) 평균 출전 시간 계산 및 A~D 등급 판정
            if matches > 0:
                avg_time = play_time / matches
                player_stats["avg_play_time"] = round(avg_time, 1)
                
                if avg_time >= 70:
                    player_stats["grade"] = "A"
                elif avg_time >= 50:
                    player_stats["grade"] = "B"
                elif avg_time >= 30:
                    player_stats["grade"] = "C"
                else:
                    player_stats["grade"] = "D"
            else:
                # 경기 수가 0이거나 정보가 부족한 경우 D로 고정
                player_stats["grade"] = "D"

            # 💡 3) 부문별 세부 스탯 파싱 (공격/패싱/수비) -> image.png / image_2.png 참조[cite: 1, 2]
            stat_boxes = soup.select('ul.statbox > li.tecstatbox')
            for box in stat_boxes:
                box_id = box.get('id', '') 
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
        # 오류 발생 시에도 기본값 'D'가 유지됨
        
    return player_stats

def crawl_match_lineups_v5():
    print("\n🚀 [Crawler V5 - 출전 시간 기반 등급 자동 판정 모드] 수집 시작...")
    
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
                                player_id = href.split('/')[-1] if 'player/' in href else ""
                                
                                p_stats = {}
                                if player_id:
                                    print(f"   ㄴ [홈 선수 분석] {name} (ID: {player_id}) 스탯 및 등급 산출 중...")
                                    p_stats = crawl_player_details(session, headers, player_id)
                                    time.sleep(0.3)

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
                            name_tag = row.select_one('div.player > a') if not guest_div.select_one('div.player > a') else guest_div.select_one('div.player > a')
                            is_injured = guest_div.select_one('span.icon-font-injured1') is not None
                            
                            # 올바른 guest 영역 안의 선수 태그 탐색 보정
                            g_name_tag = guest_div.select_one('div.player > a')
                            if g_name_tag and g_name_tag.text.strip():
                                name = g_name_tag.text.strip()
                                href = g_name_tag.get('href', '')
                                player_id = href.split('/')[-1] if 'player/' in href else ""
                                
                                p_stats = {}
                                if player_id:
                                    print(f"   ㄴ [원정 선수 분석] {name} (ID: {player_id}) 스탯 및 등급 산출 중...")
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
                print(f"✨ [7단계 완료] 출전 시간 기준 A~D 등급 자동 산출 및 데이터 연동 완료!")
            else:
                print(f"⚠️ [중단점] 페이지 응답 실패 (Status Code: {resp.status_code})")

        except Exception as e:
            print(f"❌ [에러 발생 중단점] 크롤링 중 예외 발생 ({m_code}): {e}")

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
