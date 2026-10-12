import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 🧩 100% 독립된 파싱 모듈 영역
# ==========================================

def parse_league_name(soup, league_id, fallback_name):
    """리그명 추출 모듈 (실패 시 기존 값 유지)"""
    try:
        title_elem = soup.select_one("div#title, div.title, .league_title, h4, strong")
        if title_elem:
            txt = title_elem.text.strip()
            if txt:
                cleaned = txt.replace("라이브스코어", "").replace("시즌", "").replace("스코어맨", "").strip()
                if cleaned:
                    return cleaned
    except Exception as e:
        print(f"  ⚠️ [리그명 모듈 경고]: {e}")
    return fallback_name

def parse_active_round(soup, league_id, fallback_round, fallback_total):
    """활성 라운드 및 총 라운드 수 추출 모듈 (실패 시 기존 값 유지)"""
    default_total = 46 if league_id == 39 else 38
    try:
        active_elem = soup.select_one("div.round span.current.on, div.round span.on, span.current.on")
        active_text = ""
        
        if active_elem:
            active_text = active_elem.get("round", "").strip()
            if not active_text.isdigit():
                active_text = active_elem.text.strip()

        if not active_text.isdigit():
            for span in soup.select("div.round span"):
                if "current" in span.get("class", []) and span.text.strip().isdigit():
                    active_text = span.text.strip()
                    break

        all_rounds = soup.select("div.round span[round]")
        total_cnt = len(all_rounds) if all_rounds else default_total
        
        if active_text.isdigit():
            return f"{active_text}/{total_cnt}", total_cnt
    except Exception as e:
        print(f"  ⚠️ [라운드 모듈 경고]: {e}")
        
    return fallback_round, fallback_total

def parse_standing_legends(soup, fallback_legends):
    """하단 컬러 범례 추출 모듈 (실패 시 기존 값 유지)"""
    try:
        legend_items = soup.select("#standingColor span.explain, div#standingColor span.explain, .explain")
        parsed_legends = []
        color_to_label = {}
        
        for lg in legend_items:
            color_i = lg.select_one("i")
            desc_span = lg.select_one("span")
            if color_i:
                bg_style = color_i.get("style", "")
                bg_color = ""
                if "background-color:" in bg_style:
                    try:
                        bg_color = bg_style.split("background-color:")[1].split(";")[0].strip().upper()
                    except:
                        pass
                desc_text = desc_span.text.strip() if desc_span else lg.text.strip()
                if bg_color:
                    color_to_label[bg_color] = desc_text
                parsed_legends.append({"color": bg_color, "description": desc_text})
                
        if parsed_legends:
            return parsed_legends, color_to_label
    except Exception as e:
        print(f"  ⚠️ [범례 모듈 경고]: {e}")
        
    # 기존 범례를 바탕으로 color_map 재구축
    fallback_map = {item["color"]: item["description"] for item in fallback_legends if item.get("color")}
    return fallback_legends, fallback_map

def parse_standings(soup, color_to_label, fallback_standings):
    """랭킹표 및 컬러 꼬리표 매핑 모듈 (실패 시 기존 값 유지)"""
    parsed_standings = []
    seen_teams = set()
    
    try:
        # 테이블 구조 순회 파싱
        for tbl in soup.select('table'):
            for row in tbl.select('tr'):
                cells = [c.text.strip() for c in row.select('td, th') if c.text.strip()]
                
                if len(cells) >= 8 and cells[0].isdigit():
                    rank_val = cells[0]
                    rank_int = int(rank_val)
                    
                    if 1 <= rank_int <= 25:
                        team_val = cells[1]
                        if team_val in ["구단", "PTS", "순위", "승점"] or any(k in team_val for k in ["승점", "득실"]):
                            continue
                        
                        p_val = cells[2]
                        w_val = cells[3]
                        d_val = cells[4]
                        l_val = cells[5]
                        gd_val = cells[6]
                        pts_val = cells[7]
                        
                        if p_val.isdigit() and pts_val.isdigit():
                            if team_val not in seen_teams:
                                seen_teams.add(team_val)
                                
                                style_attr = row.get("style", "")
                                tag_color = ""
                                if "--tagcolor:" in style_attr:
                                    try:
                                        tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                                    except:
                                        pass
                                
                                tag_label = color_to_label.get(tag_color, "일반")

                                parsed_standings.append({
                                    "rank": rank_val,
                                    "team": team_val,
                                    "tag_color": tag_color,
                                    "tag_label": tag_label,
                                    "경기수": p_val,
                                    "승": w_val,
                                    "무": d_val,
                                    "패": l_val,
                                    "득실": gd_val,
                                    "승점": pts_val
                                })
            if parsed_standings:
                break

        if parsed_standings:
            parsed_standings.sort(key=lambda x: int(x['rank']))
            return parsed_standings
    except Exception as e:
        print(f"  ⚠️ [랭킹표 모듈 경고]: {e}")
        
    return fallback_standings


# ==========================================
# 🚀 메인 컨트롤러 영역
# ==========================================
def run_crawler_v4():
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    # 💡 실제 스코어맨 도메인 URL 정확히 반영
    target_leagues = [
        {"id": 34, "url": "https://football.scoreman123.com/league/34"},
        {"id": 39, "url": "https://football.scoreman123.com/league/39"},
        {"id": 40, "url": "https://football.scoreman123.com/league/40"}
    ]

    all_leagues_data = {
        "updated_at": now_kst,
        "leagues": {}
    }

    driver = None
    try:
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception:
            driver = webdriver.Chrome(options=options)

        for league in target_leagues:
            league_id = league["id"]
            url = league["url"]
            print(f"🔄 [수집 중] 리그 ID {league_id} ({url})")

            # 초기 데이터 구조 (실패 시 안전하게 유지될 기본값)
            league_match_data = {
                "league_id": league_id,
                "league_name": f"리그 ID {league_id}",
                "active_round": f"1/{46 if league_id == 39 else 38}",
                "total_rounds": 46 if league_id == 39 else 38,
                "standing_legends": [],
                "standings": []
            }

            try:
                driver.get(url)
                
                # 페이지 로딩 대기
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table, div.round"))
                )
                time.sleep(3)

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # 💡 각 모듈을 독립적으로 호출하여 기존 데이터를 안전하게 갱신
                league_match_data["league_name"] = parse_league_name(
                    soup, league_id, league_match_data["league_name"]
                )
                
                active_str, total_cnt = parse_active_round(
                    soup, league_id, league_match_data["active_round"], league_match_data["total_rounds"]
                )
                league_match_data["active_round"] = active_str
                league_match_data["total_rounds"] = total_cnt
                
                legends, color_map = parse_standing_legends(
                    soup, league_match_data["standing_legends"]
                )
                league_match_data["standing_legends"] = legends
                
                league_match_data["standings"] = parse_standings(
                    soup, color_map, league_match_data["standings"]
                )

                print(f"✅ 수집 성공: {league_match_data['league_name']} (라운드: {league_match_data['active_round']}, 범례: {len(legends)}개, 순위 팀: {len(league_match_data['standings'])}개)")

            except Exception as e:
                print(f"⚠️ 리그 ID {league_id} 크롤링 중 예외 발생: {e}")

            all_leagues_data["leagues"][str(league_id)] = league_match_data

    finally:
        if driver:
            driver.quit()

    with open("match_details_v4.json", "w", encoding="utf-8") as f:
        json.dump(all_leagues_data, f, ensure_ascii=False, indent=4)
    print("🎉 match_details_v4.json 저장 완료")

if __name__ == "__main__":
    run_crawler_v4()
