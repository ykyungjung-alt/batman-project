import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def run_crawler_v4():
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    # 💡 수집할 타겟 리그 리스트 (필요에 따라 ID 추가 가능)
    target_leagues = [
        {"id": 34, "url": "https://football.scoreman123.com/league/34"},
        {"id": 39, "url": "https://football.scoreman123.com/league/39"},
        {"id": 40, "url": "https://football.scoreman123.com/league/40"}
    ]

    all_leagues_data = {
        "updated_at": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
        "leagues": {}
    }

    try:
        for league in target_leagues:
            league_id = league["id"]
            target_url = league["url"]
            print(f"\n🔄 [탐색 중] 리그 ID {league_id} ({target_url})")
            
            driver.get(target_url)
            time.sleep(2.0) # 페이지 이동 후 렌더링 안정화 대기
            
            league_match_data = {
                "league_id": league_id,
                "league_name": "",
                "active_round": "1",
                "total_rounds": "38",
                "standings": [],
                "standing_legends": [
                    {"color": "#CCCCFF", "description": "승격팀"},
                    {"color": "#00CCCC", "description": "승격 플레이오프"},
                    {"color": "#B1A7A7", "description": "강등팀"}
                ]
            }

            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#standingList")))

                # 1. 리그명 추출
                try:
                    title_elem = driver.find_element(By.CSS_SELECTOR, "div.box h4, .league_title, h4")
                    txt = title_elem.text.strip()
                    if txt and txt not in ["일정", "대진표", "팀순위", "정보", "오즈통계", "베스트11"]:
                        league_match_data["league_name"] = txt.replace("라이브스코어", "").strip()
                except:
                    pass
                
                if not league_match_data["league_name"]:
                    league_match_data["league_name"] = f"리그 ID {league_id}"

                # 2. active_round 정밀 추출
                round_spans = driver.find_elements(By.CSS_SELECTOR, "div.round span")
                for span in round_spans:
                    outer_html = span.get_attribute("outerHTML")
                    if "current" in outer_html or "style class" in outer_html:
                        league_match_data["active_round"] = span.get_attribute("round").strip()
                        break
                
                if round_spans:
                    league_match_data["total_rounds"] = str(len(round_spans))

                # 3. 순위표 파싱
                standings_items = driver.find_elements(By.CSS_SELECTOR, "#standingList li.standis")
                parsed_standings = []
                
                for item in standings_items:
                    style_attr = item.get_attribute("style") or ""
                    tag_color = ""
                    if "--tagcolor:" in style_attr:
                        try:
                            tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                        except:
                            tag_color = ""

                    try:
                        rank_val = item.find_element(By.CSS_SELECTOR, ".rank em, .rank").text.strip()
                        team_val = item.find_element(By.CSS_SELECTOR, ".team .name, span.name").text.strip()
                    except:
                        continue

                    spans = item.find_elements(By.TAG_NAME, "span")
                    all_spans = [s.text.strip() for s in spans if s.text.strip()]

                    if rank_val and team_val:
                        stat_slice = all_spans[-6:] if len(all_spans) >= 6 else []
                        parsed_standings.append({
                            "rank": rank_val.replace("\n", "").strip(),
                            "team": team_val,
                            "tag_color": tag_color,
                            "tag_label": "강등팀" if tag_color == "#B1A7A7" else ("승격팀" if tag_color == "#CCCCFF" else ("승격 플레이오프" if tag_color == "#00CCCC" else "일반")),
                            "경기수": stat_slice[0] if len(stat_slice) > 0 else "",
                            "승": stat_slice[1] if len(stat_slice) > 1 else "",
                            "무": stat_slice[2] if len(stat_slice) > 2 else "",
                            "패": stat_slice[3] if len(stat_slice) > 3 else "",
                            "득실": stat_slice[4] if len(stat_slice) > 4 else "",
                            "승점": stat_slice[5] if len(stat_slice) > 5 else ""
                        })

                league_match_data["standings"] = parsed_standings
                print(f"✅ [{league_match_data['league_name']}] 수집 성공 (Round: {league_match_data['active_round']} / 팀 수: {len(parsed_standings)}개)")

            except Exception as page_err:
                print(f"⚠️ 리그 ID {league_id} 파싱 중 예외 발생: {page_err}")

            # 💡 각 리그별 데이터를 전체 딕셔너리에 담기
            all_leagues_data["leagues"][str(league_id)] = league_match_data

        # 💡 최종적으로 하나의 match_details_v4.json 파일에 병합 저장
        with open("match_details_v4.json", "w", encoding="utf-8") as f:
            json.dump(all_leagues_data, f, ensure_ascii=False, indent=4)
        print(f"\n🎉 [match_details_v4.json] 통합 저장 완료 (갱신 시간: {all_leagues_data['updated_at']})")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_crawler_v4()
