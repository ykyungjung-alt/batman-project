import json
import os
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
# 🧩 개별 독립 파싱 모듈
# ==========================================
def parse_league_name(soup, fallback_name):
    """리그명 추출 모듈"""
    try:
        title_elem = soup.select_one("div#title, div.title, .league_title, h4, strong, .league_name, h1, h2")
        if not title_elem:
            return fallback_name, "[모듈 에러] 리그명 타이틀 DOM 요소를 찾지 못했습니다."
        txt = title_elem.text.strip()
        if not txt:
            return fallback_name, "[조건 불일치] 리그명 타이틀의 텍스트 내용이 비어 있습니다."
        cleaned = txt.replace("라이브스코어", "").replace("시즌", "").replace("스코어맨", "").strip()
        return cleaned if cleaned else fallback_name, None
    except Exception as e:
        return fallback_name, f"[코드 에러] 리그명 파싱 중 예외 발생: {str(e)}"

def parse_active_round(soup, league_id, default_round, default_total):
    """활성 라운드 및 총 라운드 수 추출 모듈"""
    fallback_total = 46 if league_id == 39 else 38
    try:
        active_elem = soup.select_one("div.round span.current.on, div.round span.on, span.current.on, span.on, div.round > span[class*='on']")
        active_text = ""
        if active_elem:
            active_text = active_elem.get("round", "").strip()
            if not active_text.isdigit():
                active_text = active_elem.text.strip()
        if not active_text.isdigit():
            for span in soup.select("div.round span, span"):
                classes = span.get("class", [])
                if "on" in classes and span.text.strip().isdigit():
                    active_text = span.text.strip()
                    break
        if not active_text.isdigit():
            return default_round, fallback_total, "[모듈 에러] 활성 라운드 요소를 찾을 수 없습니다."
        all_rounds = soup.select("div.round span[round], div.round span")
        total_cnt = len([s for s in all_rounds if s.text.strip().isdigit()])
        if total_cnt == 0:
            total_cnt = fallback_total
        return f"{active_text}/{total_cnt}", total_cnt, None
    except Exception as e:
        return default_round, fallback_total, f"[코드 에러] 라운드 파싱 중 예외 발생: {str(e)}"

def parse_standing_legends(soup, default_legends):
    """하단 컬러 범례(#standingColor) 추출 모듈"""
    try:
        legend_items = soup.select("#standingColor span.explain, div#standingColor span.explain, .explain, .legend span")
        if not legend_items:
            fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
            return default_legends, fallback_map, "[모듈 에러] 하단 범례(#standingColor)를 찾을 수 없습니다."
        parsed_legends = []
        color_to_label = {}
        for lg in legend_items:
            color_i = lg.select_one("i, span[style*='background']")
            desc_span = lg.select_one("span:not([style*='background'])")
            bg_color = ""
            if color_i:
                bg_style = color_i.get("style", "")
                if "background-color:" in bg_style:
                    try:
                        bg_color = bg_style.split("background-color:")[1].split(";")[0].strip().upper()
                    except:
                        pass
            
            desc_text = desc_span.text.strip() if desc_span else lg.text.strip()
            if bg_color:
                color_to_label[bg_color] = desc_text
            parsed_legends.append({"color": bg_color, "description": desc_text})
        if not parsed_legends:
            fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
            return default_legends, fallback_map, "[조건 불일치] 범례 색상 추출 실패"
        return parsed_legends, color_to_label, None
    except Exception as e:
        fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
        return default_legends, fallback_map, f"[코드 에러] 범례 파싱 예외 발생: {str(e)}"

