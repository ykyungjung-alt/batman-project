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
# 🧩 개별 독립 파싱 모듈 (에러 체계 및 정밀 구조 반영)
# ==========================================

def parse_league_name(soup, league_id, fallback_name):
    """리그명 추출 모듈"""
    try:
        title_elem = soup.select_one("div#title, div.title, .league_title, h4, strong")
        if not title_elem:
            return fallback_name, "[모듈 에러] 리그명 타이틀 DOM 요소를 찾지 못했습니다."
        
        txt = title_elem.text.strip()
        if not txt:
            return fallback_name, "[조건 불일치] 리그명 타이틀의 텍스트 내용이 비어 있습니다."
            
        cleaned = txt.replace("라이브스코어", "").replace("시즌", "").replace("스코어맨", "").strip()
        if not cleaned:
            return fallback_name, "[조건 불일치] 정제된 리그명 텍스트가 유효하지 않습니다."
            
        return cleaned, None
    except Exception as e:
        return fallback_name, f"[코드 에러] 리그명 파싱 중 런타임 예외 발생: {str(e)}"

def parse_active_round(soup, league_id, default_round, default_total):
    """활성 라운드 및 총 라운드 수 정밀 추출 모듈 (미탐색 시 에러 확정)"""
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
            return default_round, fallback_total, "[모듈 에러] 활성 라운드(active_round) 요소를 전혀 탐색할 수 없거나 숫자가 아닙니다."

        all_rounds = soup.select("div.round span[round], div.round span")
        total_cnt = len([s for s in all_rounds if s.text.strip().isdigit()]) 
        if total_cnt == 0:
            total_cnt = fallback_total
            
        return f"{active_text}/{total_cnt}", total_cnt, None
    except Exception as e:
        return default_round, fallback_total, f"[코드 에러] 라운드 파싱 중 런타임 예외 발생: {str(e)}"

def parse_standing_legends(soup, default_legends):
    """하단 컬러 범례 추출 모듈"""
    try:
        legend_items = soup.select("#standingColor span.explain, div#standingColor span.explain, .explain")
        if not legend_items:
            fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
            return default_legends, fallback_map, "[모듈 에러] 하단 범례(#standingColor) 요소를 탐색할 수 없습니다."

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
                
        if not parsed_legends:
            fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
            return default_legends, fallback_map, "[조건 불일치] 범례 아이템은 존재하나 색상 속성(background-color) 추출에 실패했습니다."
            
        return parsed_legends, color_to_label, None
    except Exception as e:
        fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
        return default_legends, fallback_map, f"[코드 에러] 범례 파싱 중 런타임 예외 발생: {str(e)}"

def parse_standings(soup, color_to_label, default_standings):
    """💡 ul#standingList li.standis 구조와 순차적 스탯 매핑을 적용한 정밀 파싱 모듈"""
    parsed_standings = []
    seen_teams = set()
    
    try:
        standing_rows = soup.select('ul#standingList li.standis, li.standis')
        if not standing_rows:
            return default_standings, "[모듈 에러] 페이지 내 'ul#standingList li.standis' 요소를 전혀 탐색할 수 없습니다."

        for row in standing_rows:
            # 1. 태그 컬러 (--tagcolor) 추출
            style_attr = row.get("style", "")
            tag_color = ""
            if "--tagcolor:" in style_attr:
                try:
                    tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                except:
                    pass

            # 2. 순위(Rank) 추출
            rank_elem = row.select_one("span.rank")
            if not rank_elem:
                continue
            rank_val = rank_elem.get_text(strip=True)
            if not rank_val.isdigit():
                continue

            # 3. 팀명(Team) 추출
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

            # 4. 스탯 항목 순서대로 매핑 ([0]:경기수, [1]:승, [2]:무, [3]:패, [4]:득실, [5]:승점)
            direct_spans
