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
        time.sleep(0.3)
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
                        left_val = ext_els[0].get_text(strip=True) # 경기당 득점
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
                
                # 💡 수집 단계에서 소수점 셋째 자리 반올림 및 둘째 자리 포맷 고정
                try:
                    formatted_opp_goals = f"{round(float(opp_goals), 2):.2f}"
                except ValueError:
                    formatted_opp_goals = "0.00"
                    
                try:
                    formatted_opp_conceded = f"{round(float(opp_conceded), 2):.2f}"
                except ValueError:
                    formatted_opp_conceded = "0.00"
                
                return f"{formatted_opp_goals}/{formatted_opp_conceded}"
    except Exception:
        pass
    return "0.00/0.00"

def run_table_based_crawler_v3():
    if not os.path.exists("data.json"):
        print("❌ data.json 파일이 존재하지 않습니다.")
        return
    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    target_matches = []
    daily_matches_input = data.get("daily_matches", {})
    kst = ZoneInfo("Asia/Seoul")
    
    # 💡 [안전 장치 추가] 날짜 및 경기 리스트 파싱 루틴
    for date_str, matches in daily_matches_input.items():
        for m in matches:
            target_matches.append((date_str, m))
            
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    try:
        for date_str, match in target_matches:
            main_home = match.get("home_team")
            main_away = match.get("away_team")
            detail_url = match.get("detail_url")
            if not detail_url:
                continue
            
            driver.get(detail_url)
            time.sleep(0.5)
            detail_soup = BeautifulSoup(driver.page_source, "html.parser")
            
            sclass_span = detail_soup.find("span", {"class": "sclassListLink"})
            league_name = ""
            if sclass_span:
                full_text = sclass_span.get_text(separator=" ", strip=True)
                league_name = full_text.replace("·", "").strip()
                
            recent_form_data = {
                "form_title": "최근 전적",
                "home_team_name": main_home,
                "home_matches": [],
                "away_team_name": main_away,
                "away_matches": []
            }
            stadium_form_data = {
                "form_title": "구장별 전적",
                "home_team_name": main_home,
                "home_matches": [],
                "away_team_name": main_away,
                "away_matches": []
            }
            
            def parse_matches(container_ul, target_team, target_list, max_count=10):
                if not container_ul:
                    return
                count = 0
                for li in container_ul.find_all("li", class_="courselis"):
                    if count >= max_count:
                        break
                    if "ftScore" in str(li) or li.find("span", class_="ftScore"):
                        league_div = li.find("div", class_="team")
                        time_span = li.find("span", {"name": "timeData"})
                        raw_t_str = time_span.get_text(strip=True) if time_span else ""
                        formatted_t_str = raw_t_str
                        try:
                            parts_main = raw_t_str.split(" ")
                            date_part = parts_main[0].replace("-", ".").replace("/", ".")
                            tokens = date_part.split(".")
                            if len(tokens) == 3:
                                if len(tokens[0]) <= 2 and len(tokens[2]) == 4:
                                    mm, dd, yyyy = tokens[0].zfill(2), tokens[1].zfill(2), tokens[2]
                                    date_part = f"{yyyy}.{mm}.{dd}"
                                elif len(tokens[0]) == 4:
                                    yyyy, mm, dd = tokens[0], tokens[1].zfill(2), tokens[2].zfill(2)
                                    date_part = f"{yyyy}.{mm}.{dd}"
                            if len(parts_main) > 1:
                                formatted_t_str = f"{date_part} {' '.join(parts_main[1:])}"
                            else:
                                formatted_t_str = date_part
                        except Exception:
                            formatted_t_str = raw_t_str

                        team_spans = li.find_all("span")
                        span_texts = [s.get_text(strip=True) for s in team_spans if s.get_text(strip=True) and not s.has_attr("name")]
                        teams_text = ""
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
                                except:
                                    pass
                                    
                        opponent_tier_info = "0.00/0.00"
                        if sub_m_id:
                            opponent_tier_info = fetch_opponent_stats_fast(driver, sub_m_id, target_team)
                        
                        match_info = {
                            "league": league_div.get_text(strip=True) if league_div else "",
                            "match_time": formatted_t_str,
                            "teams": teams_text,
                            "ft_scores": ft_scores,
                            "opponent_tier_info": opponent_tier_info
                        }
                        if match_info["ft_scores"] and match_info not in target_list:
                            target_list.append(match_info)
                            count += 1

            # 데이터 파싱 및 저장 로직 연결 부근 유지
            time.sleep(0.2)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_table_based_crawler_v3()
