from datetime import datetime, timedelta
import json
import time
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from zoneinfo import ZoneInfo

# 💡 [속도 최적화] 동일한 구단 summary URL의 선수 명단은 캐싱하여 중복 접속 방지
_team_squad_cache = {}

def convert_market_value_to_krw(val_str):
    if not val_str or val_str == "-" or "£" not in val_str:
        return "-"
    try:
        clean_val = val_str.replace("£", "").replace("M", "").strip()
        mil_val = float(clean_val)
        krw_billion = mil_val * 1800  # 파운드당 대략적인 원화 환산 (억 원 단위)
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
    💡 구단 페이지의 선수 명단 li 항목에서 이름, 포지션, 나이, 몸값을 안전하게 추출하도록 개선된 파서
    """
    if team_summary_url in _team_squad_cache:
        return _team_squad_cache[team_summary_url]

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
                # 1. 선수 이름 추출 (span.name 내부 처리)
                name_span = li.find("span", class_="name")
                player_name = ""
                if name_span:
                    full_text = name_span.get_text(strip=True)
                    des_span = name_span.find("span", class_="des")
                    if des_span:
                        des_text = des_span.get_text(strip=True)
                        player_name = full_text.replace(des_text, "").strip()
                    else:
                        player_name = full_text

                # 2. li 안의 모든 span 태그 중 의미 있는 텍스트를 가진 요소들을 순서대로 추출
                spans = li.find_all("span")
                valid_texts = []
                for s in spans:
                    # name span 내부의 자식 태그이거나, des 클래스인 경우는 이름/등번호/국가 부가정보이므로 제외
                    if s.find_parent("span", class_="name") or "des" in s.get("class", []):
                        continue
                    
                    txt = s.get_text(strip=True)
                    # 빈 텍스트가 아니고, 아바타 랩 등 레이아웃용 태그가 아닐 때만 수집
                    if txt and "avatar" not in s.get("class", [""])[0]:
                        if txt not in valid_texts:  # 중복 추가 방지
                            valid_texts.append(txt)

                # 보통 유효 텍스트 순서: [포지션, 나이, 몸값, 계약만료] 형태 등으로 잡힙니다.
                # 예: ['공격수', '25', '£140.000M', '2029.06.30']
                if len(valid_texts) >= 3:
                    position = valid_texts[0]
                    age = valid_texts[1]
                    raw_value = valid_texts[2]
                    
                    # 몸값 원화 변환
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
        
    _team_squad_cache[team_summary_url] = squad_list
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

    # 💡 [테스트용 제한] 1개 경기 테스트 (전체 수집 시 주석 처리)
    target_matches = target_matches[:1]
    print(f"🎯 [V5-1] 총 {len(target_matches)}개 경기 선수 명단 수집 시작")

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
            
            home_squad, away_squad = [], []
            try:
                driver.get(detail_url)
                time.sleep(0.8)
                
                soup = BeautifulSoup(driver.page_source, "html.parser")
                home_div = soup.find("div", class_="home")
                guest_div = soup.find("div", class_="guest")
                
                home_summary_url, away_summary_url = "", ""
                if home_div and home_div.has_attr("data-url"):
                    home_summary_url = "https:" + home_div["data-url"] if home_div["data-url"].startswith("//") else home_div["data-url"]
                if guest_div and guest_div.has_attr("data-url"):
                    away_summary_url = "https:" + guest_div["data-url"] if guest_div["data-url"].startswith("//") else guest_div["data-url"]
                
                if home_summary_url:
                    home_squad = parse_team_squad(driver, home_summary_url)
                if away_summary_url:
                    away_squad = parse_team_squad(driver, away_summary_url)
                
            except Exception as e:
                print(f"  ⚠️ 수집 실패 ({m_id}): {e}")

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
            
        print(f"\n🎉 성공: 선수 명단 수집 및 캐싱 최적화 완료 -> match_details_v5-1.json 저장 완료")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_squad_crawler_v5_1()
