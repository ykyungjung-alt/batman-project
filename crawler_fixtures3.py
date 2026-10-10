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

def fetch_opponent_stats_and_tiers(driver, sub_m_id, target_team_name):
    """
    서브 경기 페이지로 이동하여 target_team_name이 아닌 '상대 팀'의 득실점을 판별하고 티어를 산출합니다.
    """
    sub_url = f"https://www.scoreman123.com/match/data-{sub_m_id}"
    try:
        driver.get(sub_url)
        time.sleep(0.8)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        sub_home, sub_away = "", ""
        teams_spans = soup.find_all("span", class_=["home", "away"])
        if len(teams_spans) >= 2:
            sub_home = teams_spans[0].get_text(strip=True)
            sub_away = teams_spans[1].get_text(strip=True)
        else:
            header_div = soup.find("div", id="dv_header") or soup.find("div", class_="vs")
            if header_div:
                t_texts = header_div.get_text(separator="|", strip=True).split("|")
                if len(t_texts) >= 2:
                    sub_home = t_texts[0].strip()
                    sub_away = t_texts[-1].strip()

        recent_div = soup.find("div", id="dv_recent")
        if recent_div:
            stats_div = recent_div.find("div", id="dv_recent_stats")
            if stats_div:
                home_goals, home_conceded = "0", "0"
                away_goals, away_conceded = "0", "0"
                
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
                
                is_target_home = target_team_name in sub_home or not (target_team_name in sub_away)
                
                if is_target_home:
                    opp_goals = away_goals
                    opp_conceded = away_conceded
                else:
                    opp_goals = home_goals
                    opp_conceded = home_conceded
                
                atk_tier = calculate_attack_tier(opp_goals)
                def_tier = calculate_defense_tier(opp_conceded)
                
                return f"{opp_goals}/{opp_conceded} 공격력{atk_tier.replace('Tier ', '')}/방어력{def_tier.replace('Tier ', '')}"
    except Exception as e:
        print(f"    - 서브 경기({sub_m_id}) 상대 티어 산출 예외: {e}")
    
    return "0.00/0.00 공격력C/방어력C"

def run_table_based_crawler_v3():
    if not os.path.exists("data.json"):
        print("❌ data.json 파일이 존재하지 않습니다.")
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
    print(f"📅 [V3] 타겟 날짜 키 패턴: {target_date_key_prefix}")

    for date_key, matches in daily_matches_input.items():
        if date_key.startswith(target_date_key_prefix):
            print(f"🎯 발견한 경기 블록: {date_key}")
            for m in matches:
                m_code = m.get("match_code")
                if m_code and m_code not in [t["match_code"] for t in target_matches]:
                    target_matches.append({
                        "match_code": m_code,
                        "league": m.get("league", ""),
                        "home": m.get("home", ""),
                        "away": m.get("away", "")
                    })
                if len(target_matches) >= 3:
                    break
        if len(target_matches) >= 3:
            break

    print(f"🎯 [V3] 총 {len(target_matches)}개 메인 경기 크롤링 시작")

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
                time.sleep(1.5)
                
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

                team_tiers_data = {"home": {}, "away": {}}
                
                # 1️⃣ [보존] 기존 최근전적(전체) 데이터 수집용 컨테이너
                recent_form_data = {
                    "home_team_name": main_home, "home_matches": [], 
                    "away_team_name": main_away, "away_matches": []
                }
                
                # 2️⃣ [신규] 구장별 전적(홈/원정 맞춤) 데이터 수집용 컨테이너
                stadium_form_data = {
                    "home_team_name": main_home, "home_matches": [], 
                    "away_team_name": main_away, "away_matches": []
                }
                
                try:
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

                    # 공통 수집 헬퍼 함수 (상대 티어 산출 포함)
                    def parse_matches_from_ul(container_ul, target_team, target_list, max_count=10):
                        if not container_ul: return
                        count = 0
                        for li in container_ul.find_all("li", class_="courselis"):
                            if count >= max_count: break
                            if "ftScore" in str(li) or li.find("span", class_="ftScore"):
                                league_div = li.find("div", class_="team")
                                time_span = li.find("span", {"name": "timeData"})
                                
                                team_spans = li.find_all("span")
                                teams_text = ""
                                span_texts = [s.get_text(strip=True) for s in team_spans if s.get_text(strip=True) and not s.has_attr("name")]
                                if len(span_texts) >= 2:
                                    teams_text = f"{span_texts[0]} vs {span_texts[1]}"
                                
                                ft_scores = [span.get_text(strip=True) for span in li.find_all("span", class_="ftScore")]
                                
                                sub_m_id = None
                                for el in li.find_all(attrs={"onclick": True}):
                                    onclick_attr = el["onclick"]
                                    if "soccerInPage.analysis" in onclick_attr:
                                        try:
                                            sub_m_id = onclick_attr.split("'")[1]
                                            break
                                        except: pass
                                
                                opponent_tier_info = "정보 없음"
                                if sub_m_id:
                                    opponent_tier_info = fetch_opponent_stats_and_tiers(driver, sub_m_id, target_team)
                                    driver.get(detail_url)
                                    time.sleep(0.4)

                                match_info = {
                                    "league": league_div.get_text(strip=True) if league_div else "",
                                    "match_time": time_span.get_text(strip=True) if time_span else "",
                                    "teams": teams_text,
                                    "ft_scores": ft_scores,
                                    "opponent_tier_info": opponent_tier_info
                                }
                                if match_info["ft_scores"] and match_info not in target_list:
                                    target_list.append(match_info)
                                    count += 1

                    # A. [단계 1] 최근전적 (기본 전체 상태) 수집
                    home_ul = detail_soup.find("ul", id="tb_home_recent")
                    away_ul = detail_soup.find("ul", id="tb_guest_recent")
                    
                    if home_ul: parse_matches_from_ul(home_ul, main_home, recent_form_data["home_matches"], 10)
                    if away_ul: parse_matches_from_ul(away_ul, main_away, recent_form_data["away_matches"], 10)

                    # B. [단계 2] 구장별 전적 ('같은 H/A' 체크박스 클릭 후 상태) 수집
                    try:
                        checkbox = driver.find_element("id", "cbRecentFull")
                        if checkbox and not checkbox.is_selected():
                            driver.execute_script("arguments[0].click();", checkbox)
                            time.sleep(1.0)
                            
                        stadium_soup = BeautifulSoup(driver.page_source, "html.parser")
                        s_home_ul = stadium_soup.find("ul", id="tb_home_recent")
                        s_away_ul = stadium_soup.find("ul", id="tb_guest_recent")
                        
                        if s_home_ul: parse_matches_from_ul(s_home_ul, main_home, stadium_form_data["home_matches"], 10)
                        if s_away_ul: parse_matches_from_ul(s_away_ul, main_away, stadium_form_data["away_matches"], 10)
                    except Exception as s_err:
                        print(f"  - 구장별 전적(after) 토글 수집 예외: {s_err}")

                except Exception as e:
                    print(f"  - 전적 수집 통합 예외 ({m_id}): {e}")

                match_details[m_id] = {
                    "match_code": m_id,
                    "head_info": head_info,
                    "home": main_home,
                    "away": main_away,
                    "meta_details": {
                        "team_tiers": team_tiers_data,
                        "recent_form": recent_form_data,     # 💡 기존 최근전적 보존
                        "stadium_form": stadium_form_data   # 💡 신규 구장별 전적 분리 수집
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
            
        print(f"\n🎉 성공: 최근전적과 구장별 전적 양쪽 모두 10경기 및 상대 티어 태깅 완료 -> match_details_v3.json 저장 완료")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler_v3()
