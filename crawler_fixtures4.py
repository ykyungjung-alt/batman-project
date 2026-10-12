import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def crawl_multiple_leagues():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    # 💡 수집하고자 하는 실제 리그 URL 또는 ID 리스트
    target_leagues = [
        {"id": 34, "url": "https://football.scoreman123.com/league/34"},
        {"id": 39, "url": "https://football.scoreman123.com/league/39"},
        {"id": 40, "url": "https://football.scoreman123.com/league/40"}
    ]

    try:
        for league in target_leagues:
            league_id = league["id"]
            target_url = league["url"]
            print(f"\n==========================================")
            print(f"🚀 [페이지 전환 및 수집 시작] 리그 ID: {league_id} ({target_url})")
            
            # 1. 확실하게 새로운 페이지로 이동
            driver.get(target_url)
            
            # 2. 페이지가 완전히 바뀔 때까지 충분히 대기 (이전 페이지 잔상 방지)
            time.sleep(2.0)
            
            match_data = {
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "league_id": league_id,
                "league_name": "",
                "active_round": "",
                "total_rounds": "",
                "standings": []
            }

            try:
                # 3. 해당 페이지의 순위표(#standingList)나 타이틀이 로드될 때까지 대기
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#standingList")))

                # 리그명 추출
                title_elem = driver.find_element(By.CSS_SELECTOR, "div.box h4, .league_title, h4")
                if title_elem:
                    txt = title_elem.text.strip()
                    if txt and txt not in ["일정", "대진표", "팀순위", "정보", "오즈통계", "베스트11"]:
                        match_data["league_name"] = txt.replace("라이브스코어", "").strip()
                
                if not match_data["league_name"]:
                    match_data["league_name"] = f"리그 ID {league_id}"

                # 4. 활성 라운드 추출 (div.round 안의 span 탐색)
                active_text = "1"
                round_spans = driver.find_elements(By.CSS_SELECTOR, "div.round span")
                for span in round_spans:
                    outer_html = span.get_attribute("outerHTML")
                    if "current" in outer_html or "style class" in outer_html:
                        active_text = span.get_attribute("round").strip()
                        break
                
                total_cnt = len(round_spans) if round_spans else 38
                match_data["active_round"] = active_text
                match_data["total_rounds"] = str(total_cnt)

                # 5. 해당 페이지의 순위표 데이터 파싱
                standings_items = driver.find_elements(By.CSS_SELECTOR, "#standingList li.standis")
                parsed_standings = []
                
                for item in standings_items:
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
                            "경기수": stat_slice[0] if len(stat_slice) > 0 else "",
                            "승": stat_slice[1] if len(stat_slice) > 1 else "",
                            "무": stat_slice[2] if len(stat_slice) > 2 else "",
                            "패": stat_slice[3] if len(stat_slice) > 3 else "",
                            "득실": stat_slice[4] if len(stat_slice) > 4 else "",
                            "승점": stat_slice[5] if len(stat_slice) > 5 else ""
                        })

                match_data["standings"] = parsed_standings
                print(f"✅ [{match_data['league_name']}] 수집 완료 (Active Round: {match_data['active_round']} / 팀 수: {len(parsed_standings)}개)")

            except Exception as e:
                print(f"⚠️ 리그 ID {league_id} 파싱 중 에러 발생: {e}")

            # 6. 각 리그별로 고유 파일명으로 각각 저장되도록 분기
            output_filename = f"match_details_league_{league_id}.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(match_data, f, ensure_ascii=False, indent=4)
            print(f"📁 [{output_filename}] 저장 완료.")

    finally:
        driver.quit()
        print("\n🏁 모든 페이지 순회 작업 종료.")

if __name__ == "__main__":
    crawl_multiple_leagues()
