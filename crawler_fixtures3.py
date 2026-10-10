from datetime import datetime, timedelta
import json
import time
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from zoneinfo import ZoneInfo

def calculate_attack_tier(avg_goals):
    try:
        g = float(avg_goals)
        if g < 0.5: return "Tier E"
        elif 0.5 <= g < 1.1: return "Tier D"
        elif 1.1 <= g < 1.6: return "Tier C"
        elif 1.6 <= g < 2.3: return "Tier B"
        else: return "Tier A"
    except:
        return "Tier C"

def calculate_defense_tier(avg_conceded):
    try:
        c = float(avg_conceded)
        if c < 0.5: return "Tier A"
        elif 0.5 <= c < 0.9: return "Tier B"
        elif 0.9 <= c < 1.3: return "Tier C"
        elif 1.3 <= c < 1.7: return "Tier D"
        else: return "Tier E"
    except:
        return "Tier C"

def run_table_based_crawler_v3():
    if not os.path.exists("data.json"):
        print("❌ data.json 파일이 존재하지 않습니다. 먼저 update_data.py를 실행해 주세요.")
        return

    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    target_matches = []
    daily_matches_input = data.get("daily_matches", {})
    
    kst = ZoneInfo("Asia/Seoul")
    today_kst = datetime.now(kst)
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    
    target_dt = today_kst + timedelta(days=1)
    m_str = target_dt.strftime("%m")
    d_str = target_dt.strftime("%d")
    w_str = weekdays[target_dt.weekday()]
    
    target_date_key_prefix = f"{m_str}-{d_str} ({w_str})"
    print(f"📅 [V3] 동적 계산된 타겟 날짜 키 패턴: {target_date_key_prefix}")

    for date_key, matches in daily_matches_input.items():
        if date_key.startswith(target_date_key_prefix):
            print(f"🎯 발견한 경기 블록: {date_key} (총 {len(matches)}개 경기 중 일부 탐색)")
            for m in matches:
                m_code = m.get("match_code")
                if m_code and m_code not in [t["match_code"] for t in target_matches]:
                    target_matches.append({
                        "match_code": m_code,
                        "league": m.get("league", ""),
                        "home": m.get("home", ""),
                        "away": m.get("away", "")
                    })
                # 💡 테스트를 위해 전체 중 딱 3개 페어만 수집되도록 제한
                if len(target_matches) >= 3:
                    break
        if len(target_matches) >= 3:
            break

    print(f"🎯 [V3 테스트 모드] 총 {len(target_matches)}개 경기만 추출하여 수집 시작")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    match_details = {}
    counter = 1

    try:
        for target in target_matches:
            m_id = target["match_code"]
            main_home = target["home"]
            main_away = target["away"]
            detail_url = f"https://www.scoreman123.com/match/data-{m_id}"
            
            try:
                driver.get(detail_url)
                time.sleep(1.2)
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                head_info = {
                    "league": target["league"],
                    "round": "",
                    "match_time_display": ""
                }
                
                try:
                    sclass_span = detail_soup.find("span", {"class": "sclassListLink"})
                    if sclass_span:
                        full_text = sclass_span.get_text(separator=" ", strip=True)
                        head_info["league"] = full_text.replace("·", "").strip()
                    
                    time_span = detail_soup.find("span", {"name": "timeData"})
                    if time_span:
                        head_info["match_time_display"] = time_span.get_text(strip=True)
                except Exception:
                    pass

                recent_form_data = {"home_matches": [], "away_matches": []}
                team_tiers_data = {"home": {}, "away": {}}
                
                try:
                    # 1. 메인 팀 전체 공수 티어 산정
                    recent_div = detail_soup.find("div", id="dv_recent")
                    if recent_div:
                        stats_div = recent_div.find("div", id="dv_recent_stats")
                        if stats_div:
                            home_goals, home_conceded = 0.0, 0.0
                            away_goals, away_conceded = 0.0, 0.0
                            
                            for v in stats_div.find_all("div", class_="vote"):
                                ext_els = v.find_all("div", class_=["ext", "win-f", "draw-f", "p2"])
                                if len(ext_els) >= 3:
                                    left_val = ext_els[0].get_text(strip=True)
                                    label = ext_els[1].get_text(strip=True)
                                    right_val = ext_els[2].get_text(strip=True)
                                    
                                    if "경기당 득점" in label:
                                        home_goals = left_val
                                        away_goals = right_val
                                    elif "경기당 실점" in label:
                                        home_conceded = left_val
                                        away_conceded = right_val

                            team_tiers_data["home"] = {
                                "attack_tier": calculate_attack_tier(home_goals),
                                "defense_tier": calculate_defense_tier(home_conceded)
                            }
                            team_tiers_data["away"] = {
                                "attack_tier": calculate_attack_tier(away_goals),
                                "defense_tier": calculate_defense_tier(away_conceded)
                            }

                    # 2. 홈팀 최근전적 (최대 20경기, ftScore까지)
                    home_coursebox = detail_soup.find("ul", id="tb_home_recent")
                    if home_coursebox:
                        for c_item in home_coursebox.find_all("li", class_="courselis", limit=20):
                            league_div = c_item.find("div", class_="team")
                            time_span = c_item.find("span", {"name": "timeData"})
                            teams_div = c_item.find("div", class_="corteam")
                            
                            ft_scores = [span.get_text(strip=True) for span in c_item.find_all("span", class_="ftScore")]
                            teams_text = teams_div.get(separator=" vs ", strip=True) if teams_div else ""
                            
                            opponent_tier_tag = ""
                            if " vs " in teams_text:
                                t_parts = teams_text.split(" vs ")
                                p_home = t_parts[0].strip()
                                p_away = t_parts[1].strip()
                                opponent_name = p_away if p_home == main_home else p_home
                                opponent_tier_tag = f"상대({opponent_name}): 대기중"

                            match_info = {
                                "league": league_div.get_text(strip=True) if league_div else "",
                                "match_time": time_span.get_text(strip=True) if time_span else "",
                                "teams": teams_text,
                                "ft_scores": ft_scores,
                                "opponent_tier_info": opponent_tier_tag
                            }
                            if match_info["teams"] and match_info not in recent_form_data["home_matches"]:
                                recent_form_data["home_matches"].append(match_info)

                    # 3. 원정팀 최근전적 (최대 20경기, ftScore까지)
                    away_coursebox = detail_soup.find("ul", id="tb_guest_recent")
                    if away_coursebox:
                        for c_item in away_coursebox.find_all("li", class_="courselis", limit=20):
                            league_div = c_item.find("div", class_="team")
                            time_span = c_item.find("span", {"name": "timeData"})
                            teams_div = c_item.find("div", class_="corteam")
                            
                            ft_scores = [span.get_text(strip=True) for span in c_item.find_all("span", class_="ftScore")]
                            teams_text = teams_div.get(separator=" vs ", strip=True) if teams_div else ""
                            
                            match_info = {
                                "league": league_div.get_text(strip=True) if league_div else "",
                                "match_time": time_span.get_text(strip=True) if time_span else "",
                                "teams": teams_text,
                                "ft_scores": ft_scores,
                                "opponent_tier_info": ""
                            }
                            if match_info["teams"] and match_info not in recent_form_data["away_matches"]:
                                recent_form_data["away_matches"].append(match_info)

                except Exception as e:
                    print(f"  - 최근전적 파싱 예외 ({m_id}): {e}")

                match_details[m_id] = {
                    "match_code": m_id,
                    "head_info": head_info,
                    "home": main_home,
                    "away": main_away,
                    "meta_details": {
                        "team_tiers": team_tiers_data,
                        "recent_form": recent_form_data
                    }
                }
                counter += 1

            except Exception as e:
                print(f"  ⚠️ 데이터 수집 실패 (Match ID: {m_id}): {e}")
                continue

        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "match_details": match_details
        }
        
        with open("match_details_v3.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 테스트 성공: 딱 3개 경기만 추출하여 match_details_v3.json 저장 완료")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler_v3()
