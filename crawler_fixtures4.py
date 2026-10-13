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
# 🧩 개별 독립 파싱 모듈 (안전한 정적/동적 결합)
# ==========================================

def parse_league_name(soup, fallback_name):
    """리그명 추출 모듈"""
    try:
        title_elem = soup.select_one("div#title, div.title, .league_title, h4, strong, .league_name")
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
        active_elem = soup.select_one("div.round span.current.on, div.round span.on, span.current.on, span.on")
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
        legend_items = soup.select("#standingColor span.explain, div#standingColor span.explain, .explain")
        if not legend_items:
            fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
            return default_legends, fallback_map, "[모듈 에러] 하단 범례(#standingColor)를 찾을 수 없습니다."

        parsed_legends = []
        color_to_label = {}
        for lg in legend_items:
            color_i = lg.select_one("i")
            desc_span = lg.select_one("span")
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
    """💡 tplStandingsItem 템플릿 구조 기반 순위표 정밀 파싱 모듈 (중첩 span/b 태그 대응)"""
    parsed_standings = []
    seen_teams = set()
    
    try:
        standing_rows = soup.select('ul#standingList li.standis')
        if not standing_rows:
            return default_standings, "[모듈 에러] 페이지 내 'ul#standingList li.standis' 요소를 전혀 탐색할 수 없습니다."

        for row in standing_rows:
            style_attr = row.get("style", "")
            tag_color = ""
            if "--tagcolor:" in style_attr:
                try:
                    tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                except:
                    pass

            rank_elem = row.select_one("span.rank")
            if not rank_elem:
                continue
            rank_val = "".join([c for c in rank_elem.get_text(strip=True) if c.isdigit()])
            if not rank_val:
                continue

            team_name_elem = row.select_one("span.team span.name")
            if team_name_elem:
                team_val = team_name_elem.get_text(strip=True)
            else:
                team_elem = row.select_one("span.team")
                if team_elem:
                    for img in team_elem.select("img"):
                        img.decompose()
                    team_val = team_elem.get_text(strip=True)
                else:
                    continue

            if not team_val or team_val in ["구단", "PTS", "순위", "승점"]:
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

            child_spans = row.find_all("span", recursive=False)
            stat_values = []
            
            for span in child_spans[2:]:
                val = extract_deep_text(span)
                if val:
                    stat_values.append(val)

            if len(stat_values) < 6:
                stat_values = []
                for s in row.select("span"):
                    if s.find_parent("span", class_="team") or s.find_parent("span", class_="rank"):
                        continue
                    if s.get("class") and ("rank" in s.get("class") or "team" in s.get("class")):
                        continue
                    val = extract_deep_text(s)
                    if val and val != rank_val and val != team_val and val not in stat_values:
                        stat_values.append(val)

            if len(stat_values) >= 6:
                p_val = stat_values[0]
                w_val = stat_values[1]
                d_val = stat_values[2]
                l_val = stat_values[3]
                gd_val = stat_values[4]
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

        return default_standings, "[조건 불일치] li.standis 행은 존재하나 컬럼 매칭에 실패했습니다."
    except Exception as e:
        return default_standings, f"[코드 에러] 순위표 파싱 예외 발생: {str(e)}"


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
        {"id": 34, "url": "https://github.com/copilot6league/34"},
        {"id": 39, "url": "https://github.com/copilot6league/39"},
        {"id": 40, "url": "https://github.com/copilot6league/40"}
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
                league_match_data["standings_error"] = f"[주소 오류] URL
