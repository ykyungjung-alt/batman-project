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
    💡 £140.000M 같은 몸값 문자열을 받아 한국 원화(억/조 단위)로 변환하는 함수
    """
    if not val_str or val_str == "-" or "£" not in val_str:
        return "-"
    
    try:
        clean_val = val_str.replace("£", "").replace("M", "").strip()
        mil_val = float(clean_val)
        
        krw_billion = mil_val * 1800  # 파운드당 대략적인 원화 환산 예시 (억 원 단위)
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
    💡 구단 상세 페이지(ul#lineupList -> li.lineuplis)에서 선수 명단 파싱
    """
    squad_list = []
    try:
        driver.get(team_summary_url)
        time.sleep(0.5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        lineup_ul = soup.find("ul", id="lineupList")
        if not lineup_ul:
            return squad_list
            
        player_items = lineup_ul.find_all("li", class_="lineuplis")
        
        for li in player_items:
            try:
                # 1. 선수명 추출 (span.name 내부에서 부가정보 분리)
                name_span = li.find("span", class_="name")
                if name_span:
                    full_name_text = name_span.get_text(strip=True)
                    des_span = name_span.find("span", class_="des")
                    if des_span:
                        player_name = full_name_text.replace(des_span.get_text(strip=True), "").strip()
                    else:
                        player_name = full_name_text
                else:
                    player_name = ""

                # 2. 데이터 span들 추출 [포지션, 나이, 몸값, 계약만료]
                all_spans = li.find_all("span")
                data_spans = [s for s in all_spans if not s.find_parent("span", class_="name") and s.get_text(strip=True)]
                
                if len(data_spans) >= 3:
                    position = data_spans[0].get_text(strip=True)
                    age = data_spans[1].get_text(strip=True)
                    raw_value = data_spans[2].get_text(strip=True)
                    
                    # 몸값 원화 변환 (계약 만료 제외)
                    krw_value = convert_market_value_to_krw(raw_value)
                    
                    if player_name:
                        player_info = {
                            "name": player_name,
                            "position": position,
                            "age": age,
                            "market_value_krw": krw_value
                        }
                        squad_list.append(player_info)
            except Exception:
                continue
                
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

    # 💡 [테스트용 제한] 우선 딱 1개 경기만 테스트 수집
    target_matches = target_matches[:1]
    print(f"🎯 [V5-1 테스트 모드] 조건에 일치하는 대진 중 **딱 1개 경기** 선수 명단 수집 시작")

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
            detail_url = f"https://www.scoreman123.com/match/data-{m_id}"
            
            print(f"🏟️ 매치 페이지 접속 중: {main_home} vs {main_away} (Code: {m_id})")
            
            home_squad = []
            away_squad = []
            
            try:
                driver.get(detail_url)
                time.sleep(1.0)
                
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # 홈팀 및 원정팀 구단 summary URL 추출 (div.home, div.guest 내부 data-url 활용)
                home_div = soup.find("div", class_="home")
                guest_div = soup.find("div", class_="guest")
                
                home_summary_url = ""
                away_summary_url = ""
                
                if home_div and home_div.has_attr("data-url"):
                    home_summary_url = "https:" + home_div["data-url"] if home_div["data-url"].startswith("//") else home_div["data-url"]
                
                if guest_div and guest_div.has_attr("data-url"):
                    away_summary_url = "https:" + guest_div["data-url"] if guest_div["data-url"].startswith("//") else guest_div["data-url"]
                
                # 1. 홈팀 선수 명단 수집
                if home_summary_url:
                    print(f"  - 홈팀({main_home}) 선수 명단 수집 중...")
                    home_squad = parse_team_squad(driver, home_summary_url)
                
                # 2. 원정팀 선수 명단 수집
                if away_summary_url:
                    print(f"  - 원정팀({main_away}) 선수 명단 수집 중...")
                    away_squad = parse_team_squad(driver, away_summary_url)
                
            except Exception as e:
                print(f"  ⚠️ 구단 링크 추출 및 선수 명단 수집 실패: {e}")

            squad_details[m_id] = {
                "match_code": m_id,
                "home": main_home,
                "away": main_away,
                "home_squad": home_squad,
                "away_squad": away_squad
            }

        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "squad_details": squad_details
        }
        
        with open("match_details_v5-1.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 1개 경기 홈/원정 선수 명단 수집 완료 -> match_details_v5-1.json 저장 완료")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_squad_crawler_v5_1()
