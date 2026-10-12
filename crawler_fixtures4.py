import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def crawl_match_details_with_browser():
    # 💡 백그라운드 브라우저 모드 설정 (headless를 원치 않으시면 options.headless = False로 변경 가능)
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 화면 창을 띄우지 않고 백그라운드 실행
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # 웹드라이버 실행
    driver = webdriver.Chrome(options=chrome_options)
    
    target_league_ids = [34, 39, 40]

    try:
        for league_id in target_league_ids:
            target_url = f"https://football.scoreman123.com/league/{league_id}"
            print(f"\n--- 브라우저 탐색 시작: 리그 ID {league_id} ---")
            
            # 브라우저로 실제 페이지 접속
            driver.get(target_url)
            
            # 페이지가 렌더링될 때까지 충분히 대기 (동적 로딩 대응)
            time.sleep(3)

            match_data = {
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "league_id": league_id,
                "league_name": "",
                "active_round": "",
                "total_rounds": "",
                "standings": [],
                "standing_legends": []
            }

            try:
                # 1. 리그명 추출
                try:
                    title_elem = driver.find_element(By.CSS_SELECTOR, "div.box h4, .league_title, h4")
                    txt = title_elem.text.strip()
                    if txt and txt not in ["일정", "대진표", "팀순위", "정보", "오즈통계", "베스트11"]:
                        match_data["league_name"] = txt.replace("라이브스코어", "").strip()
                except Exception:
                    pass
                
                if not match_data["league_name"]:
                    match_data["league_name"] = f"리그 ID {league_id}"

                # 2. active_round 추출 (div.round 안의 span 태그들 중 style class 요소를 가진 것 탐색)
                active_text = "1"
                round_spans = driver.find_elements(By.CSS_SELECTOR, "div.round span")
                
                for span in round_spans:
                    # 각 span의 HTML 원본 소스를 가져와서 "current" 또는 "style class" 포함 여부 확인
                    outer_html = span.get_attribute("outerHTML")
                    if "current" in outer_html or "style class" in outer_html:
                        active_text = span.get_attribute("round").strip()
                        break
                
                total_cnt = len(round_spans) if round_spans else 38
                match_data["active_round"] = active_text
                match_data["total_rounds"] = str(total_cnt)

                # 3. 순위표(Standings) 파싱
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
                    except:
                        rank_val = ""

                    try:
                        team_val = item.find_element(By.CSS_SELECTOR, ".team .name, span.name").text.strip()
                    except:
                        team_val = ""

                    spans = item.find_elements(By.TAG_NAME, "span")
                    all_spans = [s.text.strip() for s in spans if s.text.strip()]

                    if rank_val and team_val:
                        stat_slice = all_spans[-6:] if len(all_spans) >= 6 else []
                        parsed_standings.append({
                            "rank": rank_val.replace("\n", "").strip(),
                            "team": team_val,
                            "tag_color": tag_color,
                            "tag_label": "일반",
                            "경기수": stat_slice[0] if len(stat_slice) > 0 else "",
                            "승": stat_slice[1] if len(stat_slice) > 1 else "",
                            "무": stat_slice[2] if len(stat_slice) > 2 else "",
                            "패": stat_slice[3] if len(stat_slice) > 3 else "",
                            "득실": stat_slice[4] if len(stat_slice) > 4 else "",
                            "승점": stat_slice[5] if len(stat_slice) > 5 else ""
                        })

                match_data["standings"] = parsed_standings
                print(f"[{match_data['league_name']}] 수집 성공 (Round: {match_data['active_round']} / Total: {match_data['total_rounds']})")

            except Exception as parse_err:
                print(f"데이터 파싱 중 오류 발생: {parse_err}")

            # 파일로 개별 저장
            output_filename = f"match_details_league_{league_id}.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(match_data, f, ensure_ascii=False, indent=4)
            print(f"[{output_filename}] 저장 완료.")

            # 다음 페이지로 넘어갈 때 자연스러운 브라우저 탐색 간격 유지
            time.sleep(2)

    finally:
        # 작업 완료 후 브라우저 세션 종료
        driver.quit()
        print("\n모든 브라우저 탐색 작업이 종료되었습니다.")

if __name__ == "__main__":
    crawl_match_details_with_browser()
