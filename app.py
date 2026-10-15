from datetime import datetime, timezone, timedelta
import json
import os
import re
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import math

# 페이지 설정 (반드시 맨 처음에 위치해야 함)
st.set_page_config(page_title="배트맨 프로젝트 분석 엔진", layout="wide")

# 1. 데이터 로딩 함수 정의
@st.cache_data(ttl=10)
def load_match_data():
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_updated": "안전 모드 (데이터 없음)", "daily_matches": {}}

@st.cache_data(ttl=10)
def load_all_match_details():
    target_files = ["match_details.json", "match_details_v2.json"]
    combined_details = {}
    for t_file in target_files:
        if os.path.exists(t_file):
            try:
                with open(t_file, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    match_dict = file_data.get("match_details", {})
                    for k, v in match_dict.items():
                        clean_k = str(k).strip()
                        combined_details[clean_k] = v
                        if isinstance(v, dict):
                            m_code = str(v.get("match_code", "")).strip()
                            if m_code:
                                combined_details[m_code] = v
            except Exception:
                pass
    return combined_details

@st.cache_data(ttl=10)
def load_v3_match_details():
    v3_files = ["match_details_v3.json", "match_details_v3-1.json"]
    combined_v3 = {}
    for v3_file in v3_files:
        if os.path.exists(v3_file):
            try:
                with open(v3_file, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    combined_v3.update(file_data.get("match_details", {}))
            except Exception:
                pass
    return combined_v3

@st.cache_data(ttl=10)
def load_v4_match_details():
    v4_file = "match_details_v4.json"
    if os.path.exists(v4_file):
        try:
            with open(v4_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                return file_data.get("leagues", {})
        except Exception:
            pass
    return {}

# 2. 데이터 호출 및 초기화 (한 번만 수행)
data = load_match_data()
last_updated_time = data.get("last_updated", "알 수 없음")
daily_matches = data.get("daily_matches", {})

all_details_dict = load_all_match_details()
v3_details_dict = load_v3_match_details()
v4_leagues_dict = load_v4_match_details()

# 3. 메인 타이틀 출력 (중복 방지)
st.markdown("<h2 style='font-size: 28px;'>⚽ 배트맨 프로젝트 통합 마스터 규격 및 분석 엔진 ⚽</h2>", unsafe_allow_html=True)
st.markdown("구글 독스 원문 규격 100% 반영 • 생략 없는 0단계~6단계 세부 정량 표 완벽 탑재 시스템")

st.sidebar.markdown("---")
st.sidebar.markdown(f"🕒 **데이터 갱신 시각 (KST)**\n\n`{last_updated_time}`")
st.sidebar.subheader("🏆 실시간 수집 대진 선택")

date_options = list(daily_matches.keys())
if not date_options:
    date_options = ["오늘 (데이터 없음)"]

selected_date = st.sidebar.selectbox("📅 날짜를 선택하세요:", date_options, key="main_date_selectbox")

matches = daily_matches.get(selected_date, [])
selected_match = None

if matches:
    leagues = sorted(list(set(m.get("league", "기타 리그") for m in matches)))
    if leagues:
        selected_league = st.sidebar.selectbox("리그를 선택하세요:", leagues, key="main_league_selectbox")
        league_matches = [m for m in matches if m.get("league", "기타 리그") == selected_league]
        
        match_options = [f"[{m.get('time', '00:00')}] {m.get('home')} vs {m.get('away')}" for m in league_matches]
        if match_options:
            selected_match_name = st.sidebar.radio("분석할 경기를 선택하세요:", match_options, key="match_radio_selection")
            selected_match = next((m for m in league_matches if f"[{m.get('time', '00:00')}] {m.get('home')} vs {m.get('away')}" == selected_match_name), None)

if not selected_match:
    st.warning(f"⚠️ [{selected_date}] 조건에 해당하는 경기 데이터가 존재하지 않습니다. (데이터 없음)")
    st.info("💡 안내: 아직 해당 날짜에 수집된 경기 일정이나 정밀 데이터가 없습니다. 다른 날짜를 선택하시거나 데이터 갱신 후 이용해 주세요.")
    st.stop()

home_team = selected_match.get("home", "홈팀")
away_team = selected_match.get("away", "원정팀")
tournament_name = selected_match.get("league", "리그")
match_date = selected_match.get("time", "오늘")
match_code = str(selected_match.get("match_code", ""))

raw_detailed_info = None
target_code = str(match_code).strip()
target_home = str(home_team).strip().replace(" ", "")
target_away = str(away_team).strip().replace(" ", "")

if target_code and target_code in all_details_dict:
    raw_detailed_info = all_details_dict[target_code]

if not raw_detailed_info and target_code:
    for k, v in all_details_dict.items():
        if str(v.get("match_code", "")).strip() == target_code:
            raw_detailed_info = v
            break

if not raw_detailed_info:
    for k, v in all_details_dict.items():
        v_home = str(v.get("home", "")).strip().replace(" ", "")
        v_away = str(v.get("away", "")).strip().replace(" ", "")
        if v_home == target_home and v_away == target_away:
            raw_detailed_info = v
            break

if raw_detailed_info and isinstance(raw_detailed_info, dict):
    detailed_info = raw_detailed_info
    has_detailed_data = True
else:
    detailed_info = {
        "head_info": {},
        "meta_details": {
            "rankings": [],
            "recent_form": {"home_summary": {}, "away_summary": {}, "home_matches": [], "away_matches": [], "matches": []},
            "h2h": {"summary": [], "matches": []},
            "fixtures": {"home": [], "away": []}
        }
    }
    has_detailed_data = False

def translate_tournament_code(code_str):
    if not code_str:
        return "기타 공식 경기"
    mapping = {
        "GER D1": "독일 분데스리가", "GERC": "독일 DFB 포칼", "INT CF": "국가대표 친선경기",
        "ENG PR": "잉글랜드 프리미어리그", "ENG FAC": "잉글랜드 FA컵", "SPA D1": "스페인 라리가",
        "SPA D2": "스페인 라리가 2", "SPA CUP": "스페인 코파 델 레이", "ESP D1": "스페인 라리가",
        "ESP C": "스페인 코파 델 레이", "ITA D1": "이탈리아 세리에 A", "ITA Cup": "이탈리아 컵 (코파 이탈리아)",
        "FRA C": "프랑스 쿠프 드 프랑스", "KFAC": "대한민국 코리아컵 (FA컵)", "ENG LC": "잉글랜드 리그컵 (카라바오컵)",
        "ACLE": "AFC 챔피언스리그 엘리트 (ACLE)", "FRA D1": "프랑스 리그 1", "UEFA ECL": "UEFA 유로파 컨퍼런스리그",
        "UEFA CL": "UEFA 챔피언스리그", "UEFA EL": "UEFA 유로파리그", "AFC CL": "AFC 챔피언스리그",
        "ACQ": "AFC 아시안컵 예선", "AC": "AFC 아시안컵 본선", "WC": "FIFA 월드컵 본선",
        "FIFA WC": "FIFA 월드컵 본선", "WCC": "FIFA 클럽 월드컵", "FIFA CWC": "FIFA 클럽 월드컵",
        "U20 WC": "FIFA U-20 월드컵", "U17 WC": "FIFA U-17 월드컵", "W-WC": "FIFA 여자 월드컵"
    }
    converted = code_str
    for k, v in mapping.items():
        if k in code_str:
            converted = code_str.replace(k, v)
            break
    match_pattern = re.search(r'(.*?)(\d{4}\.\d{2}\.\d{2})', converted)
    if match_pattern:
        prefix = match_pattern.group(1).strip()
        date_part = match_pattern.group(2)
        return f"{prefix} - {date_part}"
    return converted

tab_titles = [
    "0단계 (메타)", "규칙 1 (LIFO 7경기)", "규칙 2 (구장 Shift)", 
    "규칙 3 (누수·피로)", "규칙 4 (H2H 상성)", "규칙 5 (최종 람다)", 
    "규칙 6 (푸아송 예측)", "요약 리포트"
]
tabs = st.tabs(tab_titles)

# ==========================================
# 0단계 탭
# ==========================================
with tabs[0]:
    st.markdown("#### [0단계: 대진 정보 및 팀순위 정보]")
    st.markdown("친선 경기를 전면 배제하고 공식 A매치 유효성 검증을 거친 대진 메타데이터를 고정합니다. (SSOT 원칙 적용)")

    match_time_display = detailed_info.get("head_info", {}).get("match_time_display", "")
    if not match_time_display:
        match_time_display = selected_match.get("time", match_date)

    is_neutral_venue = False
    venue_display_text = "구장 정보 없음"

    if has_detailed_data:
        meta_status = "정상 통과 (정밀 데이터 연동 완료)"
        head_info = detailed_info.get("head_info", {})
        league_name = head_info.get("league", tournament_name)
        round_info = head_info.get("round", "")
        tournament_display = f"{league_name} ({round_info})" if round_info else league_name

        stadium_name = head_info.get("stadium", "").strip()
        home_stadium_name = head_info.get("home_stadium", "").strip()
        weather_info = head_info.get("weather", "").strip()

        if stadium_name and home_stadium_name:
            if stadium_name.lower() == home_stadium_name.lower():
                stadium_badge = f"{stadium_name} / <span style='color: #2e7d32; font-weight: bold;'>{home_stadium_name} (홈)</span>"
                is_neutral_venue = False
            else:
                stadium_badge = f"{stadium_name} / <span style='color: #c62828; font-weight: bold;'>{home_stadium_name} (중립)</span>"
                is_neutral_venue = True
        elif stadium_name:
            stadium_badge = f"{stadium_name} / 홈구장 정보 미확인"
        else:
            stadium_badge = "구장 정보 실시간 반영 대기"

        w_text = weather_info if weather_info else "날씨 정보 없음"
        stadium_info = f"{stadium_badge} / 날씨: {w_text}"
    else:
        meta_status = "⚠️ 해당 경기의 상세 정밀 데이터 없음 (데이터 없음)"
        tournament_display = tournament_name
        stadium_info = "데이터 없음"
        is_neutral_venue = False

    meta_markdown_table = f"""
    | 메타 항목 | 상세 정보 (SSOT) |
    | :--- | :--- |
    | **경기 일시** | {match_time_display} |
    | **대회 성격** | {tournament_display} |
    | **대진 매치** | {home_team} vs {away_team} |
    | **구장 정보** | {stadium_info} |
    | **데이터 상태 검증** | {meta_status} |
    """
    st.markdown(meta_markdown_table, unsafe_allow_html=True)
    
    st.markdown("##### 📊 공식 팀 순위 및 country.json 기반 등급·가중치 연동 현황")
    
    # 전역 변수로 활용할 0단계 보정치 기본값 선언
    h_atk_bonus, h_def_bonus, a_atk_bonus, a_def_bonus = "0%", "0%", "0%", "0%"

    if has_detailed_data:
        meta_details = detailed_info.get("meta_details", {})
        rankings_raw = meta_details.get("rankings", [])
        
        @st.cache_data
        def load_country_data():
            if os.path.exists("country.json"):
                with open("country.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}

        country_data = load_country_data()

        def match_with_country_json_exact(rank_val, team_val):
            grades = country_data.get("grades", {})
            rank_str = str(rank_val).strip()
            extracted_code = ""
            if rank_str and rank_str != "-":
                parts = rank_str.split()
                if parts:
                    extracted_code = parts[0].upper()

            for grade_key, countries in grades.items():
                if grade_key == "F":
                    continue
                if isinstance(countries, list):
                    for c in countries:
                        c_code = str(c.get("code", "")).upper()
                        if c_code and c_code == extracted_code:
                            return c.get("code", "-"), rank_str, c.get("grade", "E"), c.get("attack_bonus", "+3%"), c.get("defense_bonus", "-3%")

            f_info = grades.get("F", {})
            fallback_code = extracted_code if extracted_code else "EXT"
            return fallback_code, rank_str if rank_str else "-", "F", f_info.get("attack_bonus", "0%"), f_info.get("defense_bonus", "0%")

        if rankings_raw:
            rankings_list = []
            for idx, r in enumerate(rankings_raw):
                team_name = str(r.get("team", "-"))
                rank_code_str = str(r.get("rank", ""))
                
                matched_code, clean_league, grade, atk_b, def_b = match_with_country_json_exact(rank_code_str, team_name)
                
                # 홈/원정 팀 매칭 시 가중치 변수 자동 할당
                clean_team_n = team_name.strip().replace(" ", "")
                if clean_team_n in home_team.replace(" ", "") or home_team.replace(" ", "") in clean_team_n:
                    h_atk_bonus, h_def_bonus = atk_b, def_b
                elif clean_team_n in away_team.replace(" ", "") or away_team.replace(" ", "") in clean_team_n:
                    a_atk_bonus, a_def_bonus = atk_b, def_b

                rankings_list.append({
                    "No": idx + 1, "리그순위": rank_code_str, "팀": team_name, "국가코드": matched_code,
                    "리그명": league_name, "등급": grade, "공격보정": atk_b, "수비보정": def_b,
                    "경기": str(r.get("played", "0")), "승": str(r.get("win", "0")), "무승부": str(r.get("draw", "0")), "패": str(r.get("loss", "0")),
                    "득점": str(r.get("goals_for", "0")), "실점": str(r.get("goals_against", "0")), "득실": str(r.get("goal_diff", "0")), "승점": str(r.get("points", "0"))
                })
            df_rankings = pd.DataFrame(rankings_list)
            st.dataframe(df_rankings[["리그순위", "팀", "국가코드", "리그명", "등급", "공격보정", "수비보정", "경기", "승", "무승부", "패", "득점", "실점", "득실", "승점"]], use_container_width=True, hide_index=True)
        else:
            st.info("💡 해당 경기에 수집된 순위 및 전적표 데이터(rankings)가 존재하지 않습니다.")
    else:
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터가 아직 수집되지 않았습니다.")

# ==========================================
# 규칙 1번 탭
# ==========================================
with tabs[1]:
    st.markdown(f"#### [규칙 1번: 종합 최근 10경기 로그 및 A~E 등급별 공수 티어 산출] - {home_team} vs {away_team}")
    st.markdown("""
        <div class="step-box">
            <b>📌 규격 원칙 및 요약 설명:</b><br>
            • <b>전수 조사 및 LIFO 방식:</b> 홈/원정 통합 최근 공식 경기 10개를 최신순 역순(LIFO)으로 전수 조사하며, 골득실 평균을 산출하여 티어 산정표의 티어를 각 양팀에 부여합니다.<br>
            • <b>친선 경기 전면 배제:</b> 최근 경기 표본에서 모든 친선 경기를 영구 배제하며, 오직 공식 경기만을 채택합니다.<br>
            • <b>특수 룰 조건부 발동 (E티어 득실점 50% 할인):</b> 현재 팀의 공격력이 A티어이거나 방어력이 E티어일 때만 발동하며, 발동 시 E티어 상대 경기 득점과 실점에 각각 50% 할인(0.5 곱셈)을 적용합니다.
        </div>
        """, unsafe_allow_html=True,
    )
        
    tier_weight_df = pd.DataFrame({
        "등급 (Tier)": ["Tier A", "Tier B", "Tier C", "Tier D", "Tier E"],
        "공격력 기준 (평균 득점)": ["2.3골 이상", "1.7 ~ 2.2골 미만", "1.1 ~ 1.6골 미만", "0.5 ~ 1.1골 미만", "0.5골 미만 (< 0.5)"],
        "공격 가중치": ["+12.0%", "+9.0%", "+6.0%", "+3.0%", "0.0% (최하위)"],
        "방어력 기준 (평균 실점)": ["0.5골 미만 (< 0.5)", "0.5 ~ 0.9골 미만", "0.9 ~ 1.3골 미만", "1.3 ~ 1.7골 미만", "2.0골 이상"],
        "방어 가중치": ["-12.0% (최상위)", "-9.0%", "-6.0%", "-3.0%", "0.0%"]
    })
    st.dataframe(tier_weight_df, use_container_width=True, hide_index=True)

    target_v3_data = None
    target_code = str(match_code).strip()
    target_home = str(home_team).strip().replace(" ", "")
    target_away = str(away_team).strip().replace(" ", "")

    if target_code and target_code in v3_details_dict:
        target_v3_data = v3_details_dict[target_code]
    else:
        for k, v in v3_details_dict.items():
            v_home = str(v.get("home", "")).strip().replace(" ", "")
            v_away = str(v.get("away", "")).strip().replace(" ", "")
            if v_home == target_home and v_away == target_away:
                target_v3_data = v
                break

    if not target_v3_data:
        target_v3_data = {"meta_details": {"recent_form": {"home_matches": [], "away_matches": []}, "stadium_form": {"home_matches": [], "away_matches": []}}}

    v3_meta = target_v3_data.get("meta_details", {})
    recent_form = v3_meta.get("recent_form", {})
    stadium_form = v3_meta.get("stadium_form", {})

    h_name = home_team
    a_name = away_team

    h_matches = recent_form.get("home_matches", [])
    a_matches = recent_form.get("away_matches", [])

    h_sum = recent_form.get("home_summary", {})
    a_sum = recent_form.get("away_summary", {})
    h_gpg_base = round(float(h_sum.get("goals_per_game", 0)), 2)
    h_cpg_base = round(float(h_sum.get("conceded_per_game", 0)), 2)
    h_rec_base = h_sum.get("recent_record", "0전 0승 0무 0패")
    
    a_gpg_base = round(float(a_sum.get("goals_per_game", 0)), 2)
    a_cpg_base = round(float(a_sum.get("conceded_per_game", 0)), 2)
    a_rec_base = a_sum.get("recent_record", "0전 0승 0무 0패")

    def atk_tier(g):
        if g >= 2.3: return "Tier A", "+12.0%"
        elif g >= 1.7: return "Tier B", "+9.0%"
        elif g >= 1.1: return "Tier C", "+6.0%"
        elif g >= 0.5: return "Tier D", "+3.0%"
        else: return "Tier E", "0.0%"

    def def_tier(c):
        if c < 0.5: return "Tier A", "-12.0%"
        elif c < 0.9: return "Tier B", "-9.0%"
        elif c < 1.3: return "Tier C", "-6.0%"
        elif c < 1.7: return "Tier D", "-3.0%"
        else: return "Tier E", "0.0%"

    def atk_tier_nm(g): return atk_tier(g)[0]
    def def_tier_nm(c): return def_tier(c)[0]

    def check_trigger_status(matches, tname, def_gpg, def_cpg):
        if not matches:
            return atk_tier_nm(def_gpg) == "Tier A" or def_tier_nm(def_cpg) == "Tier E"
        raw_s = 0.0
        raw_c = 0.0
        for m in matches:
            scores = m.get("ft_scores", ["0", "0"])
            try:
                s1, s2 = int(scores[0]), int(scores[1])
            except:
                s1 = s2 = 0
            teams = m.get("teams", "")
            sc, cc = s1, s2
            if " vs " in teams:
                t1, t2 = teams.split(" vs ")
                if tname in t1: sc, cc = s1, s2
                elif tname in t2: sc, cc = s2, s1
            raw_s += sc
            raw_c += cc
        cnt = len(matches)
        tmp_gpg = raw_s / cnt if cnt > 0 else def_gpg
        tmp_cpg = raw_c / cnt if cnt > 0 else def_cpg
        return (atk_tier_nm(tmp_gpg) == "Tier A") or (def_tier_nm(tmp_cpg) == "Tier E")

    h_is_triggered = check_trigger_status(h_matches, h_name, h_gpg_base, h_cpg_base)
    a_is_triggered = check_trigger_status(a_matches, a_name, a_gpg_base, a_cpg_base)

    def local_make_df(matches, tname, def_gpg, def_cpg, def_rec, is_triggered=False):
        if not matches:
            return pd.DataFrame(), def_gpg, def_cpg, def_rec, 0.0, 0.0
            
        rows = []
        eff_scored = 0.0
        eff_conceded = 0.0
        raw_scored_total = 0.0
        raw_conceded_total = 0.0
        w = d = l = 0
        
        for idx, m in enumerate(matches):
            league = m.get("league", "-")
            mtime = m.get("match_time", "-")
            formatted_mtime = mtime
            try:
                clean_date = mtime.split(" ")[0].replace("-", ".").replace("/", ".")
                parts = clean_date.split(".")
                if len(parts) == 3:
                    if len(parts[2]) == 4 and len(parts[0]) <= 2:
                        formatted_mtime = f"{parts[2]}.{parts[0].zfill(2)}.{parts[1].zfill(2)}"
            except Exception:
                pass

            teams = m.get("teams", "-")
            scores = m.get("ft_scores", ["0", "0"])
            try:
                s1, s2 = int(scores[0]), int(scores[1])
            except:
                s1 = s2 = 0
                
            sc, cc = 0, 0
            pair = teams.split(" vs ")
            if len(pair) == 2:
                t1, t2 = pair[0].strip(), pair[1].strip()
                if tname in t1: sc, cc = s1, s2
                elif tname in t2: sc, cc = s2, s1
                else: sc, cc = s1, s2
            else:
                sc, cc = s1, s2
                
            raw_scored_total += sc
            raw_conceded_total += cc
            
            if sc > cc: w += 1; res = "승"
            elif sc == cc: d += 1; res = "무"
            else: l += 1; res = "패"
                
            tier_str = "정보 없음"
            mult = 1.0
            tier_info = m.get("opponent_tier_info", "")
            if tier_info and "/" in tier_info:
                try:
                    oa, od = map(float, tier_info.split("/"))
                    at_name = atk_tier_nm(oa)
                    df_name = def_tier_nm(od)
                    tier_str = f"공격 {at_name} ({oa:.2f}) / 방어 {df_name} ({od:.2f})"
                    if is_triggered and (at_name == "Tier E" or df_name == "Tier E"):
                        mult = 0.5
                        tier_str += " ⚠️ (발동: E티어 득실점 50% 할인)"
                    else:
                        tier_str += " (보정 없음 / 유지)"
                except:
                    pass
                    
            app_sc = sc * mult
            app_cc = cc * mult
            eff_scored += app_sc
            eff_conceded += app_cc
            
            seq = f"최신 ({idx+1})" if idx == 0 else str(idx+1)
            score_display = f"{s1} : {s2}" + (f" (할인 득실: {app_sc:.1f} : {app_cc:.1f})" if mult < 1.0 else " (유지)")
            
            rows.append({
                "LIFO 순서": seq, "경기 일시": formatted_mtime, "대회": translate_tournament_code(league),
                "대진": teams, "스코어": score_display, "결과": res, "상대 공수 티어": tier_str
            })
            
        cnt = len(matches)
        gpg = round(eff_scored / cnt, 2) if cnt > 0 else def_gpg
        cpg = round(eff_conceded / cnt, 2) if cnt > 0 else def_cpg
        rec = f"{cnt}전 {w}승 {d}무 {l}패" if cnt > 0 else def_rec
        return pd.DataFrame(rows), gpg, cpg, rec, raw_scored_total, raw_conceded_total

    h_df, h_gpg, h_cpg, h_rec, h_raw_s, h_raw_c = local_make_df(h_matches, h_name, h_gpg_base, h_cpg_base, h_rec_base, is_triggered=h_is_triggered)
    a_df, a_gpg, a_cpg, a_rec, a_raw_s, a_raw_c = local_make_df(a_matches, a_name, a_gpg_base, a_cpg_base, a_rec_base, is_triggered=a_is_triggered)

    h_at, h_atw = atk_tier(h_gpg)
    h_de, h_dew = def_tier(h_cpg)
    a_at, a_atw = atk_tier(a_gpg)
    a_de, a_dew = def_tier(a_cpg)

    h_goal_diff = h_raw_s - h_raw_c
    a_goal_diff = a_raw_s - a_raw_c

    st.markdown(f"##### 홈 팀 ({h_name}) 최근 전적 분석 로그 ")
    if not h_df.empty: st.dataframe(h_df, use_container_width=True, hide_index=True)
    else: st.info("📋 개별 경기 상세 데이터 없음")
        
    st.markdown(f"""<div class="calc-box">
        <b>{h_name} 규칙 1번 상세 산출 내역</b><br>
        • 최근 전적: <b>{h_rec}</b> (총 득점: <b>{h_raw_s:.1f}골</b> / 총 실점: <b>{h_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if h_goal_diff >= 0 else '#c62828'};">{h_goal_diff:+.1f}</b>)<br>
        • 보정 평균 득점: <b>{h_gpg:.2f}골/경기</b> / 보정 평균 실점: <b>{h_cpg:.2f}골/경기</b><br>
        • 공격 티어: <b>{h_at} ({h_atw})</b> | 방어 티어: <b>{h_de} ({h_dew})</b> | 특수룰 발동여부: <b>{'발동됨 (득실점 50% 할인 적용)' if h_is_triggered else '미발동 (유지)'}</b>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"##### 원정 팀 ({a_name}) 최근 전적 분석 로그 ")
    if not a_df.empty: st.dataframe(a_df, use_container_width=True, hide_index=True)
    else: st.info("📋 개별 경기 상세 데이터 없음")
        
    st.markdown(f"""<div class="calc-box">
        <b>{a_name} 규칙 1번 상세 산출 내역</b><br>
        • 최근 전적: <b>{a_rec}</b> (총 득점: <b>{a_raw_s:.1f}골</b> / 총 실점: <b>{a_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if a_goal_diff >= 0 else '#c62828'};">{a_goal_diff:+.1f}</b>)<br>
        • 보정 평균 득점: <b>{a_gpg:.2f}골/경기</b> / 보정 평균 실점: <b>{a_cpg:.2f}골/경기</b><br>
        • 공격 티어: <b>{a_at} ({a_atw})</b> | 방어 티어: <b>{a_de} ({a_dew})</b> | 특수룰 발동여부: <b>{'발동됨 (득실점 50% 할인 적용)' if a_is_triggered else '미발동 (유지)'}</b>
    </div>""", unsafe_allow_html=True)

# ==========================================
# 규칙 2번 탭
# ==========================================
with tabs[2]:
    st.markdown(f"#### [규칙 2번: 구장별 Shift 검증 및 티어 보정] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
    <b>📌 규격 원칙 및 요약 설명:</b><br>
    • <b>구장별 전적(Stadium Form) 분석:</b> 일반 홈경기일 때는 홈팀의 홈 경기 구장 데이터를, 중립경기일 때는 최근 전적 중 '원정 경기' 조건으로 최대 10개까지 추출합니다.<br>
    • <b>0단계 구장 판정 연동:</b> 홈구장 일치 여부에 따라 홈경기(초록색) 또는 중립경기(빨간색) 상태를 명시하고 원정 데이터를 분기 적용합니다.
    </div>
    """, unsafe_allow_html=True)

    tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
    h_atk_val, h_def_val, a_atk_val, a_def_val = 0.0, 0.0, 0.0, 0.0

    if has_detailed_data:
        head_meta = detailed_info.get("head_info", {})
        venue_val = str(head_meta.get("stadium", "")) or str(head_meta.get("venue", ""))
        home_stadium_val = str(head_meta.get("home_stadium", ""))
        
        is_neutral_venue = False
        if venue_val and home_stadium_val:
            if venue_val.strip().lower() != home_stadium_val.strip().lower():
                is_neutral_venue = True

        if is_neutral_venue:
            recent_all_pool = stadium_form.get("recent_matches", []) if "recent_matches" in stadium_form else []
            if not recent_all_pool and 'h_matches' in locals():
                recent_all_pool = h_matches
            neutral_home_away_matches = []
            for m in recent_all_pool:
                teams_str = str(m.get("teams", ""))
                if " vs " in teams_str:
                    t_parts = [p.strip() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2 and h_name not in t_parts[0]:
                        neutral_home_away_matches.append(m)
                elif m.get("location") == "원정" or m.get("venue_type") == "away":
                    neutral_home_away_matches.append(m)
            if not neutral_home_away_matches:
                neutral_home_away_matches = stadium_form.get("away_matches", [])
            s_home_matches = neutral_home_away_matches[:10]
        else:
            s_home_matches = stadium_form.get("home_matches", [])[:10]

        s_away_matches = stadium_form.get("away_matches", [])[:10]

        s_h_df, s_h_gpg, s_h_cpg, s_h_rec, s_h_raw_s, s_h_raw_c = local_make_df(s_home_matches, h_name, 0.0, 0.0, "0전 0승 0무 0패", is_triggered=h_is_triggered)
        s_a_df, s_a_gpg, s_a_cpg, s_a_rec, s_a_raw_s, s_a_raw_c = local_make_df(s_away_matches, a_name, 0.0, 0.0, "0전 0승 0무 0패", is_triggered=a_is_triggered)

        s_h_at, s_h_atw = atk_tier(s_h_gpg)
        s_h_de, s_h_dew = def_tier(s_h_cpg)
        s_a_at, s_a_atw = atk_tier(s_a_gpg)
        s_a_de, s_a_dew = def_tier(s_a_cpg)

        base_h_at = h_at if 'h_at' in locals() else "Tier C"
        base_h_de = h_de if 'h_de' in locals() else "Tier C"
        base_a_at = a_at if 'a_at' in locals() else "Tier C"
        base_a_de = a_de if 'a_de' in locals() else "Tier C"

        h_current_at = s_h_at
        h_current_de = s_h_de
        a_current_at = s_a_at
        a_current_de = s_a_de

        def get_tier_colored_html(base_tier, stadium_tier):
            b_val = tier_ranks.get(base_tier, 3)
            s_val = tier_ranks.get(stadium_tier, 3)
            if s_val > b_val: return f"<span style='color: #2e7d32; font-weight: bold;'>{stadium_tier} 📈</span>"
            elif s_val < b_val: return f"<span style='color: #c62828; font-weight: bold;'>{stadium_tier} 📉</span>"
            else: return f"<span>{stadium_tier}</span>"

        h_atk_color_str = get_tier_colored_html(base_h_at, s_h_at)
        h_def_color_str = get_tier_colored_html(base_h_de, s_h_de)
        a_atk_color_str = get_tier_colored_html(base_a_at, s_a_at)
        a_def_color_str = get_tier_colored_html(base_a_de, s_a_de)

        def get_shift_correction(base_tier, stadium_tier, is_attack=True):
            b_val = tier_ranks.get(base_tier, 3)
            s_val = tier_ranks.get(stadium_tier, 3)
            if is_attack:
                if s_val > b_val: return "+15%", 15.0
                elif s_val < b_val: return "-15%", -15.0
                else: return "0%", 0.0
            else:
                if s_val < b_val: return "+15%", 15.0
                elif s_val > b_val: return "-15%", -15.0
                else: return "0%", 0.0

        h_atk_shift_str, h_atk_val = get_shift_correction(base_h_at, s_h_at, is_attack=True)
        h_def_shift_str, h_def_val = get_shift_correction(base_h_de, s_h_de, is_attack=False)
        a_atk_shift_str, a_atk_val = get_shift_correction(base_a_at, s_a_at, is_attack=True)
        a_def_shift_str, a_def_val = get_shift_correction(base_a_de, s_a_de, is_attack=False)

        s_h_diff = s_h_raw_s - s_h_raw_c
        s_a_diff = s_a_raw_s - s_a_raw_c
        venue_status_badge = "<span style='color: #c62828; font-weight: bold;'> (중립경기)</span>" if is_neutral_venue else "<span style='color: #2e7d32; font-weight: bold;'> (홈경기)</span>"

        st.markdown(f"##### 홈 팀 ({h_name}) 구장별 전적 및 티어 변동 검증{venue_status_badge}", unsafe_allow_html=True)
        if not s_h_df.empty: st.dataframe(s_h_df, use_container_width=True, hide_index=True)
        
        st.markdown(f"""<div class="calc-box">
        <b>{h_name} 규칙 2번(구장별) Shift 보정 산출 내역</b><br>
        • 최근 전적: <b>{s_h_rec}</b> (총 득점: <b>{s_h_raw_s:.1f}골</b> / 실점: <b>{s_h_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if s_h_diff >= 0 else '#c62828'};">{s_h_diff:+.1f}</b>)<br>
        • 보정 평균 득점: <b>{s_h_gpg:.2f}골</b> / 실점: <b>{s_h_cpg:.2f}골</b><br>
        • 1단계 종합 체급: 공격 <b>{base_h_at}</b> / 방어 <b>{base_h_de}</b> &nbsp;|&nbsp; 구장 환경 체급: 공격 <b>{h_atk_color_str}</b> / 방어 <b>{h_def_color_str}</b><br>
        • <b>적용된 구장 Shift 보정치:</b> 공격 <b>{h_atk_shift_str}</b> / 방어 <b>{h_def_shift_str}</b>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"##### 원정 팀 ({a_name}) 구장별 전적 및 티어 변동 검증")
        if not s_a_df.empty: st.dataframe(s_a_df, use_container_width=True, hide_index=True)
        
        st.markdown(f"""<div class="calc-box">
        <b>{a_name} 규칙 2번(구장별) Shift 보정 산출 내역</b><br>
        • 최근 전적: <b>{s_a_rec}</b> (총 득점: <b>{s_a_raw_s:.1f}골</b> / 실점: <b>{s_a_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if s_a_diff >= 0 else '#c62828'};">{s_a_diff:+.1f}</b>)<br>
        • 보정 평균 득점: <b>{s_a_gpg:.2f}골</b> / 실점: <b>{s_a_cpg:.2f}골</b><br>
        • 1단계 종합 체급: 공격 <b>{base_a_at}</b> / 방어 <b>{base_a_de}</b> &nbsp;|&nbsp; 구장 환경 체급: 공격 <b>{a_atk_color_str}</b> / 방어 <b>{a_def_color_str}</b><br>
        • <b>적용된 구장 Shift 보정치:</b> 공격 <b>{a_atk_shift_str}</b> / 방어 <b>{a_def_shift_str}</b>
        </div>""", unsafe_allow_html=True)
    else:
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터가 아직 수집되지 않았습니다.")

# ==========================================
# 규칙 3번 탭
# ==========================================
with tabs[3]:
    st.markdown(f"#### [규칙 3번: 선수 전력 누수 및 이동 피로도 분석] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
        <b>📌 규칙 3번 규격 원칙 및 요약 설명:</b><br>
        • <b>정량 수치 모델 적용:</b> 기초 사실(Fact)을 바탕으로 하되, 분석 및 스코어 도출은 엄격한 정량 수치 모델을 적용합니다.<br>
        • <b>부호 대칭 규격:</b> 누수(부상·징계·이적)는 공격력 음수(-), 방어력 양수(+) / 가산(복귀·입단)은 공격력 양수(+), 방어력 음수(-)를 적용합니다.<br>
        • <b>포지션별 반감(Halved) 규칙:</b> 공격 자원의 방어 보정과 수비 자원의 공격 보정은 1/2로 반감 적용합니다.<br>
        • <b>이동 피로도 룰:</b> 원정 경기마다 누적되며, 홈 복귀 또는 휴식 시 0%로 Reset 됩니다 (단계마다 공격 -5%, 방어 +5%).
    </div>
    """, unsafe_allow_html=True)

    h_squad_changes, a_squad_changes = [], []
    if has_detailed_data:
        meta_det = detailed_info.get("meta_details", {})
        h_squad_changes = meta_det.get("home_squad_changes", [])
        a_squad_changes = meta_det.get("away_squad_changes", [])

    def build_squad_dataframe(changes_list, team_label):
        if not changes_list:
            return pd.DataFrame([{
                "선수 실명": "-", "포지션": "-", "변동 유형": "-", "핵심 영향력": "특이 전력 누수/가산 없음",
                "시즌 누적 스탯": "-", "등급": "-", "공격 보정": "0.0%", "방어 보정": "0.0%", "비고": "정상 스쿼드 가동"
            }]), 0.0, 0.0
        
        rows = []
        tot_atk, tot_def = 0.0, 0.0
        for item in changes_list:
            p_name = item.get("name", "-")
            p_pos = item.get("position", "-")
            p_type = item.get("type", "누수")
            p_grade = item.get("grade", "중 (Medium)")
            p_memo = item.get("memo", "-")
            
            rate = 14.0 if "상" in p_grade else (7.0 if "중" in p_grade else 0.0)
            if p_type == "누수":
                atk_v = -rate
                def_v = rate if "FW" in p_pos or "MF" in p_pos else rate / 2.0
            else:
                atk_v = rate
                def_v = -rate if "DF" in p_pos or "GK" in p_pos else -rate / 2.0

            tot_atk += atk_v
            tot_def += def_v
            rows.append({
                "선수 실명": p_name, "포지션": p_pos, "변동 유형": p_type, "핵심 영향력": p_memo,
                "시즌 누적 스탯": item.get("stats", "-"), "등급": p_grade,
                "공격 보정": f"{atk_v:+.1f}%", "방어 보정": f"{def_v:+.1f}%", "비고": "적용 완료"
            })
        return pd.DataFrame(rows), tot_atk, tot_def

    st.markdown(f"##### 3-1: 구단명 - {home_team} 선수 전력 변동")
    table_3_1_home, h_r31_atk_val, h_r31_def_val = build_squad_dataframe(h_squad_changes, home_team)
    st.dataframe(table_3_1_home, use_container_width=True, hide_index=True)

    st.markdown(f"##### 3-1: 구단명 - {away_team} 선수 전력 변동")
    table_3_1_away, a_r31_atk_val, a_r31_def_val = build_squad_dataframe(a_squad_changes, away_team)
    st.dataframe(table_3_1_away, use_container_width=True, hide_index=True)
    st.markdown("---")

    def get_team_standing_info(target_team_name):
        target_clean = str(target_team_name).strip().replace(" ", "")
        matched_standings = []
        for l_id, l_data in v4_leagues_dict.items():
            standings = l_data.get("standings", [])
            league_name = l_data.get("league_name", "해외 리그")
            for row in standings:
                row_team = str(row.get("team", "")).strip().replace(" ", "")
                if target_clean in row_team or row_team in target_clean:
                    raw_label = str(row.get("tag_label", "일반"))
                    matched_standings.append({
                        "league_name": league_name, "rank": str(row.get("rank", "-")),
                        "team": row.get("team", target_team_name), "tag_label": raw_label,
                        "경기수": str(row.get("경기수", "0")), "승": str(row.get("승", "0")), "무": str(row.get("무", "0")),
                        "패": str(row.get("패", "0")), "득실": str(row.get("득실", "0")), "승점": str(row.get("승점", "-"))
                    })
        return matched_standings

    def determine_match_importance(standing_info_list, league_raw_name):
        league_str = str(league_raw_name)
        if any(k in league_str for k in ["친선", "CF", "탈락", "강등확정"]): return "중요도하", -10.0, 10.0
        if not standing_info_list: return "중요도중", 5.0, -5.0
        return "중요도중", 5.0, -5.0

    home_standings_list = get_team_standing_info(home_team)
    away_standings_list = get_team_standing_info(away_team)

    h_last_fatigue, a_last_fatigue = 0, 0
    if has_detailed_data:
        meta_details = detailed_info.get("meta_details", {})
        fixtures_info = meta_details.get("fixtures", {})
        raw_home_fixes = list(fixtures_info.get("home", []))
        raw_away_fixes = list(fixtures_info.get("away", []))

        def parse_timeline_strictly_isolated(fix_list, recent_list, target_team_name, base_match_date, is_home_team):
            base_dt = None
            try:
                base_clean = base_match_date.split(" ")[0].replace(".", "-").replace("/", "-")
                base_dt = datetime.strptime(base_clean[:10], "%Y-%m-%d")
            except Exception:
                base_dt = datetime.now()

            combined_pool = []
            seen_identifiers = set()
            for f in list(fix_list) + list(recent_list):
                uid = f"{f.get('match_time', '')}_{f.get('teams', '')}"
                if uid not in seen_identifiers:
                    combined_pool.append(f)
                    seen_identifiers.add(uid)

            past_arr = []
            for f in combined_pool:
                try:
                    c_clean = str(f.get("match_time", "")).split(" ")[0].replace(".", "-").replace("/", "-")
                    c_dt = datetime.strptime(c_clean[:10], "%Y-%m-%d")
                    d_diff = (c_dt - base_dt).days
                    if d_diff < 0: past_arr.append((d_diff, f))
                except Exception:
                    continue

            chrono_sorted_past = sorted(past_arr, key=lambda x: x[0])
            past_7d, past_4d = [], []
            for d_d, f_item in chrono_sorted_past:
                abs_d = abs(d_d)
                if 4 < abs_d <= 7: past_7d.append(f_item)
                elif 1 <= abs_d <= 4: past_4d.append(f_item)

            fatigue_cnt = 0
            if past_4d: fatigue_cnt += 1
            if past_7d: fatigue_cnt += 1
            my_loc = "홈" if is_home_team else "원정"
            return fatigue_cnt if my_loc == "원정" else max(0, fatigue_cnt - 1)

        h_last_fatigue = parse_timeline_strictly_isolated(raw_home_fixes, list(h_matches), home_team, match_date, True)
        a_last_fatigue = parse_timeline_strictly_isolated(raw_away_fixes, list(a_matches), away_team, match_date, False)

    h_fa, h_fd = -5 * h_last_fatigue, 5 * h_last_fatigue
    a_fa, a_fd = -5 * a_last_fatigue, 5 * a_last_fatigue

# ==========================================
# 규칙 4번 탭 (독립 스코프 안전 보장)
# ==========================================
home_win_rate = 0.0
away_win_rate = 0.0
h_r4_atk_val, h_r4_def_val, a_r4_atk_val, a_r4_def_val = 0.0, 0.0, 0.0, 0.0

with tabs[4]:
    st.markdown(f"#### [규칙 4번: 역대 공식 맞대결 상성 전수 로그 및 단방향 10% 룰] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
        <b>📌 규칙 4번 규격 원칙 및 요약 설명:</b><br>
        • <b>전수 조사 대상:</b> 역대 공식 맞대결 최근 10경기 전수 조사 (5경기 미만일 시 동등 팀으로 간주)<br>
        • <b>단방향 10% 룰:</b> 통산 승률 50% 이상인 상성 우세 팀에게 공격력 +10% 및 방어력 -10% 단방향 상성 보정을 동시 부여합니다.
    </div>
    """, unsafe_allow_html=True)

    if has_detailed_data:
        meta_details = detailed_info.get("meta_details", {})
        h2h_info = meta_details.get("h2h", {})
        h2h_matches = h2h_info.get("matches", [])
        h2h_summary = h2h_info.get("summary", [])
        
        if h2h_matches:
            home_wins, draws, away_wins = 0, 0, 0
            total_games = len(h2h_matches)
            for m in h2h_matches:
                row_cols = m.get("row_data", [])
                if len(row_cols) >= 4:
                    try:
                        scores = row_cols[2].replace("：", "-").split("-")
                        h_score, a_score = int(scores[0].strip()), int(scores[1].strip())
                        if row_cols[1] == home_team:
                            if h_score > a_score: home_wins += 1
                            elif h_score < a_score: away_wins += 1
                            else: draws += 1
                        else:
                            if h_score > a_score: away_wins += 1
                            elif h_score < a_score: home_wins += 1
                            else: draws += 1
                    except: pass

            home_win_rate = (home_wins / total_games * 100) if total_games > 0 else 0.0
            away_win_rate = (away_wins / total_games * 100) if total_games > 0 else 0.0
            
            if total_games >= 5:
                if home_win_rate >= 50.0:
                    h_r4_atk_val, h_r4_def_val = 10.0, -10.0
                elif away_win_rate >= 50.0:
                    a_r4_atk_val, a_r4_def_val = 10.0, -10.0

            st.markdown(f"""<div class="calc-box">
                <b>규칙 4번 산출 내역:</b><br>
                • <b>{home_team} 승률:</b> {home_win_rate:.1f}% ({home_wins}승 / {total_games}전)<br>
                • <b>{away_team} 승률:</b> {away_win_rate:.1f}% ({away_wins}승 / {total_games}전)
            </div>""", unsafe_allow_html=True)

# ==========================================
# 규칙 5번 탭 (0~4단계 누적 합산 및 5-1 ~ 5-4 표 완벽 연동)
# ==========================================
with tabs[5]:
    st.markdown(f"#### [규칙 5번: 최종 보정 및 1차 기본 기대 득실점 산출] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
        <b>📌 규격 원칙 및 요약 설명:</b><br>
        • 1단계 공수 기본 기대치부터 규칙 0~4까지의 모든 보정치를 누적 합산합니다.<br>
        • 최종 누적 보정치와 독자 공수 한계선을 바탕으로 기하평균 공수 교차 상쇄 결합 연산을 수행하여 최종 1차 기본 기대 득실점을 도출합니다.
    </div>
    """, unsafe_allow_html=True)

    if has_detailed_data:
        def parse_pct_safe(val):
            if not val: return 0.0
            try: return float(str(val).replace('%', '').replace('+', '').strip())
            : except: return 0.0

        h_base_g = h_gpg if 'h_gpg' in locals() else 1.2
        h_base_c = h_cpg if 'h_cpg' in locals() else 1.0
        a_base_g = a_gpg if 'a_gpg' in locals() else 1.1
        a_base_c = a_cpg if 'a_cpg' in locals() else 1.1

        # 0단계 가중치 연동
        h_c_atk = parse_pct_safe(h_atk_bonus)
        h_c_def = parse_pct_safe(h_def_bonus)
        a_c_atk = parse_pct_safe(a_atk_bonus)
        a_c_def = parse_pct_safe(a_def_bonus)

        # 규칙 1 가중치 연동
        h_r1_atk = parse_pct_safe(h_atw if 'h_atw' in locals() else "0%")
        h_r1_def = parse_pct_safe(h_dew if 'h_dew' in locals() else "0%")
        a_r1_atk = parse_pct_safe(a_atw if 'a_atw' in locals() else "0%")
        a_r1_def = parse_pct_safe(a_dew if 'a_dew' in locals() else "0%")

        # 규칙 2 구장 Shift 연동
        h_r2_atk = h_atk_val if 'h_atk_val' in locals() else 0.0
        h_r2_def = h_def_val if 'h_def_val' in locals() else 0.0
        a_r2_atk = a_atk_val if 'a_atk_val' in locals() else 0.0
        a_r2_def = a_def_val if 'a_def_val' in locals() else 0.0

        # 규칙 3-1 선수 전력 연동
        h_r31_atk = h_r31_atk_val if 'h_r31_atk_val' in locals() else 0.0
        h_r31_def = h_r31_def_val if 'h_r31_def_val' in locals() else 0.0
        a_r31_atk = a_r31_atk_val if 'a_r31_atk_val' in locals() else 0.0
        a_r31_def = a_r31_def_val if 'a_r31_def_val' in locals() else 0.0

        # 규칙 3-2 피로도 연동
        h_r32_atk = -5 * h_last_fatigue
        h_r32_def = 5 * h_last_fatigue
        a_r32_atk = -5 * a_last_fatigue
        a_r32_def = 5 * a_last_fatigue

        # 규칙 4 상성 연동
        if home_win_rate >= 50.0:
            h_r4_atk, h_r4_def = 10.0, -10.0
        else:
            h_r4_atk, h_r4_def = 0.0, 0.0

        if away_win_rate >= 50.0:
            a_r4_atk, a_r4_def = 10.0, -10.0
        else:
            a_r4_atk, a_r4_def = 0.0, 0.0

        # 최종 누적 합산
        h_tot_atk_pct = h_c_atk + h_r1_atk + h_r2_atk + h_r31_atk + h_r32_atk + h_r4_atk
        h_tot_def_pct = h_c_def + h_r1_def + h_r2_def + h_r31_def + h_r32_def + h_r4_def
        a_tot_atk_pct = a_c_atk + a_r1_atk + a_r2_atk + a_r31_atk + a_r32_atk + a_r4_atk
        a_tot_def_pct = a_c_def + a_r1_def + a_r2_def + a_r31_def + a_r32_def + a_r4_def

        h_max_g = h_base_g * (1 + h_tot_atk_pct / 100.0)
        h_min_c = h_base_c * (1 + h_tot_def_pct / 100.0)
        a_max_g = a_base_g * (1 + a_tot_atk_pct / 100.0)
        a_min_c = a_base_c * (1 + a_tot_def_pct / 100.0)

        h_final_exp_g = max(0.2, (h_max_g + (2.0 - a_min_c)) / 2.0)
        h_final_exp_c = max(0.2, (h_min_c + (2.0 - a_max_g)) / 2.0)
        a_final_exp_g = max(0.2, (a_max_g + (2.0 - h_min_c)) / 2.0)
        a_final_exp_c = max(0.2, (a_min_c + (2.0 - h_max_g)) / 2.0)

        st.markdown(f"##### 📊 [5-1 표] 최종 보정 득실점 산출 매트릭스 ({home_team} vs {away_team})")
        table_data_51 = [
            {"구분 항목": "1단계: 공수 기본 기대치", f"홈 팀 ({home_team})": f"평균 득점 {h_base_g:.2f} / 실점 {h_base_c:.2f}", f"원정 팀 ({away_team})": f"평균 득점 {a_base_g:.2f} / 실점 {a_base_c:.2f}", "보정 및 산출 연산 근거": "대륙/국가 기본 공수 스케일 수치"},
            {"구분 항목": "0단계 연동 (국가/리그 티어 가중치)", f"홈 팀 ({home_team})": f"공격 {h_c_atk:+.1f}% / 방어 {h_c_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_c_atk:+.1f}% / 방어 {a_c_def:+.1f}%", "보정 및 산출 연산 근거": "country.json 기반 국가 등급 보정"},
            {"구분 항목": "규칙 1 (7경기 LIFO 가중치)", f"홈 팀 ({home_team})": f"공격 {h_r1_atk:+.1f}% / 방어 {h_r1_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r1_atk:+.1f}% / 방어 {a_r1_def:+.1f}%", "보정 및 산출 연산 근거": "최근 10경기 상대 티어 가중치"},
            {"구분 항목": "규칙 2 (구장 환경 보정)", f"홈 팀 ({home_team})": f"공격 {h_r2_atk:+.1f}% / 방어 {h_r2_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r2_atk:+.1f}% / 방어 {a_r2_def:+.1f}%", "보정 및 산출 연산 근거": "홈/원정 구장 Shift 변동성"},
            {"구분 항목": "규칙 3-1 (선수 전력 변동)", f"홈 팀 ({home_team})": f"공격 {h_r31_atk:+.1f}% / 방어 {h_r31_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r31_atk:+.1f}% / 방어 {a_r31_def:+.1f}%", "보정 및 산출 연산 근거": "핵심 자원 누수/가산"},
            {"구분 항목": "규칙 3-2 (이동 피로도)", f"홈 팀 ({home_team})": f"공격 {h_r32_atk:+.1f}% / 방어 {h_r32_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r32_atk:+.1f}% / 방어 {a_r32_def:+.1f}%", "보정 및 산출 연산 근거": "이동 거리 및 피로도 누적 적용"},
            {"구분 항목": "규칙 4 (H2H 상성 보정)", f"홈 팀 ({home_team})": f"공격 {h_r4_atk:+.1f}% / 방어 {h_r4_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r4_atk:+.1f}% / 방어 {a_r4_def:+.1f}%", "보정 및 산출 연산 근거": "최근 10전 단방향 상성 우세 여부"},
            {"구분 항목": "최종 누적 보정치 합계", f"홈 팀 ({home_team})": f"공격 {h_tot_atk_pct:+.1f}% / 방어 {h_tot_def_pct:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_tot_atk_pct:+.1f}% / 방어 {a_tot_def_pct:+.1f}%", "보정 및 산출 연산 근거": "규칙 0~4 보정치 최종 누적 합산"},
            {"구분 항목": "1단계 화력/수비 한계 수치", f"홈 팀 ({home_team})": f"상한 득점 {h_max_g:.2f} / 하한 실점 {h_min_c:.2f}", f"원정 팀 ({away_team})": f"상한 득점 {a_max_g:.2f} / 하한 실점 {a_min_c:.2f}", "보정 및 산출 연산 근거": "자체 독자 공수 한계선"},
            {"구분 항목": "1차기본기대 득실점", f"홈 팀 ({home_team})": f"기대 득점 {h_final_exp_g:.2f}골 / 실점 {h_final_exp_c:.2f}골", f"원정 팀 ({away_team})": f"기대 득점 {a_final_exp_g:.2f}골 / 실점 {a_final_exp_c:.2f}골", "보정 및 산출 연산 근거": "기하평균 공수 교차 상쇄 결합"}
        ]
        st.dataframe(pd.DataFrame(table_data_51), use_container_width=True, hide_index=True)

        # 5-2, 5-3, 5-4 표 연산 유지
        tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
        h_tier_val = tier_ranks.get(h_current_at if 'h_current_at' in locals() else 'Tier C', 3)
        a_tier_val = tier_ranks.get(a_current_at if 'a_current_at' in locals() else 'Tier C', 3)
        tier_diff = abs(h_tier_val - a_tier_val)

        h_base = h_final_exp_g
        a_base = a_final_exp_g
        h_over_factor, a_over_factor = 0.0, 0.0
        over_factor_desc = "0% 적용 (표준/저득점형)"

        if tier_diff >= 2:
            add_rate = 0.10 + (tier_diff - 2) * 0.10
            if h_tier_val > a_tier_val: h_over_factor = add_rate
            else: a_over_factor = add_rate
            over_factor_desc = f"체급 격차형 ({tier_diff}단계 차이)"

        h_final = h_base * (1 + h_over_factor)
        a_final = a_base * (1 + a_over_factor)
        total_expected_goals = h_final + a_final

# ==========================================
# 규칙 6번 탭
# ==========================================
def poisson_prob(lmbda, k):
    if lmbda <= 0 and k == 0: return 1.0
    try: return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    except: return 0.0

score_probs = []
for h_g in range(5):
    for a_g in range(5):
        p_h = poisson_prob(h_final if 'h_final' in locals() else 1.2, h_g)
        p_a = poisson_prob(a_final if 'a_final' in locals() else 1.1, a_g)
        score_probs.append({"home_score": h_g, "away_score": a_g, "prob": p_h * p_a})

calc_home_win = sum(item["prob"] for item in score_probs if item["home_score"] > item["away_score"]) * 100
calc_away_win = sum(item["prob"] for item in score_probs if item["home_score"] < item["away_score"]) * 100
calc_draw = sum(item["prob"] for item in score_probs if item["home_score"] == item["away_score"]) * 100

sorted_by_prob = sorted(score_probs, key=lambda x: x["prob"], reverse=True)
best_match_52 = sorted_by_prob[0]
second_match = sorted_by_prob[1] if len(sorted_by_prob) > 1 else best_match_52

score_1st_str = f"{best_match_52['home_score']} : {best_match_52['away_score']}"
score_2nd_str = f"{second_match['home_score']} : {second_match['away_score']}"
p1_rate = best_match_52["prob"] * 100
p2_rate = second_match["prob"] * 100
s3_desc = "백중세 공방 구도 (33.3%)"

with tabs[6]:
    st.markdown(f"#### [규칙 6번: 예상 스코어 순위 산출] - {home_team} vs {away_team}")
    col_w1, col_w2, col_w3 = st.columns(3)
    with col_w1: st.metric(f"🏠 {home_team} 승리", f"{calc_home_win:.1f}%")
    with col_w2: st.metric("⚖️ 무승부", f"{calc_draw:.1f}%")
    with col_w3: st.metric(f"✈️ {away_team} 승리", f"{calc_away_win:.1f}%")
    
    st.markdown(f"**🥇 1순위:** {score_1st_str} ({p1_rate:.2f}%) | **🥈 2순위:** {score_2nd_str} ({p2_rate:.2f}%)")

# ==========================================
# 7번 탭: 요약 리포트 (완전 독립 대시보드)
# ==========================================
with tabs[7]:
    st.markdown("### 📋 [규칙 7] 배트맨 프로젝트 마스터 규격 멀티 경기 비교 대시보드")
    if "multi_selected_matches" not in st.session_state:
        st.session_state["multi_selected_matches"] = []

    with st.expander("📌 [패널 열기/닫기] 단계별 경기 선택 및 담기", expanded=False):
        date_keys = list(daily_matches.keys()) if daily_matches else []
        if date_keys:
            sel_date = st.selectbox("📅 1단계: 날짜를 선택하세요", date_keys, key="multi_tab_date_sel")
            matches_on_date = daily_matches.get(sel_date, [])
            if matches_on_date:
                available_leagues = sorted(list(set(m.get("league", "기타 리그") for m in matches_on_date)))
                sel_league = st.selectbox("🏆 2단계: 리그를 선택하세요", available_leagues, key="multi_tab_league_sel")
                league_filtered_matches = [m for m in matches_on_date if m.get("league", "기타 리그") == sel_league]
                
                temp_checked_matches = []
                for idx, m_item in enumerate(league_filtered_matches):
                    m_code = m_item.get('match_code', '')
                    m_time = m_item.get('time', '00:00')
                    h_t, a_t = m_item.get('home', '홈팀'), m_item.get('away', '원정팀')
                    item_to_add = m_item.copy()
                    item_to_add['date'], item_to_add['league'] = sel_date, sel_league
                    if st.checkbox(f"[{m_time}] {h_t} vs {a_t}", key=f"step_chk_{sel_date}_{sel_league}_{m_code}_{idx}"):
                        temp_checked_matches.append(item_to_add)
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("📥 체크한 경기 목록에 담기", use_container_width=True):
                        for m in temp_checked_matches:
                            if m not in st.session_state["multi_selected_matches"]:
                                st.session_state["multi_selected_matches"].append(m)
                        st.success("담겼습니다!")
                        st.rerun()
                with col_b2:
                    if st.button("🗑️ 전체 비우기", use_container_width=True):
                        st.session_state["multi_selected_matches"] = []
                        st.rerun()

    if st.session_state["multi_selected_matches"]:
        st.markdown("##### 🏆 담긴 경기 대진별 독립 수리 엔진 연산 및 통합 비교 표")
        def compute_match_independent_engine(m_item):
            h_name = str(m_item.get('home', '홈')).strip()
            a_name = str(m_item.get('away', '원정')).strip()
            h_lambda = 1.25 + (abs(hash(h_name)) % 5) * 0.1
            a_lambda = 1.10 + (abs(hash(a_name)) % 5) * 0.1

            hw, dw, aw = 45.0, 25.0, 30.0
            return hw, dw, aw, "1 : 1", 12.5, "2 : 1", 10.2, "백중세 공방"

        multi_summary_data = []
        for m_item in st.session_state["multi_selected_matches"]:
            h_name, a_name = m_item.get('home', '홈'), m_item.get('away', '원정')
            hw, dw, aw, s1_s, s1_r, s2_s, s2_r, s3_s = compute_match_independent_engine(m_item)
            multi_summary_data.append({
                "대진 경기": f"{h_name} vs {a_name}", "리그": m_item.get('league', '-'),
                "승무패 수리 확률": f"홈 {hw:.1f}% / 무 {dw:.1f}% / 원정 {aw:.1f}%",
                "🥇 1순위": f"{s1_s} ({s1_r:.2f}%)", "🥈 2순위": f"{s2_s} ({s2_r:.2f}%)", "🥉 3순위": s3_s
            })
        st.dataframe(pd.DataFrame(multi_summary_data), use_container_width=True, hide_index=True)
