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

def parse_team_squad(driver, team_summary_url):
    """
    💡 텍스트 내에서 중복되는 선수 이름을 정제하여 단 한 번만 남기고,
       포지션과 나이를 정확히 매칭하는 정밀 파서
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
                # 1. span.name 전체 텍스트 가져오기
                name_span = li.find("span", class_="name")
                raw_name_text = name_span.get_text(strip=True) if name_span else ""
                
                # 2. [핵심] 만약 이름이 두 번 겹쳐서 들어가 있다면 하나를 날려버림
                # 예: "아산 디아오아산 디아오#11 세네갈" -> 이름을 두 번 찾아서 하나로 정제
                des_span = name_span.find("span", class_="des") if name_span else None
                des_text = des_span.get_text(strip=True) if des_span else ""
                
                # 순수 선수 이름 추출 (중복 제거 및 des 영역 분리)
                if des_text:
                    player_name = raw_name_text.replace(des_text, "").strip()
                else:
                    player_name = raw_name_text
                
                # 만약 이름 자체가 내부에서 두 번 반복되어 붙어 있다면 반으로 쪼개서 하나만 남김
                half_len = len(player_name) // 2
                if len(player_name) > 4 and player_name[:half_len] == player_name[half_len:half_len*2]:
                    player_name = player_name[:half_len].strip()

                # 3. 나머지 데이터(포지션, 나이) 추출
                child_spans = li.find_all("span", recursive=False)
                valid_texts = []
                for s in child_spans:
                    if "name" in s.get("class", []):
                        continue
                    txt = s.get_text(strip=True)
                    if txt:
                        valid_texts.append(txt)

                position = valid_texts[0] if len(valid_texts) > 0 else "-"
                age = valid_texts[1] if len(valid_texts) > 1 else "-"

                if player_name:
                    player_info = {
                        "name": player_name,
                        "position": position,
                        "age": age
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

    # 💡 [테스트용 제한] 1개 경기 테스트 (전체 수집 시 주석 처리 가능)
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
