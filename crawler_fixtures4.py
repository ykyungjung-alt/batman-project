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
# 🧩 1단계: 개별 독립 파싱 모듈 (실패 원인 명시 기능 포함)
# ==========================================

def parse_league_name(soup, league_id, fallback_name):
    """리그명 추출 모듈"""
    try:
        title_elem = soup.select_one("div#title, div.title, .league_title, h4, strong")
        if title_elem:
            txt = title_elem.text.strip()
            if txt:
                cleaned = txt.replace("라이브스코어", "").replace("시즌", "").replace("스코어맨", "").strip()
                if cleaned:
                    return cleaned, None
        return fallback_name, "리그명 타이틀 요소를 찾지 못했거나 텍스트가 비어있습니다."
    except Exception as e:
        return fallback_name, f"리그명 파싱 중 예외 발생: {str(e)}"

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

        all_rounds = soup.select("div.round span[round], div.round span")
        total_cnt = len([s for s in all_rounds if s.text.strip().isdigit()]) 
        if total_cnt == 0:
            total_cnt = fallback_total
        
        if active_text.isdigit():
            return f"{active_text}/{total_cnt}", total_cnt, None
            
        return default_round, fallback_total, "활성 라운드 숫자(digit)를 감지하지 못했습니다."
    except Exception as e:
        return default_round, fallback_total, f"라운드 파싱 중 예외 발생: {str(e)}"

def parse_standing_legends(soup, default_legends):
    """하단 컬러 범례 추출 모듈"""
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
            fallback_map = {item["color"]: item["description"] for item in parsed_legends if item.get("color")}
            return parsed_legends, fallback_map, None
            
        return default_legends, {item["color"]: item["description"] for item in default_legends if item.get("color")}, "하단 범례(#standingColor) 요소를 찾지 못했습니다."
    except Exception as e:
        fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
        return default_legends, fallback_map, f"범례 파싱 중 예외 발생: {str(e)}"

def parse_standings(soup, color_to_label, default_standings):
    """💡 랭킹표 및 컬러 꼬리표 매핑 모듈 (li.standis 정밀 파싱)"""
    parsed_standings = []
    seen_teams = set()
    
    try:
        standing_rows = soup.select('li.standis')
        if not standing_rows:
            return default_standings, "페이지 내 'li.standis' 랭킹 리스트 요소를 찾지 못했습니다. (탭 세팅 누락 또는 DOM 구조 변경 의심)"

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
            rank_val = rank_elem.text.strip()
            if not rank_val.isdigit():
                continue

            team_name_elem = row.select_one("span.team span.name")
            if team_name_elem:
                team_val = team_name_elem.text.strip()
            else:
                team_elem = row.select_one("span.team")
                if team_elem:
                    for img in team_elem.select("img"):
                        img.decompose()
                    team_val = team_elem.text.strip()
                else:
                    continue

            if not team_val or team_val in ["구단", "PTS", "순위", "승점"]:
                continue

            direct_spans = [s for s in row.find_all("span", recursive=False)]
            stat_values = []
            for s in direct_spans[2:]:
                stat_values.append(s.text.strip())

            if len(stat_values) >= 6:
                p_val = stat_values[0]
                w_val = stat_values[1]
                d_val = stat_values[2]
                l_val = stat_values[3]
                gd_val = stat_values[4]
                pts_val = stat_values[5]

                if p_val.isdigit() and pts_val.isdigit():
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
            parsed_standings.sort(key=lambda x: int(x['rank']))
            return parsed_standings, None
            
        return default_standings, "li.standis 행은 존재하나 유효한 순위/스탯 데이터 매칭에 실패했습니다."
    except Exception as e:
        return default_standings, f"랭킹표 파싱 중 예외 발생: {str(e)}"


# ==========================================
# 🚀 2단계: 메인 제어 및 드라이버 실행부
# ==========================================
def run_crawler_v4():
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    
    existing_leagues = {}
    if os.path.exists("match_details_v4.json"):
        try:
            with open("match_details_v4.json", "r", encoding="utf-8") as f:
                loaded_json = json.load(f)
                existing_leagues = loaded_json.get
