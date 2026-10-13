import json
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 🧩 템플릿 구조 기반 정밀 파싱 모듈
# ==========================================

def parse_league_name(driver, fallback_name):
    """리그명 추출 모듈"""
    try:
        title_elem = driver.find_element(By.CSS_SELECTOR, "div#title, div.title, .league_title, h4, strong, .league_name")
        txt = title_elem.text.strip()
        if not txt:
            return fallback_name, "[조건 불일치] 리그명 타이틀의 텍스트 내용이 비어 있습니다."
        cleaned = txt.replace("라이브스코어", "").replace("시즌", "").replace("스코어맨", "").strip()
        return cleaned if cleaned else fallback_name, None
    except Exception as e:
        return fallback_name, f"[모듈 에러] 리그명 타이틀 DOM 요소를 찾지 못했습니다: {str(e)}"

def parse_active_round(driver, league_id, default_round, default_total):
    """활성 라운드 및 총 라운드 수 추출 모듈"""
    fallback_total = 46 if league_id == 39 else 38
    try:
        active_elem = driver.find_element(By.CSS_SELECTOR, "div.round span.current.on, div.round span.on, span.current.on, span.on")
        active_text = active_elem.get_attribute("round") or active_elem.text.strip()
        if not active_text.isdigit():
            spans = driver.find_elements(By.CSS_SELECTOR, "div.round span, span")
            for s in spans:
                if "on" in (s.get_attribute("class") or "") and s.text.strip().isdigit():
                    active_text = s.text.strip()
                    break
        if not active_text.isdigit():
            return default_round, fallback_total, "[모듈 에러] 활성 라운드 요소를 찾을 수 없습니다."
        
        all_rounds = driver.find_elements(By.CSS_SELECTOR, "div.round span[round], div.round span")
        total_cnt = len([s for s in all_rounds if s.text.strip().isdigit()])
        if total_cnt == 0:
            total_cnt = fallback_total
        return f"{active_text}/{total_cnt}", total_cnt, None
    except Exception as e:
        return default_round, fallback_total, f"[모듈 에러] 라운드 파싱 예외: {str(e)}"

def parse_standing_legends(driver, default_legends):
    """💡 tplStandingsBlock 템플릿 구조에 맞춘 하단 컬러 범례 추출 모듈"""
    try:
        legend_items = driver.find_elements(By.CSS_SELECTOR, "#standingColor span.explain, div#standingColor span.explain")
        if not legend_items:
            legend_items = driver.find_elements(By.CSS_SELECTOR, ".explain")

        if not legend_items:
            fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
            return default_legends, fallback_map, "[모듈 에러] 하단 범례(#standingColor) 요소를 찾지 못했습니다."

        parsed_legends = []
        color_to_label = {}
        for lg in legend_items:
            try:
                color_i = lg.find_element(By.TAG_NAME, "i")
                bg_style = color_i.get_attribute("style") or ""
                bg_color = ""
                if "background-color:" in bg_style:
                    bg_color = bg_style.split("background-color:")[1].split(";")[0].strip().upper()
                
                desc_span = lg.find_element(By.TAG_NAME, "span")
                desc_text = desc_span.text.strip() if desc_span else lg.text.strip()
                if bg_color:
                    color_to_label[bg_color] = desc_text
                parsed_legends.append({"color": bg_color, "description": desc_text})
            except:
                continue

        if not parsed_legends:
            fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
            return default_legends, fallback_map, "[조건 불일치] 범례 색상 추출 실패"
        return parsed_legends, color_to_label, None
    except Exception as e:
        fallback_map = {item["color"]: item["description"] for item in default_legends if item.get("color")}
        return default_legends, fallback_map, f"[코드 에러] 범례 파싱 예외: {str(e)}"

