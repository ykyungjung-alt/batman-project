import json
import os
import time
import re
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

# Selenium 관련 임포트
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 설정 파일 경로
OUTPUT_FILE = "match_details_v5.json"
SOURCE_FILES = ["match_details.json", "match_details2.json"]

def get_kst_time_string():
    """UTC 시간 기준에서 9시간을 더한 대한민국 표준시(KST) 문자열을 반환합니다."""
    kst_zone = timezone(timedelta(hours=9))
    return datetime.now(kst_zone).strftime("%Y-%m-%d %H:%M:%S")

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

def crawl_player_details_with_selenium(driver, player_id):
    """Selenium을 통해 선수 페이지에 접속한 뒤, 최신 시즌 셀렉트 박스를 클릭하고 핵심 지표를 파싱합니다."""
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
        driver.get(player_url)
        # 페이지가 로드되고 ul#techImportant 영역이 나타날 때까지 최대 10초 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul#techImportant"))
        )
        
        # 💡 [핵심] 최신 시즌 데이터를 보장하기 위해 시즌 선택 셀렉트 박스 조작이 필요한 경우 여기서 클릭 제어 가능
        # 예시: 필요시 driver.execute_script 등을 통해 자바스크립트 함수 직접 호출 가능
        # driver.execute_script("changeTechSelect(2, document.querySelector('#techSeasonSelect li'))")
        # time.sleep(0.5)

        # BeautifulSoup으로 현재 렌더링된 소스 파싱
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        important_items = soup.select('ul#techImportant > li')
        
        matches = 0
        play_time = 0
        imp_stats = {}
        
        for item in important_items:
            span_tag = item.select_one('span')
            if span_tag:
                label = span_tag.text.strip()
                
                # 이미지 태그 제거
                for img in item.select('img'):
                    img.decompose()
                # 라벨 span 제거
                span_tag.decompose()
                
                val = item.text.strip()
                imp_stats[label] = val
                
                # 수치 매핑 추출 (정규식 활용)
                if "경기" in label and "평점" not in label:
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
    print("\n🚀 [Crawler V5 - Selenium 기반 자동화 모드] 시작...")
    
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
        "last_updated": get_kst_time_string(),
        "lineup_details": {}
    }

    # 셀레니움 옵션 설정 (Headless 모드)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("window-size=1920x1080")
    chrome_options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        for idx, m_code in enumerate(test_target_codes, 1):
            target_url = f"https://www.scoreman123.com/match/data-{m_code}"
            teams = match_master_map.get(m_code, {"home": "파리생제르맹", "away": "바르셀로나"})
            
            print(f"\n--------------------------------------------------")
            print(f"📍 [4단계 진입] 경기 요청 시도 ({idx}/{len(test_target_codes)}) -> Match Code: {m_code} ({teams['home']} vs {teams['away']})")

            home_absentees = []
            away_absentees = []

            try:
                driver.get(target_url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div#hurtLineup"))
                )
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
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
                                player_id = home_div.get('techwinid', '')
                                if not player_id:
                                    onclick_attr = name_tag.get('onclick', '')
                                    found_ids = re.findall(r'\d+', onclick_attr)
                                    if found_ids:
                                        player_id = found_ids[0]
                                
                                p_stats = {}
                                if player_id:
                                    print(f"   ㄴ [홈 선수 분석] {name} (ID: {player_id}) 핵심 지표 수집 중...")
                                    p_stats = crawl_player_details_with_selenium(driver, player_id)
                                    time.sleep(0.5)

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
                                player_id = guest_div.get('techwinid', '')
                                if not player_id:
                                    onclick_attr = g_name_tag.get('onclick', '')
                                    found_ids = re.findall(r'\d+', onclick_attr)
                                    if found_ids:
                                        player_id = found_ids[0]
                                
                                p_stats = {}
                                if player_id:
                                    print(f"   ㄴ [원정 선수 분석] {name} (ID: {player_id}) 핵심 지표 수집 중...")
                                    p_stats = crawl_player_details_with_selenium(driver, player_id)
                                    time.sleep(0.5)

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
                print(f"✨ [7단계 완료] Selenium 기반 데이터 수집 및 KST 시간 기록 완료!")

            except Exception as e:
                print(f"❌ [에러 발생 중단점] 크롤링 중 예외 발생 ({m_code}): {e}")

            break

    finally:
        driver.quit()  # 브라우저 자원 해제

    print(f"\n📍 [8단계 진입] 결과 JSON 파일 저장 시도 ({OUTPUT_FILE})...")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=4)
        print(f"✅ [최종 완료] 파일 저장 성공: {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ [에러 발생 중단점] JSON 파일 저장 실패: {e}")

if __name__ == "__main__":
    crawl_match_lineups_v5()
