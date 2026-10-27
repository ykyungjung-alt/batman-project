from datetime import datetime, timedelta
import json
import time
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from zoneinfo import ZoneInfo

# 💡 [속도 최적화] 동일한 서브 페이지 ID 결과는 메모리에 캐싱하여 중복 이동(`driver.get`)을 원천 방지
_opponent_stats_cache = {}

def get_atk_tier_char(val):
    if val >= 2.3: return "A"
    elif val >= 1.7: return "B"
    elif val >= 1.1: return "C"
    elif val >= 0.5: return "D"
    else: return "E"

def get_def_tier_char(val):
    if val < 0.5: return "A"
    elif val < 0.9: return "B"
    elif val < 1.3: return "C"
    elif val < 1.7: return "D"
    else: return "E"

def fetch_opponent_stats_fast(driver, detail_url, sub_m_id, is_my_team_home):
    """
    💡 서브 페이지 골득실 수치 수집 및 '공격C(1.50)/방어E(1.90)' 형식 변환 함수
    - is_my_team_home: True면 내가 홈(상대방은 원정=오른쪽), False면 내가 원정(상대방은 홈=왼쪽)
    """
    if sub_m_id in _opponent_stats_cache:
        return _opponent_stats_cache[sub_m_id]

    sub_url = f"https://www.scoreman123.com/match/data-{sub_m_id}"
    try:
        driver.get(sub_url)
        time.sleep(0.3)  # 렌더링 안정 대기
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        recent_div = soup.find("div", id="dv_recent")
        if recent_div:
            stats_div = recent_div.find("div", id="dv_recent_stats")
            if stats_div:
                home_goals, home_conceded = "0.00", "0.00"
                away_goals, away_conceded = "0.00", "0.00"
                
                for v in stats_div.find_all("div", class_="vote"):
                    ext_els = v.find_all("div", class_=["ext", "win-f", "draw-f", "p2"])
                    if len(ext_els) >= 3:
                        left_val = ext_els[0].get_text(strip=True)   # 왼쪽 칸 (서브 페이지 홈팀)
                        label = ext_els[1].get_text(strip=True)
                        right_val = ext_els[2].get_text(strip=True)  # 오른쪽 칸 (서브 페이지 원정팀)
                        
                        if "경기당 득점" in label:
                            home_goals = left_val
                            away_goals = right_val
                        elif "경기당 실점" in label:
                            home_conceded = left_val
                            away_conceded = right_val
                
                # 🎯 [핵심 교차 매칭] 내가 홈이었으면 상대방(원정)인 오른쪽 수치를 가져오고,
                #                    내가 원정이었으면 상대방(홈)인 왼쪽 수치를 가져옴
                if is_my_team_home:
                    opp_g_str = away_goals
                    opp_c_str = away_conceded
                else:
                    opp_g_str = home_goals
                    opp_c_str = home_conceded
                
                try:
                    g_val = float(opp_g_str)
                    c_val = float(opp_c_str)
                except:
                    g_val, c_val = 0.00, 0.00

                # 💡 [핵심 추가] 득실점 수치를 바탕으로 공격/방어 티어 문자열 조합 (예: 공격C(1.50)/방어E(1.90))
                at_char = get_atk_tier_char(g_val)
                de_char = get_def_tier_char(c_val)
                
                result_val = f"공격{at_char}({g_val:.2f})/방어{de_char}({c_val:.2f})"
                _opponent_stats_cache[sub_m_id] = result_val
                return result_val
    except Exception:
        pass
    
    return "공격E(0.00)/방어E(0.00)"

def expand_dropdowns_to_20(driver):
    """
    💡 페이지 내 모든 'selRecentMatch' 드롭다운을 열어 'v-data="20"' 항목을 클릭하여 20개로 확장
    """
    try:
        dropdown_buttons = driver.find_elements("xpath", "//span[@id='selRecentMatch']")
        for d_btn in dropdown_buttons:
            try:
                driver.execute_script("arguments[0].click();", d_btn)
                time.sleep(0.1)
                
                option_20s = driver.find_elements("xpath", "//div[@id='selRecentMatchItem']//li[@v-data='20']")
                for opt in option_20s:
                    try:
                        driver.execute_script("arguments[0].click();", opt)
                        time.sleep(0.1)
                    except:
                        pass
            except:
                pass
    except Exception as e:
        print(f"  - 20개 확장 드롭다운 클릭 예외: {e}")