def parse_standings(soup, color_to_label, default_standings):
    """💡 1위 팀을 포함하여 모든 순위 및 통계 데이터를 누락 없이 정확히 파싱"""
    parsed_standings = []
    seen_teams = set()
    
    selectors_to_try = [
        'ul#standingList li.standis',
        'ul#standingList li',
        '#standingList li',
        '.standing_list li',
        '#standingPlates li',
        'li[class*="stand"]',
        '.rank-list li'
    ]
    
    standing_rows = []
    used_selector = None
    for sel in selectors_to_try:
        rows = soup.select(sel)
        if rows:
            standing_rows = rows
            used_selector = sel
            break
    
    if not standing_rows:
        all_lis = soup.select('#standingPlates li, ul li')
        sample_classes = list(set([li.get('class','') for li in all_lis[:10]]))
        return default_standings, f"[모듈 에러] 모든 선택자 실패. 시도한 마지막: {used_selector}, 발견된 샘플 클래스: {sample_classes}"
    
    for row in standing_rows:
        # 그룹 타이틀 및 헤더 행 제외
        row_classes = row.get("class", [])
        if isinstance(row_classes, str):
            row_classes = [row_classes]
        if any(cls in row_classes for cls in ["group", "title", "gray"]):
            continue

        style_attr = row.get("style", "")
        tag_color = ""
        if "--tagcolor:" in style_attr:
            try:
                tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
            except:
                pass
        if not tag_color and "background-color:" in style_attr:
            try:
                tag_color = style_attr.split("background-color:")[1].split(";")[0].strip().upper()
            except:
                pass

        rank_elem = row.select_one("span.rank, .rank, td:nth-child(1)")
        if not rank_elem:
            continue
        rank_val = "".join([c for c in rank_elem.get_text(strip=True) if c.isdigit()])
        if not rank_val:
            continue

        team_name_elem = row.select_one("span.team span.name, .team .name, .team-name, td:nth-child(2)")
        if team_name_elem:
            team_val = team_name_elem.get_text(strip=True)
        else:
            team_elem = row.select_one("span.team, .team")
            if team_elem:
                for img in team_elem.select("img"):
                    img.decompose()
                team_val = team_elem.get_text(strip=True)
            else:
                continue

        if not team_val or team_val in ["구단", "PTS", "순위", "승점", "Team"]:
            continue

        def extract_deep_text(elem):
            if not elem:
                return ""
            b_tag = elem.select_one("b")
            if b_tag:
                return b_tag.get_text(strip=True)
            inner_spans = elem.find_all("span")
            if inner_spans:
                for s in reversed(inner_spans):
                    txt = s.get_text(strip=True)
                    if txt:
                        return txt
            return elem.get_text(strip=True)

        # 💡 유효한 스탯 데이터를 순서대로 안전하게 추출
        raw_cells = row.find_all("span") + row.find_all("td")
        stat_values = []
        
        for cell in raw_cells:
            if cell.find_parent("span", class_="team") or cell.find_parent("span", class_="rank"):
                continue
            val = extract_deep_text(cell)
            if val and val != rank_val and val != team_val:
                if val.isdigit() or val == "-" or (val.startswith(('+','-')) and val[1:].isdigit()):
                    if not stat_values or stat_values[-1] != val:
                        stat_values.append(val)

        key_elem = row.select_one("span.key, .key")
        pts_val = "-"
        if key_elem:
            pts_val = extract_deep_text(key_elem)

        if len(stat_values) >= 5:
            p_val = stat_values[0]
            w_val = stat_values[1]
            d_val = stat_values[2]
            l_val = stat_values[3]
            gd_val = stat_values[4]
            if len(stat_values) >= 6 and pts_val == "-":
                pts_val = stat_values[5]
        else:
            p_val = stat_values[0] if len(stat_values) > 0 else "0"
            w_val = stat_values[1] if len(stat_values) > 1 else "0"
            d_val = stat_values[2] if len(stat_values) > 2 else "0"
            l_val = stat_values[3] if len(stat_values) > 3 else "0"
            gd_val = stat_values[4] if len(stat_values) > 4 else "0"

        if pts_val == "-" and len(stat_values) >= 6:
            pts_val = stat_values[5]

        if team_val not in seen_teams:
            seen_teams.add(team_val)
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
        parsed_standings.sort(key=lambda x: int(x['rank']) if x['rank'].isdigit() else 999)
        return parsed_standings, None
    return default_standings, f"[조건 불일치] {used_selector} 행 {len(standing_rows)}개 발견했으나 팀 데이터 추출 실패"

