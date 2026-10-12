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
# 🧩 개별 독립 파싱 모듈 (1안 / 2안 복합 방어 체계)
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

def parse_standings_with_fallback(driver, soup, color_to_label, default_standings, league_id):
    """
    💡 1안(JS 동적 DOM 추출) 실패 시 2안(대체 셀렉터 및 화면 캡처 백업)으로 전환하는 방어형 파싱 모듈
    """
    parsed_standings = []
    seen_teams = set()

    try:
        # ==========================================
        # 🟢 [1안] JavaScript를 통한 브라우저 라이브 DOM 직접 추출
        # ==========================================
        js_rows_data = driver.execute_script("""
            const rows = document.querySelectorAll('li.standis');
            let results = [];
            rows.forEach(row => {
                let style = row.getAttribute('style') || '';
                let rankEl = row.querySelector('span.rank');
                let teamEl = row.querySelector('span.team span.name') || row.querySelector('span.team');
                
                let rank = rankEl ? rankEl.innerText.trim() : '';
                let team = '';
                if (teamEl) {
                    // 이미지 등 불필요한 자식 요소 제거 후 텍스트 추출
                    let clone = teamEl.cloneNode(true);
                    clone.querySelectorAll('img').forEach(img => img.remove());
                    team = clone.innerText.trim();
                }
                
                let spans = Array.from(row.querySelectorAll('span')).map(s => s.innerText.trim());
                results.push({
                    style: style,
                    rank: rank,
                    team: team,
                    spans: spans
                });
            });
            return results;
        """)

        if js_rows_data and len(js_rows_data) > 0:
            for item in js_rows_data:
                style_attr = item.get("style", "")
                tag_color = ""
                if "--tagcolor:" in style_attr:
                    try:
                        tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                    except:
                        pass

                rank_val = item.get("rank", "")
                team_val = item.get("team", "")
                if not rank_val.isdigit() or not team_val or team_val in ["구단", "PTS", "순위", "승점"]:
                    continue

                spans = item.get("spans", [])
                # 직접 자식 span들 매칭 (일반적으로 rank, team 뒤에 스탯 span들이 위치)
                if len(spans) >= 8:
                    # spans 구조: [rank, team, P, W, D, L, GD, PTS ...]
                    p_val = spans[2]
                    w_val = spans[3]
                    d_val = spans[4]
                    l_val = spans[5]
                    gd_val = spans[6]
                    pts_val = spans[7]

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

        # ==========================================
        # 🟡 [2안] 1안 실패 시: BeautifulSoup 대체 셀렉터 백업 + 스크린샷 캡처
        # ==========================================
        print(f"  ⚠️ [2안 전환] 리그 ID {league_id}: 1안 JS 추출 실패, 대체 셀렉터 및 캡처 백업 시도 중...")
        driver.save_screenshot(f"fallback_league_{league_id}.png")

        standing_rows = soup.select('#standingList li, ul.list li, li.standis')
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
            stat_values = [s.text.strip() for s in direct_spans[2:]]

            if len(stat_values) >= 6:
                p_val, w_val, d_val, l_val, gd_val, pts_val = stat_values[:6]
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

        return default_standings, "[모듈 에러] 1안(JS 추출) 및 2안(대체 셀렉터 캡처 백업) 모두에서 랭킹 데이터를 탐색하지 못했습니다."

    except Exception as e:
        driver.save_screenshot(f"error_standings_{league_id}.png")
        return default_standings, f"[코드 에러] 랭킹표 파싱 중 런타임 예외 발생: {str(e)}"


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
        {"id": 40, "url": "https://sports.scoreman123.com/tennisleague/40"}
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
                # 1. URL 접속 검증
                try:
                    driver.get(url)
                except Exception as net_err:
                    league_match_data["standings_error"] = f"[주소 오류] URL 접속에 실패했습니다: {str(net_err)}"
                    print(f"⚠️ {league_match_data['standings_error']}")
                    all_leagues_data["leagues"][str(league_id)] = league_match_data
                    continue

                # 2. 로딩 대기
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "li.standis"))
                    )
                except Exception:
                    league_match_data["standings_error"] = "[모듈 에러] 페이지 내 타겟 요소(li.standis)가 시간 내에 렌더링되지 않았습니다."

                # 3. 필수 탭 고정 (합계 + 결과) 및 검증
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
                    time.sleep(2) # 동적 렌더링 대기 시간 추가 확충
                except Exception as tab_err:
                    print(f"  ⚠️ [조건 불일치] 필수 탭 제어 중 예외 발생: {tab_err}")

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # 모듈별 독립 호출 및 에러 분류 기록
                name_res, name_err = parse_league_name(soup, league_id, league_match_data["league_name"])
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
                
                # 💡 1안/2안 복합 방어 체계가 적용된 랭킹표 파싱 호출
                standings_res, standings_err = parse_standings_with_fallback(
                    driver, soup, color_map, league_match_data["standings"], league_id
                )
                league_match_data["standings"] = standings_res
                league_match_data["standings_error"] = standings_err

                print(f"✅ 수집 완료: {league_match_data['league_name']} (순위 팀: {len(league_match_data['standings'])}개)")

            except Exception as e:
                err_msg = f"[코드 에러] 크롤링 실행 중 런타임 예외 발생: {str(e)}"
                print(f"⚠️ 리그 ID {league_id} 실패: {err_msg}")
                league_match_data["standings_error"] = err_msg
                driver.save_screenshot(f"error_league_{league_id}.png")

            all_leagues_
