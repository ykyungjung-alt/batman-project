import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def crawl_leagues_v3_style():
    # 3번 코드와 동일하게 옵션 설정
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    # 💡 3번처럼 드라이버를 루프 밖에서 딱 한 번만 실행 (세션 유지)
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    target_league_ids = [34, 39, 40]

    try:
        for league_id in target_league_ids:
            target_url = f"https://football.scoreman123.com/league/{league_id}"
            print(f"\n--- [순차 수집] 리그 ID {league_id} 시작 ---")
            
            driver.get(target_url)
            
            # 💡 3번 코드처럼 페이지 이동 후 렌더링이 완전히 끝날 때까지 충분히 대기
            time.sleep(1.5) 
            
            match_data = {
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "league_id": league_id,
                "league_name": "",
                "active_round": "",
                "total_rounds": "",
                "standings": []
            }

            try:
                # 순위표와 라운드 바가 DOM에 완전히 올라올 때까지 대기
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#standingList")))

                # 1. 리그명 추출
                title_elem = driver.find_element(By.CSS_SELECTOR, "div.box h4, .league_title, h4")
                if title_elem:
                    txt = title_elem.text.strip()
                    if txt and txt not in ["일정", "대진표", "팀순위", "정보", "오즈통계", "베스트11"]:
                        match_data["league_name"] = txt.replace("라이브스코어", "").strip()
                
                if not match_data["league_name"]:
                    match_data["league_name"] = f"리그 ID {league_id}"

                # 2. active_round 추출 (동적 렌더링된 span 태그 전수 검사)
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

                # 3. 순위표 파싱
                standings_items = driver.find_elements(By.CSS_SELECTOR, "#standingList li.standis")
                parsed_standings = []
                
                for item in standings_items:
                    style_attr = item.get_attribute("style") or ""
                    tag_color = ""
                    if "--tagcolor:" in style_attr:
                        try:
                            tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                        except Exception:
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
                            "경기수": stat_slice[0] if len(stat_slice) > 0 else "",
                            "승": stat_slice[1] if len(stat_slice) > 1 else "",
                            "무": stat_slice[2] if len(stat_slice) > 2 else "",
                            "패": stat_slice[3] if len(stat_slice) > 3 else "",
                            "득실": stat_slice[4] if len(stat_slice) > 4 else "",
                            "승점": stat_slice[5] if len(stat_slice) > 5 else ""
                        })

                match_data["standings"] = parsed_standings
                print(f"  - [{match_data['league_name']}] 수집 성공 (Round: {match_data['active_round']})")

            except Exception as e:
                print(f"  - 파싱 중 에러 발생: {e}")

            # 파일 저장
            output_filename = f"match_details_league_{league_id}.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(match_data, f, ensure_ascii=False, indent=4)
            
            # 다음 리그로 넘어가기 전 3번 코드처럼 여유 대기
            time.sleep(1.0)

    finally:
        driver.quit()
        print("\n모든 순차 수집 완료.")

if __name__ == "__main__":
    crawl_leagues_v3_style()