def parse_standings(driver, color_to_label, default_standings):
    """💡 tplStandingsItem 원본 템플릿 구조(R, 구단, P, W, D, L, GD, PTS) 1대1 매칭 파싱 모듈"""
    parsed_standings = []
    seen_teams = set()
    
    try:
        # li.standis 항목들이 DOM에 렌더링될 때까지 대기
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul#standingList li.standis"))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, "ul#standingList li.standis")
        if not rows:
            return default_standings, "[모듈 에러] 'ul#standingList li.standis' 요소를 찾을 수 없습니다."

        for row in rows:
            style_attr = row.get_attribute("style") or ""
            tag_color = ""
            if "--tagcolor:" in style_attr:
                try:
                    tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                except:
                    pass

            try:
                # 1. 순위 (R) -> span.rank <em>
                rank_elem = row.find_element(By.CSS_SELECTOR, "span.rank")
                rank_val = "".join([c for c in rank_elem.text.strip() if c.isdigit()])
                if not rank_val:
                    continue

                # 2. 구단명 (Team Name) -> span.team span.name
                team_elem = row.find_element(By.CSS_SELECTOR, "span.team span.name")
                team_val = team_elem.text.strip()
            except:
                continue

            if not team_val or team_val in ["구단", "PTS", "순위", "승점"]:
                continue

            # 3. 템플릿 직계 자식 span 순서 매칭
            # [0]: span.rank
            # [1]: span.team
            # [2]: <span>{$sum}</span> (경기수 P)
            # [3]: <span><span>{$win}</span></span> (승 W)
            # [4]: <span><span>{$draw}</span></span> (무 D)
            # [5]: <span><span>{$lose}</span></span> (패 L)
            # [6]: <span><span>{$goalDiff}</span></span> (득실 GD)
            # [7]: <span class="key blue"><b>{$point}</b></span> (승점 PTS)
            child_spans = row.find_elements(By.XPATH, "./span")
            
            def get_text_safe(elem):
                if not elem:
                    return ""
                try:
                    b_tag = elem.find_element(By.TAG_NAME, "b")
                    if b_tag:
                        return b_tag.text.strip()
                except:
                    pass
                try:
                    inner = elem.find_element(By.TAG_NAME, "span")
                    if inner:
                        return inner.text.strip()
                except:
                    pass
                return elem.text.strip()

            if len(child_spans) >= 8:
                p_val = get_text_safe(child_spans[2])   # P
                w_val = get_text_safe(child_spans[3])   # W
                d_val = get_text_safe(child_spans[4])   # D
                l_val = get_text_safe(child_spans[5])   # L
                gd_val = get_text_safe(child_spans[6])  # GD
                pts_val = get_text_safe(child_spans[7]) # PTS

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

        return default_standings, "[조건 불일치] li.standis 행은 존재하나 템플릿 컬럼 매칭에 실패했습니다."
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
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#standingPlates"))
                )
            except Exception:
                league_match_data["standings_error"] = "[모듈 에러] 페이지 내 순위표 영역(#standingPlates)이 시간 내에 렌더링되지 않았습니다."

            try:
                total_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#standingType span[data-st-type='1']"))
                )
                driver.execute_script("arguments[0].click();", total_btn)
                time.sleep(1)

                result_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#standingHF span[data-st-hf='0']"))
                )
                driver.execute_script("arguments[0].click();", result_btn)
                time.sleep(1.5)
            except Exception as tab_err:
                print(f"  ⚠️ [조건 불일치] 필수 탭 제어 중 예외 발생: {tab_err}")

            # 모듈 호출
            name_res, name_err = parse_league_name(driver, league_match_data["league_name"])
            league_match_data["league_name"] = name_res
            league_match_data["league_name_error"] = name_err
            
            round_res, total_cnt, round_err = parse_active_round(
                driver, league_id, league_match_data["active_round"], league_match_data["total_rounds"]
            )
            league_match_data["active_round"] = round_res
            league_match_data["total_rounds"] = total_cnt
            league_match_data["active_round_error"] = round_err
            
            legends_res, color_map, legend_err = parse_standing_legends(
                driver, league_match_data["standing_legends"]
            )
            league_match_data["standing_legends"] = legends_res
            league_match_data["standing_legends_error"] = legend_err
            
            standings_res, standings_err = parse_standings(
                driver, color_map, league_match_data["standings"]
            )
            league_match_data["standings"] = standings_res
            league_match_data["standings_error"] = standings_err

            print(f"✅ 수집 완료: {league_match_data['league_name']} (순위 팀: {len(league_match_data['standings'])}개)")

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