def run_table_based_crawler_v3():
    if not os.path.exists("data.json"):
        print("❌ data.json 파일이 존재하지 않습니다.")
        return

    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    target_matches = []
    daily_matches_input = data.get("daily_matches", {})
    
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
    limit_kst = now_kst + timedelta(hours=24)
    
    print(f"🕒 [V3] 실행 시간(KST): {now_kst.strftime('%Y-%m-%d %H:%M')}")
    print(f"🎯 [V3] 수집 대상 타임라인 (~24시간 후): {limit_kst.strftime('%Y-%m-%d %H:%M')}")

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

    print(f"🎯 [V3] 24시간 이내 조건에 일치하는 총 {len(target_matches)}개 메인 경기 전체 크롤링 시작")

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
                time.sleep(0.5)
                
                recent_form_data = {
                    "form_title": "최근 전적",
                    "home_team_name": main_home, "home_matches": [], 
                    "away_team_name": main_away, "away_matches": []
                }
                
                stadium_form_data = {
                    "form_title": "구장별 전적",
                    "home_team_name": main_home, "home_matches": [], 
                    "away_team_name": main_away, "away_matches": []
                }
                
                def parse_matches(container_ul, target_team, target_list, max_count=20):
                    if not container_ul: return
                    count = 0
                    for li in container_ul.find_all("li", class_="courselis"):
                        if count >= max_count: break
                        if "ftScore" in str(li) or li.find("span", class_="ftScore"):
                            league_div = li.find("div", class_="team")
                            time_span = li.find("span", {"name": "timeData"})
                            
                            raw_t_str = time_span.get_text(strip=True) if time_span else ""
                            match_time_val = raw_t_str
                            try:
                                parts = raw_t_str.split()
                                if len(parts) >= 2:
                                    d_part = parts[0].replace("-", ".").replace("/", ".")
                                    y_part = parts[1]
                                    d_tokens = d_part.split(".")
                                    if len(d_tokens) == 2:
                                        match_time_val = f"{y_part}.{d_tokens[0].zfill(2)}.{d_tokens[1].zfill(2)}"
                            except Exception:
                                pass
                            
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
                            
                            opponent_tier_info = "공격E(0.00)/방어E(0.00)"
                            if sub_m_id:
                                is_my_team_home = True
                                if " vs " in teams_text:
                                    parts = [p.strip() for p in teams_text.split(" vs ")]
                                    if len(parts) == 2:
                                        t1, t2 = parts[0], parts[1]
                                        # 💡 [핵심 정립] 대진표 좌측(t1)이 홈, 우측(t2)이 원정
                                        if target_team in t2 and target_team not in t1:
                                            is_my_team_home = False

                                opponent_tier_info = fetch_opponent_stats_fast(driver, detail_url, sub_m_id, is_my_team_home)
                                driver.get(detail_url)
                                time.sleep(0.1)

                            match_info = {
                                "league": league_div.get_text(strip=True) if league_div else "",
                                "match_time": match_time_val,
                                "teams": teams_text,
                                "ft_scores": ft_scores,
                                "opponent_tier_info": opponent_tier_info
                            }
                            if match_info["ft_scores"] and match_info not in target_list:
                                target_list.append(match_info)
                                count += 1

                # -------------------------------------------------------------
                # 1. [최근 전적] 20개 확장 클릭 후 수집
                # -------------------------------------------------------------
                try:
                    expand_dropdowns_to_20(driver)
                    detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                    
                    home_ul = detail_soup.find("ul", id="tb_home_recent")
                    away_ul = detail_soup.find("ul", id="tb_guest_recent")
                    if home_ul: parse_matches(home_ul, main_home, recent_form_data["home_matches"], 20)
                    if away_ul: parse_matches(away_ul, main_away, recent_form_data["away_matches"], 20)
                except Exception as e:
                    print(f"  - 최근 전적 수집 예외: {e}")

                # -------------------------------------------------------------
                # 2. [구장별 전적] 체크박스 클릭 후, 드롭다운 20개 확장 클릭 후 수집
                # -------------------------------------------------------------
                try:
                    checkbox = driver.find_element("id", "cbRecentFull")
                    if checkbox and not checkbox.is_selected():
                        driver.execute_script("arguments[0].click();", checkbox)
                        time.sleep(0.3)
                    
                    expand_dropdowns_to_20(driver)
                    
                    stadium_soup = BeautifulSoup(driver.page_source, "html.parser")
                    s_home_ul = stadium_soup.find("ul", id="tb_home_recent")
                    s_away_ul = stadium_soup.find("ul", id="tb_guest_recent")
                    
                    if s_home_ul: parse_matches(s_home_ul, main_home, stadium_form_data["home_matches"], 20)
                    if s_away_ul: parse_matches(s_away_ul, main_away, stadium_form_data["away_matches"], 20)
                except Exception as s_err:
                    print(f"  - 구장별 전적 토글 수집 예외: {s_err}")

                head_info = {"league": target["league"], "round": ""}
                try:
                    sclass_span = detail_soup.find("span", {"class": "sclassListLink"})
                    if sclass_span:
                        full_text = sclass_span.get_text(separator=" ", strip=True)
                        head_info["league"] = full_text.replace("·", "").strip()
                except Exception:
                    pass

                match_details[m_id] = {
                    "match_code": m_id,
                    "head_info": head_info,
                    "home": main_home,
                    "away": main_away,
                    "meta_details": {
                        "recent_form": recent_form_data,
                        "stadium_form": stadium_form_data
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
            
        print(f"\n🎉 성공: V3 20개 확장, 티어 포맷 변환 및 홈/원정 상대방 평득실 대칭 매칭 완료 -> match_details_v3.json 저장 완료")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler_v3()
