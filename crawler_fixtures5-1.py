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
    💡 [완벽 개선된 파서] 순서 밀림 현상에 대응하여 포지션 키워드 및 태그 구조를 지능형으로 탐색하는 파서
    """
    if team_summary_url in _team_squad_cache:
        return _team_squad_cache[team_summary_url]

    squad_list = []
    # 확실하게 판정할 포지션 키워드 목록
    position_keywords = ["포워드", "공격수", "미드필더", "수비수", "골키퍼", "FW", "MF", "DF", "GK"]

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
                # 1. [이름 추출] span.name 안에서 순수 선수 이름 추출
                name_span = li.find("span", class_="name")
                player_name = ""
                if name_span:
                    des_span = name_span.find("span", class_="des")
                    if des_span:
                        des_text = des_span.get_text(strip=True)
                        full_text = name_span.get_text(strip=True)
                        player_name = full_text.replace(des_text, "").strip()
                    else:
                        player_name = name_span.get_text(strip=True)

                if not player_name:
                    continue

                # 2. [직계 및 하위 span 전체 텍스트 수집]
                child_spans = li.find_all("span")
                valid_texts = [s.get_text(strip=True) for s in child_spans if s.get_text(strip=True)]

                # 3. [지능형 필드 매핑: 포지션 키워드 우선 탐색]
                position = "-"
                number_info = valid_texts[0] if len(valid_texts) > 0 else "-"
                
                # 수집된 텍스트 중 포지션 키워드가 포함된 항목이 있다면 우선적으로 position으로 지정
                for txt in valid_texts:
                    if any(kw in txt for kw in position_keywords):
                        position = txt
                        break
                
                # 만약 키워드로 못 찾았다면 기존 인덱스 방식(valid_texts[1])을 차선책으로 사용
                if position == "-" and len(valid_texts) > 1:
                    position = valid_texts[1]

                # 등번호 정보 재탐색 (이름과 포지션이 아닌 첫 번째 값)
                for txt in valid_texts:
                    if txt != player_name and txt != position:
                        number_info = txt
                        break

                player_info = {
                    "name": player_name,
                    "player_number_info": number_info,  
                    "position": position                 # 정확하게 파싱된 진짜 포지션 값 장착
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

    # 💡 [전체 수집 활성화] 테스트용 슬라이싱(:1 등)을 완전히 제거하여 모든 대상 경기를 순회합니다.
    print(f"🎯 [V5-1] 총 {len(target_matches)}개 경기 선수 명단 전체 수집 시작")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    squad_details = {}

    try:
        for idx, target in enumerate(target_matches, 1):
            m_id = target["match_code"]
            main_home = target["home"]
            main_away = target["away"]
            detail_url = f"https://www.scoreman123.com/match/data-{m_id}"
            
            print(f"  [{idx}/{len(target_matches)}] 수집 중: {main_home} vs {main_away} (Code: {m_id})")
            
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
            
        print(f"\n🎉 성공: 대상 경기 전체 ({len(target_matches)}개) 선수 명단 수집 및 최적화 완료 -> match_details_v5-1.json 저장 완료")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_squad_crawler_v5_1()
