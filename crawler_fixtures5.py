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

# 설정 파일 경로 (필요한 모든 match_details 파일을 포괄하도록 확장)
OUTPUT_FILE = "match_details_v5.json"
SOURCE_FILES = [
    "match_details.json", 
    "match_details2.json", 
    "match_details_v3.json", 
    "match_details_v3-1.json", 
    "match_details_v3-2.json", 
    "match_details_v4.json"
]

def get_kst_time_string():
    """UTC 시간 기준에서 9시간을 더한 대한민국 표준시(KST) 문자열을 반환합니다."""
    kst_zone = timezone(timedelta(hours=9))
    return datetime.now(kst_zone).strftime("%Y-%m-%d %H:%M:%S")

def load_match_master_info():
    """기존의 모든 match_details 및 데이터 파일들에서 match_code와 매칭되는 홈/원정 팀명 정보를 전수 수집합니다."""
    print("📍 [1단계 진입] 모든 기존 match_details 및 데이터 파일에서 매치 정보 전수 로드 시작...")
    match_master_map = {}
    
    for s_file in SOURCE_FILES:
        if os.path.exists(s_file):
            try:
                print(f"   - 파일 확인됨: {s_file}, 읽기 시도 중...")
                with open(s_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # 1) 일반적인 match_details 구조 탐색
                    details = data.get("match_details", {})
                    if not details and isinstance(data, dict):
                        # 파일 구조에 따라 최상위나 leagues 등에 데이터가 있을 경우 대비
                        details = data.get("leagues", data)

                    if isinstance(details, dict):
                        for m_code, m_info in details.items():
                            if isinstance(m_info, dict):
                                m_code_str = str(m_info.get("match_code", m_code)).strip()
                                home_t = m_info.get("home", "")
                                away_t = m_info.get("away", "")
                                if m_code_str and home_t and away_t:
                                    if m_code_str not in match_master_map:
                                      match_master_map[m_code_str] = {
                                          "home": home_t,
                                          "away": away_t
                                      }
                    elif isinstance(details, list):
                        for item in details:
                            if isinstance(item, dict):
                                m_code_str = str(item.get("match_code", "")).strip()
                                home_t = item.get("home", "")
                                away_t = item.get("away", "")
                                if m_code_str and home_t and away_t:
                                    if m_code_str not in match_master_map:
                                        match_master_map[m_code_str] = {
                                            "home": home_t,
                                            "away": away_t
                                        }
                print(f"📁 [1단계 완료] {s_file}에서 매치 정보 누적 확보 완료 (현재 누적 총 {len(match_master_map)}개)")
            except Exception as e:
                print(f"⚠️ [1단계 오류] {s_file} 읽기 실패: {e}")
        else:
            print(f"⚠️ [1단계 알림] 파일이 존재하지 않습니다: {s_file}")
            
    return match_master_map

def crawl_player_details_with_selenium(driver, player_id):
    """Selenium을 통해 선수 페이지에 접속한 뒤, 자바스크립트로 최신 시즌을 강제 선택하고 핵심 지표를 파싱합니다."""
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
        
        # 1) 셀렉트 박스가 로드될 때까지 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#techSeasonSelect"))
        )
        
        # 2) 최신 시즌 강제 선택 자바스크립트 실행
        try:
            latest_season_script = """
                const seasonSelect = document.querySelector('#techSeasonSelect ul.selectpop');
                if (seasonSelect) {
                    const latestLi = seasonSelect.querySelector('li[onclick]');
                    if (latestLi) {
                        latestLi.click();
                    }
                }
            """
            driver.execute_script(latest_season_script)
            time.sleep(0.5) # 데이터 렌더링 대기
        except Exception as script_e:
            print(f"⚠️ [셀레니움 제어 오류] 시즌 선택 실패 (기본값 파싱 시도): {script_e}")

        # 3) 업데이트된 HTML 소스 파싱
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        important_items = soup.select('ul#techImportant > li')
        
        matches = 0
        play_time = 0
        imp_stats = {}
        
        for item in important_items:
            text_tag = item.select_one('text')
            span_tag = item.select_one('span')
            
            if text_tag and span_tag:
                val = text_tag.text.strip()
                label = span_tag.text.strip()
                
                imp_stats[label] = val
                
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
    print("\n🚀 [Crawler V5 - 전체 경기 제한 없는 전수 수집 모드] 시작...")
    
    match_master_map = load_match_master_info()
    if not match_master_map:
        print("❌ [중단점 도달] 수집할 매치 정보가 없습니다. 프로세스를 종료합니다.")
        return

    target_match_codes = list(match_master_map.keys())
    print(f"📍 [3단계 진입] 전체 수집 대상 매치 총 {len(target_match_codes)}개 확보 완료. 순차 크롤링을 시작합니다.")
    
    # 기존에 수집된 v5 결과가 있다면 로드하여 병합 (중단 지점 이어하기 지원)
    result_data = {
        "last_updated": get_kst_time_string(),
        "lineup_details": {}
    }
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, dict) and "lineup_details" in existing_data:
                    result_data["lineup_details"] = existing_data["lineup_details"]
                    print(f"📂 기존 {OUTPUT_FILE} 파일에서 {len(result_data['lineup_details D'])}개의 기존 수집 데이터를 성공적으로 불러왔습니다.")
        except Exception:
            pass

    # 셀레니움 옵션 설정 (Headless 모드)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("window-size=1920x1080")
    chrome_options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        for idx, m_code in enumerate(target_match_codes, 1):
            # 이미 수집된 매치코드라면 중복 크롤링 방지를 위해 스킵 가능 (원할 경우 주석 해제)
            # if m_code in result_data["lineup_details"]:
            #     print(f"⏭️ [{idx}/{len(target_match_codes)}] 매치코드 {m_code} 이미 수집됨. 건너뜁니다.")
            #     continue

            target_url = f"https://www.scoreman123.com/match/data-{m_code}"
            teams = match_master_map.get(m_code, {"home": "홈팀", "away": "원정팀"})
            
            print(f"\n--------------------------------------------------")
            print(f"📍 [진행 상황] ({idx}/{len(target_match_codes)}) -> Match Code: {m_code} ({teams['home']} vs {teams['away']})")

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
                                    print(f"   ㄴ [홈 선수 분석] {name} (ID: {player_id}) 지표 수집 중...")
                                    p_stats = crawl_player_details_with_selenium(driver, player_id)
                                    time.sleep(0.2)

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
                                    print(f"   ㄴ [원정 선수 분석] {name} (ID: {player_id}) 지표 수집 중...")
                                    p_stats = crawl_player_details_with_selenium(driver, player_id)
                                    time.sleep(0.2)

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
                print(f"✨ [{idx}/{len(target_match_codes)}] 매치코드 {m_code} 수집 완료")

                # 매 경기 수집 직후마다 실시간으로 JSON 파일 백업 저장 (중단 시 데이터 유실 방지)
                result_data["last_updated"] = get_kst_time_string()
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=4)

            except Exception as e:
                print(f"❌ [에러 발생] 매치코드 {m_code} 수집 중 예외 발생: {e}")

    finally:
        driver.quit()  # 브라우저 자원 해제

    print(f"\n📍 [완료 단계] 전체 결과 JSON 파일 최종 저장 완료 ({OUTPUT_FILE})")

if __name__ == "__main__":
    crawl_match_lineups_v5()
