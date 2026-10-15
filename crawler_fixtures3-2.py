from datetime import datetime, timedelta
import json
import time
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from zoneinfo import ZoneInfo

def fetch_opponent_stats_fast(driver, sub_m_id, target_team_name):
    """
    💡 서브 페이지에 들어가서 순수하게 골득실(경기당 득점/실점) 수치만 가져오도록 최적화된 함수
    """
    sub_url = f"https://www.scoreman123.com/match/data-{sub_m_id}"
    try:
        driver.get(sub_url)
        time.sleep(0.5)  # 서브 페이지 로딩 대기
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        sub_home, sub_away = "", ""
        teams_spans = soup.find_all("span", class_=["home", "away"])
        if len(teams_spans) >= 2:
            sub_home = teams_spans[0].get_text(strip=True)
            sub_away = teams_spans[1].get_text(strip=True)

        recent_div = soup.find("div", id="dv_recent")
        if recent_div:
            stats_div = recent_div.find("div", id="dv_recent_stats")
            if stats_div:
                home_goals, home_conceded = "0.00", "0.00"
                away_goals, away_conceded = "0.00", "0.00"
                
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
                opp_goals = away_goals if is_target_home else home_goals
                opp_conceded = away_conceded if is_target_home else home_conceded
                
                return f"{opp_goals}/{opp_conceded}"
    except Exception:
        pass
    
    return "0.00/0.00"

def run_table_based_crawler_v3_2():
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
    
    print(f"🕒 [V3-2] 실행 시간(KST): {now_kst.strftime('%Y-%m-%d %H:%M')}")
    print(f"🎯 [V3-2] 수집 대상 타임라인 (~24시간 후): {limit_kst.strftime('%Y-%m-%d %H:%M')}")

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

    print(f"🎯 [V3-2] 24시간 이내 조건에 일치하는 총 {len(target_matches)}개 메인 경기 중 테스트를 위해 **1개만** 수집합니다.")

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
                time.sleep(2.0)  # 페이지 초기 로딩 대기 시간 확보
                
                # 💡 [드롭다운 제어 수정]: 'selRecentMatch' 클릭 후 팝업 메뉴 내 'v-data="20"' 항목 클릭
                try:
                    dropdown_btn = driver.find_element("id", "selRecentMatch")
                    if dropdown_btn:
                        driver.execute_script("arguments[0].click();", dropdown_btn)
                        time.sleep(1.0)  # 메뉴 열림 대기
                        
                        option_20 = driver.find_element("xpath", "//div[@id='selRecentMatchItem']//li[@v-data='20']")
                        if option_20:
                            driver.execute_script("arguments[0].click();", option_20)
                            time.sleep(2.0)  # 20개 항목 비동기 렌더링 완료 대기
                except Exception as drop_err:
                    print(f"  - 최근 20개 확장 드롭다운 클릭 예외 (기본값 진행): {drop_err}")

                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                head_info = {
                    "league": target["league"],
                    "round": ""
                }
                
                try:
                    sclass_span = detail_soup.find("span", {"class": "sclassListLink"})
                    if sclass_span:
                        full_text = sclass_span.get_text(separator=" ", strip=True)
                        head_info["league"] = full_text.replace("·", "").strip()
                except Exception:
                    pass

                # 💡 원정팀 관련 데이터 필드 제거 및 홈팀 전적 구조만 유지
                recent_form_data = {
                    "form_title": "최근 전적",
                    "home_team_name": main_home, 
                    "home_matches": []
                }
                
                stadium_form_data = {
                    "form_title": "구장별 전적",
                    "home_team_name": main_home, 
                    "home_matches": []
                }
                
                try:
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
                                
                                opponent_tier_info = "0.00/0.00"
                                if sub_m_id:
                                    opponent_tier_info = fetch_opponent_stats_fast(driver, sub_m_id, target_team)
                                    driver.get(detail_url)
                                    time.sleep(0.5)  # 메인 페이지 복귀 후 대기

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

                    # 💡 홈팀 전적 데이터(tb_home_recent)만 수집 (원정팀 tb_guest_recent 제거)
                    home_ul = detail_soup.find("ul", id="tb_home_recent")
                    if home_ul: 
                        parse_matches(home_ul, main_home, recent_form_data["home_matches"], 20)

                except Exception as e:
                    print(f"  - 전적 수집 예외 ({m_id}): {e}")

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

            print(f"🎯 [테스트 모드] 메인 경기 1개 수집 완료. 크롤링을 종료합니다.")
            break

        output_data = {
            "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
            "match_details": match_details
        }
        
        with open("match_details_v3-2.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 성공: 20개 확장 선택 및 홈팀 전적 수집 완료 -> match_details_v3-2.json 저장 완료")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler_v3_2()