# ==========================================
# 🚀 메인 제어 및 드라이버 실행부
# ==========================================
def run_crawler_v4():
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    
    existing_leagues = {}
    if os.path.exists("match_details_v4.json"):
        try:
            with open("match_details_v4.json", "r", encoding="utf-8") as f:
                loaded_json = json.load(f)
                existing_leagues = loaded_json.get("leagues", {})
        except Exception as e:
            print(f"ℹ️ [불러오기 실패] 기존 JSON 파일 로드 실패: {e}")
            
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    target_leagues = [
        {"id": 34, "url": "https://football.scoreman123.com/league/34"},
        {"id": 39, "url": "https://football.scoreman123.com/league/39"},
        {"id": 40, "url": "https://football.scoreman123.com/league/40"},
        {"id": 36, "url": "https://football.scoreman123.com/league/36"},
        {"id": 37, "url": "https://football.scoreman123.com/league/37"},
        {"id": 31, "url": "https://football.scoreman123.com/league/31"},
        {"id": 33, "url": "https://football.scoreman123.com/league/33"},
        {"id": 8, "url": "https://football.scoreman123.com/league/8"},
        {"id": 9, "url": "https://football.scoreman123.com/league/9"},
        {"id": 11, "url": "https://football.scoreman123.com/league/11"},
        {"id": 12, "url": "https://football.scoreman123.com/league/12"},
        {"id": 25, "url": "https://football.scoreman123.com/league/25"},
        {"id": 15, "url": "https://football.scoreman123.com/league/15"},
        {"id": 1292, "url": "https://football.scoreman123.com/league/1292"},
        {"id": 35, "url": "https://football.scoreman123.com/league/35"},
        {"id": 90, "url": "https://football.scoreman123.com/league/90"},
        {"id": 83, "url": "https://football.scoreman123.com/league/83"},
        {"id": 23, "url": "https://football.scoreman123.com/league/23"},
        {"id": 29, "url": "https://football.scoreman123.com/league/29"},
        {"id": 16, "url": "https://football.scoreman123.com/league/16"},
        {"id": 22, "url": "https://football.scoreman123.com/league/22"},
        {"id": 27, "url": "https://football.scoreman123.com/league/27"},
        {"id": 103, "url": "https://football.scoreman123.com/league/103"},
        {"id": 113, "url": "https://football.scoreman123.com/league/113"},
        {"id": 2187, "url": "https://football.scoreman123.com/league/2187"}
    ]
    
    all_leagues_data = {
        "updated_at": now_kst,
        "leagues": {}
    }
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"❌ [코드 에러] 드라이버 초기화 실패: {e}")
        return
        
    try:
        for league in target_leagues:
            league_id = league["id"]
            url = league["url"]
            print(f"🔄 [수집 중] 리그 ID {league_id} ({url})")
            prev_data = existing_leagues.get(str(league_id), {})
            
            league_match_data = {
                "league_id": league_id,
                "league_name": prev_data.get("league_name", f"리그 ID {league_id}"),
                "league_name_error": None,
                "active_round": prev_data.get("active_round", f"1/{46 if league_id == 39 else 38}"),
                "active_round_error": None,
                "total_rounds": prev_data.get("total_rounds", 46 if league_id == 39 else 38),
                "standing_legends": prev_data.get("standing_legends", []),
                "standing_legends_error": None,
                "standings": prev_data.get("standings", []),
                "standings_error": None
            }
            try:
                driver.get(url)
            except Exception as net_err:
                league_match_data["standings_error"] = f"[주소 오류] URL 접속에 실패했습니다: {str(net_err)}"
                print(f"⚠️ {league_match_data['standings_error']}")
                all_leagues_data["leagues"][str(league_id)] = league_match_data
                continue

            try:
                WebDriverWait(driver, 20).until(
                    lambda d: d.find_element(By.CSS_SELECTOR, "#standingPlates").is_displayed()
                )
                time.sleep(2.5)
            except Exception as wait_err:
                league_match_data["standings_error"] = f"[대기 오류] 순위표 영역이 보이지 않음: {str(wait_err)}"

            try:
                total_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#standingType span[data-st-type='1']"))
                )
                driver.execute_script("arguments[0].click();", total_btn)
                time.sleep(1.5)
                result_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#standingHF span[data-st-hf='0']"))
                )
                driver.execute_script("arguments[0].click();", result_btn)
                time.sleep(2)
            except Exception as tab_err:
                print(f"  ⚠️ [조건 불일치] 필수 탭 제어 중 예외 발생: {tab_err} — 계속 진행")

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            with open(f"debug_html_{league_id}.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify()[:20000])

            name_res, name_err = parse_league_name(soup, league_match_data["league_name"])
            league_match_data["league_name"] = name_res
            league_match_data["league_name_error"] = name_err
            
            round_res, total_cnt, round_err = parse_active_round(
                soup, league_id, league_match_data["active_round"], league_match_data["total_rounds"]
            )
            league_match_data["active_round"] = round_res
            league_match_data["total_rounds"] = total_cnt
            league_match_data["active_round_error"] = round_err
            
            legends_res, color_map, legend_err = parse_standing_legends(
                soup, league_match_data["standing_legends"]
            )
            league_match_data["standing_legends"] = legends_res
            league_match_data["standing_legends_error"] = legend_err
            
            standings_res, standings_err = parse_standings(
                soup, color_map, league_match_data["standings"]
            )
            league_match_data["standings"] = standings_res
            league_match_data["standings_error"] = standings_err
            print(f"✅ 수집 완료: {league_match_data['league_name']} (순위 팀: {len(league_match_data['standings'])}개)")
            if standings_err:
                print(f"   → 경고: {standings_err}")
            all_leagues_data["leagues"][str(league_id)] = league_match_data
    except Exception as e:
        print(f"❌ [크롤링 실행 중 예외 발생]: {e}")
    finally:
        if driver:
            driver.quit()
            
    with open("match_details_v4.json", "w", encoding="utf-8") as f:
        json.dump(all_leagues_data, f, ensure_ascii=False, indent=4)
    print("🎉 match_details_v4.json 저장 완료")

if __name__ == "__main__":
    run_crawler_v4()
