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

    # 💡 올바른 풀 URL 주소로 수정 (세리에 A, 기타 리그 등)
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
            time.sleep(3.0)
            
            league_match_data = {
                "league_id": league_id,
                "league_name": "",
                "active_round": "1",
                "total_rounds": "38",
                "standing_legends": [],
                "standings": []
            }

            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#standingList")))

                # 1. 실제 리그명 추출
                try:
                    title_elem = driver.find_element(By.CSS_SELECTOR, "div#title, div.box h4, .league_title, h4")
                    txt = title_elem.text.strip()
                    if txt and txt not in ["일정", "대진표", "팀순위", "정보", "오즈통계", "베스트11"]:
                        league_match_data["league_name"] = txt.replace("라이브스코어", "").strip()
                except:
                    pass
                
                if not league_match_data["league_name"]:
                    league_match_data["league_name"] = f"리그 ID {league_id}"

                # 2. active_round 추출
                round_spans = driver.find_elements(By.CSS_SELECTOR, "div.round span")
                for span in round_spans:
                    outer_html = span.get_attribute("outerHTML")
                    if "current" in outer_html or "style class" in outer_html:
                        league_match_data["active_round"] = span.get_attribute("round").strip()
                        break
                
                if round_spans:
                    league_match_data["total_rounds"] = str(len(round_spans))

                # 3. 하단 색상 범례(standingColor) 수집
                color_to_label = {}
                parsed_legends = []
                try:
                    legend_elements = driver.find_elements(By.CSS_SELECTOR, "#standingColor span.explain")
                    for el in legend_elements:
                        try:
                            i_elem = el.find_element(By.TAG_NAME, "i")
                            bg_style = i_elem.get_attribute("style") or ""
                            bg_color = ""
                            if "background-color:" in bg_style:
                                bg_color = bg_style.split("background-color:")[1].split(";")[0].strip()
                            
                            desc_text = el.text.strip()
                            if bg_color and desc_text:
                                parsed_legends.append({"color": bg_color, "description": desc_text})
                                color_to_label[bg_color.upper()] = desc_text
                        except:
                            continue
                except:
                    pass

                league_match_data["standing_legends"] = parsed_legends

                # 4. 💡 순위표(Standings) 파싱 로직 (ul#standingList 하위 데이터 정밀 타격)
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

                    tag_label = color_to_label.get(tag_color, "일반")

                    # 순위(R) 추출
                    rank_val = ""
                    try:
                        rank_val = item.find_element(By.CSS_SELECTOR, "span.rank em, span.rank").text.strip()
                    except:
                        pass

                    # 구단명 추출
                    team_val = ""
                    try:
                        team_val = item.find_element(By.CSS_SELECTOR, "span.team span.name, span.name").text.strip()
                    except:
                        pass

                    # 행 내부의 모든 말단 텍스트 요소들을 순서대로 수집
                    all_elements = item.find_elements(By.XPATH, ".//*")
                    leaf_texts = []
                    for el in all_elements:
                        if not el.find_elements(By.XPATH, "./*"):
                            t = el.text.strip()
                            if t and t != rank_val and t != team_val:
                                leaf_texts.append(t)

                    if not team_val:
                        for t in leaf_texts:
                            if not t.isdigit() and len(t) > 1:
                                team_val = t
                                break

                    # 뒤에서부터 정확히 6개 스탯 슬라이싱 (경기, 승, 무, 패, 득실, 승점)
                    stat_candidates = [t for t in leaf_texts if t != rank_val and t != team_val]
                    if len(stat_candidates) >= 6:
                        stat_slice = stat_candidates[-6:]
                    else:
                        stat_slice = stat_candidates + [""] * (6 - len(stat_candidates))

                    if rank_val and team_val:
                        parsed_standings.append({
                            "순위": rank_val.replace("\n", "").strip(),
                            "구단": team_val,
                            "tag_color": tag_color,
                            "tag_label": tag_label,
                            "경기": stat_slice[0],
                            "승": stat_slice[1],
                            "무": stat_slice[2],
                            "패": stat_slice[3],
                            "득실": stat_slice[4],
                            "승점": stat_slice[5]
                        })

                league_match_data["standings"] = parsed_standings
                print(f"✅ [{league_match_data['league_name']}] 수집 성공 (팀 수: {len(parsed_standings)}개)")

            except Exception as page_err:
                print(f"⚠️ 리그 ID {league_id} 파싱 중 예외 발생: {page_err}")

            all_leagues_data["leagues"][str(league_id)] = league_match_data

        with open("match_details_v4.json", "w", encoding="utf-8") as f:
            json.dump(all_leagues_data, f, ensure_ascii=False, indent=4)
        print(f"\n🎉 [match_details_v4.json] 순위표 데이터 정밀 수집 및 저장 완료")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_crawler_v4()
