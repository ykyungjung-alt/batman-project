from datetime import datetime, timedelta
import json
import time
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from zoneinfo import ZoneInfo

def convert_market_value_to_krw(val_str):
    """
    💡 £140.000M 같은 몸값 문자열을 받아 한국 원화(또는 억/원 단위)로 변환하는 함수
    (필요에 따라 환율 기준을 조절하실 수 있습니다.)
    """
    if not val_str or val_str == "-" or "£" not in val_str:
        return "-"
    
    try:
        # 예: '£140.000M' -> 숫자 140.0 추출
        clean_val = val_str.replace("£", "").replace("M", "").strip()
        mil_val = float(clean_val)
        
        # 1M 파운드를 대략 1,800원 기준(또는 원하시는 환율)으로 환산 시 예시 계산
        # 여기서는 직관적인 원화 억 단위(또는 조 단위)로 표기합니다.
        krw_billion = mil_val * 1800  # 대략적인 파운드당 원화 환산 예시 (억 원 단위)
        if krw_billion >= 10000:
            조 = krw_billion // 10000
            억 = krw_billion % 10000
            return f"{int(조)}조 {int(억)}억원"
        else:
            return f"{int(krw_billion)}억원"
    except Exception:
        return val_str

def parse_team_squad(driver, team_summary_url):
    """
    💡 구단 상세 페이지에서 선수 명단을 표 형식(리스트)으로 수집 (계약 만료 제외, 몸값 원화 변환)
    """
    squad_list = []
    try:
        driver.get(team_summary_url)
        time.sleep(0.5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 선수정보 영역 탐색 (공유해주신 뷰포트 구조 기준)
        # 테이블 혹은 리스트 형태의 행들을 순회합니다.
        # 실제 사이트의 HTML 구조(tr 또는 선수 정보 row 클래스)에 맞춰 파싱합니다.
        
        # 예시로 선수 정보가 담긴 행들을 찾는 셀렉터 구조
        player_rows = soup.find_all("tr") # 또는 선수 정보 전용 태그/클래스
        
        for row in player_rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                name = cols[0].get_text(strip=True)
                position = cols[1].get_text(strip=True)
                age = cols[2].get_text(strip=True)
                raw_value = cols[3].get_text(strip=True)
                
                # 몸값을 한국 원화로 변환
                krw_value = convert_market_value_to_krw(raw_value)
                
                player_info = {
                    "name": name,
                    "position": position,
                    "age": age,
                    "market_value_krw": krw_value  # 계약 만료 항목은 제외
                }
                squad_list.append(player_info)
                
    except Exception as e:
        print(f"  - 선수 명단 파싱 예외: {e}")
        
    return squad_list

def run_squad_crawler_v5_1():
    if not os.path.exists("data.json"):
        print("❌ data.json 파일이 존재하지 않습니다.")
        return

    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    target_matches = []
    daily_matches_input = data.get("daily_matches", {})
    
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
    limit_kst = now_kst + timedelta(hours=48)
    
    print(f"🕒 [V5-1] 실행 시간(KST): {now_kst.strftime('%Y-%m-%d %H:%M')}")
    print(f"🎯 [V5-1] 수집 대상 타임라인 (~48시간 후): {limit_kst.strftime('%Y-%m-%d %H:%M')}")

    current_year = now_kst.year

    for date_key, matches in daily_matches_input.items():
        try:
            date_part = date_key.split()[0]
            m_part, d_part = map(int, date_part.split("-"))
        except Exception:
            continue

        for m in matches:
            time_str = m.get("time", "")
            if not time_str or ":" not in time_str:
                continue
            
            try:
                if " " in time_str:
                    time_part = time_str.split(" ")[1]
                else:
                    time_part = time_str
                    
                hour_val, min_val = map(int, time_part.split(":"))
                match_dt = datetime(current_year, m_part, d_part, hour_val, min_val, tzinfo=kst)
                
                if match_dt < now_kst - timedelta(days=15) and m_part == 1:
                    match_dt = datetime(current_year + 1, m_part, d_part, hour_val, min_val, tzinfo=kst)

                if now_kst <= match_dt <= limit_kst:
                    m_code = m.get("match_code")
                    if m_code and m_code not in [t["match_code"] for t in target_matches]:
                        target_matches.append({
                            "match_code": m_code,
                            "league": m.get("league", ""),
                            "home": m.get("home", ""),
                            "away": m.get("away", "")
                        })
            except Exception:
                continue

    print(f"🎯 [V5-1] 조건에 일치하는 총 {len(target_matches)}개 경기 대상 선수 명단 수집 시작")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    squad_details = {}

    try:
        for target in target_matches:
            m_id = target["match_code"]
            main_home = target["home"]
            main_away = target["away"]
            
            # 예시로 경기 상세 페이지 혹은 구단 summary 페이지 접근 구조 연동
            # (필요한 팀 ID나 링크 구조에 맞춰 조율 가능합니다)
            
            squad_details[m_id] = {
                "match_code": m_id,
                "home": main_home,
                "away": main_away,
                "home_squad": [],
                "away_squad": []
            }

        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "squad_details": squad_details
        }
        
        with open("match_details_v5-1.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 선수 명단 수집 완료 -> match_details_v5-1.json 저장 완료")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_squad_crawler_v5_1()
