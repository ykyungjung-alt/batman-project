import json
import os
import time
import re
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
    """선수 고유 ID를 받아 image_5.png의 <text>와 <span> 구조에 맞게 핵심 지표를 정확히 파싱합니다."""
    player_url = f"https://football.scoreman123.com/team/player/{player_id}"
    
    player_stats = {
        "player_id": player_id,
        "matches_played": 0,
        "total_play_time": 0,
        "avg_play_time": 0.0,
        "grade": "D",
        "important_stats": {}
    }
    
    try:
        resp = session.get(player_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # ul#techImportant 내부의 각 li 항목 탐색
            important_items = soup.select('ul#techImportant > li')
            matches = 0
            play_time = 0
            imp_stats = {}
            
            for item in important_items:
                # 💡 핵심 수정: <text> 태그에서 직접 수치 데이터를 읽고, <span> 태그에서 라벨을 읽습니다.
                text_tag = item.select_one('text')
                span_tag = item.select_one('span')
                
                if text_tag and span_tag:
                    val = text_tag.text.strip()
                    label = span_tag.text.strip()
                    
                    imp_stats[label] = val
                    
                    # 수치 매핑 추출 (정규식 활용)
                    if "경기" in label:
                        numbers = re.findall(r'\d+', val)
                        if numbers:
                            try: matches = int(numbers[0])
                            except: pass
                    elif "출전시간" in label:
                        numbers = re.findall(r'\d+', val)
                        if numbers:
                            try: play_time = int(numbers[0])
                            except: pass
            
            player_stats["important_stats"] = imp_stats
            player_stats["matches_played"] = matches
            player_stats["total_play_time"] = play_time
            
            # 평균 출전 시간 계산 및 A~D 등급 판정
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
                player_stats["grade"] = "D"
                
    except Exception as e:
        print(f"⚠️ [선수 스탯 파싱 오류 - ID: {player_id}]: {e}")
        
    return player_stats
def crawl_match_lineups_v5():
    print("\n🚀 [Crawler V5 - ID 추출 개선 및 타임슬립 적용 모드] 시작...")
    
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
                                
                                # 💡 [핵심 수정] techwinid 속성 또는 onclick 속성에서 정확한 player_id 추출
                                player_id = home_div.get('techwinid', '')
                                if not player_id:
                                    onclick_attr = name_tag.get('onclick', '')
                                    found_ids = re.findall(r'\d+', onclick_attr)
                                    if found_ids:
                                        player_id = found_ids[0]
                                
                                p_stats = {}
                                if player_id:
                                    print(f"   ㄴ [홈 선수 분석] {name} (ID: {player_id}) 핵심 지표 수집 중...")
                                    p_stats = crawl_player_details(session, headers, player_id)
                                    time.sleep(0.7) # 서버 부하 방지 타임슬립

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
                            g_name_tag = guest_div.select_one('div.player > a')
                            is_injured = guest_div.select_one('span.icon-font-injured1') is not None
                            
                            if g_name_tag and g_name_tag.text.strip():
                                name = g_name_tag.text.strip()
                                
                                # 💡 [핵심 수정] techwinid 속성 또는 onclick 속성에서 정확한 player_id 추출
                                player_id = guest_div.get('techwinid', '')
                                if not player_id:
                                    onclick_attr = g_name_tag.get('onclick', '')
                                    found_ids = re.findall(r'\d+', onclick_attr)
                                    if found_ids:
                                        player_id = found_ids[0]
                                
                                p_stats = {}
                                if player_id:
                                    print(f"   ㄴ [원정 선수 분석] {name} (ID: {player_id}) 핵심 지표 수집 중...")
                                    p_stats = crawl_player_details(session, headers, player_id)
                                    time.sleep(0.7) # 서버 부하 방지 타임슬립

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
                print(f"✨ [7단계 완료] 선수 ID 정상 추출 및 상세 지표 연동 완료!")
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
