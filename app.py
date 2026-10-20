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

# 💡 [신규 추가] V5 결장자 및 선수 스탯 딕셔너리 독립 전용 로딩 함수
@st.cache_data(ttl=10)
def load_v5_match_details():
    v5_file = "match_details_v5.json"
    if os.path.exists(v5_file):
        try:
            with open(v5_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                return file_data.get("lineup_details", {})
        except Exception:
            pass
    return {}

# 💡 [신규 추가] V5-1 구단 전체 선수단 명단 딕셔너리 독립 전용 로딩 함수
@st.cache_data(ttl=10)
def load_v5_1_match_details():
    v5_1_file = "match_details_v5-1.json"
    if os.path.exists(v5_1_file):
        try:
            with open(v5_1_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                return file_data.get("squad_details", {})
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
v5_details_dict = load_v5_match_details()      # 👈 V5 독립 딕셔너리 장착 완료
v5_1_details_dict = load_v5_1_match_details()  # 👈 V5-1 독립 딕셔너리 장착 완료


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

# 💡 상단 메인 분석은 사이드바 선택(selected_match)을 100% 독립적으로 따르도록 오버라이드 로직 제거 완료

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
    
    if has_detailed_data:
        meta_details = detailed_info.get("meta_details", {})
        rankings_raw = meta_details.get("rankings", [])
        
        # country.json 로드 함수
        @st.cache_data
        def load_country_data():
            import json, os
            if os.path.exists("country.json"):
                with open("country.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}

        country_data = load_country_data()

# 💡 [국가 및 등급 정밀 대조 함수 - '리그 1' 글자 겹치기 오탐지 완벽 해결 및 country_code 연동 규격]
        def resolve_country_and_grade_from_rankings(rank_val, team_val, current_league_name=""):
            grades = country_data.get("grades", {})
            rank_str = str(rank_val).strip()
            team_str = str(team_val).strip().lower()
            clean_league = str(current_league_name).strip().replace(" ", "").lower()

            # 💡 [최우선 방어] 리그명이나 랭크 코드에 'K리그' 또는 'KOR'이 포함되어 있으면 프랑스('리그 1') 오탐지를 원천 차단하고 대한민국(KOR) 고정
            if "k리그" in clean_league or "kor" in rank_str.upper():
                for c in grades.get("C", []):
                    if c.get("country_code") == "KOR":
                        return c.get("country_code", "KOR"), rank_str, c.get("grade", "C"), c.get("attack_bonus", "+9%"), c.get("defense_bonus", "-9%")
                return "KOR", rank_str, "C", "+9%", "-9%"

            # 2. 띄어쓰기나 하이픈(-) 앞쪽의 국가/리그 코드 추출 (예: "NGA PR-1" -> "NGA")
            extracted_code = ""
            if rank_str and rank_str != "-":
                token = re.split(r'[\s\-]+', rank_str)[0].strip().upper()
                if token and not token.isdigit():
                    extracted_code = token

            # 3. 추출된 코드가 있으면 country.json의 국가 코드와 대조 (country_code 기준)
            if extracted_code:
                for grade_key, countries in grades.items():
                    if grade_key == "F":
                        continue
                    if isinstance(countries, list):
                        for c in countries:
                            c_code = str(c.get("country_code", "")).strip().upper()
                            leagues_list = [str(l).strip().upper() for l in c.get("leagues", [])]
                            if c_code == extracted_code or any(extracted_code == l.split()[0] for l in leagues_list if l):
                                return c.get("country_code", "EXT"), rank_str, c.get("grade", "E"), c.get("attack_bonus", "+3%"), c.get("defense_bonus", "-3%")

            # 4. 일반 해외 리그명 대조 (프랑스 등)
            for grade_key, countries in grades.items():
                if grade_key == "F":
                    continue
                if isinstance(countries, list):
                    for c in countries:
                        kor_league = str(c.get("league_kor_name", "")).strip().replace(" ", "").lower()
                        c_name = str(c.get("name", "")).strip().lower()
                        
                        # 정확히 일치하거나 독립된 단어일 때만 매칭 허용 (글자 겹침 방지)
                        match_kor = kor_league and (kor_league == clean_league or f" {kor_league} " in f" {clean_league} ")
                        match_name = c_name and (c_name in clean_league or c_name in team_str)

                        if match_kor or match_name:
                            return c.get("country_code", "EXT"), rank_str, c.get("grade", "E"), c.get("attack_bonus", "+3%"), c.get("defense_bonus", "-3%")

            # 5. 매칭 실패 시 F등급 폴백 처리
            f_info = grades.get("F", {})
            return "EXT", rank_str if rank_str else "-", "F", f_info.get("attack_bonus", "0%"), f_info.get("defense_bonus", "0%")

        # ==========================================
        # 순위표 순회 및 홈/원정 등급 매핑 처리 영역
        # ==========================================
        if rankings_raw:
            rankings_list = []
            
            clean_home_target = str(home_team).strip().replace(" ", "")
            clean_away_target = str(away_team).strip().replace(" ", "")

            # 기본값 F등급 및 0% 세팅
            h_grade, h_atk_b, h_def_b = "F", "0%", "0%"
            a_grade, a_atk_b, a_def_b = "F", "0%", "0%"

            # 💡 [방어 1] 중복 매칭 방지용 플래그 장착
            found_home = False
            found_away = False

            for idx, r in enumerate(rankings_raw):
                team_name = str(r.get("team", "-"))
                rank_code_str = str(r.get("rank", ""))  
                
                matched_code, clean_rank_str, grade, atk_b, def_b = resolve_country_and_grade_from_rankings(rank_code_str, team_name, league_name)
                
                clean_row_team = team_name.strip().replace(" ", "")
                
                # 💡 [방어 2] 홈/원정 각각 최초 1회만 정확히 매칭하고 이후 덮어쓰기 원천 차단
                if not found_home and (clean_home_target in clean_row_team or clean_row_team in clean_home_target):
                    h_grade, h_atk_b, h_def_b = grade, atk_b, def_b
                    found_home = True
                elif not found_away and (clean_away_target in clean_row_team or clean_row_team in clean_away_target):
                    a_grade, a_atk_b, a_def_b = grade, atk_b, def_b
                    found_away = True

                rankings_list.append({
                    "No": idx + 1,
                    "리그순위": rank_code_str,
                    "팀": team_name,
                    "국가코드": matched_code,
                    "리그명": league_name,
                    "등급": grade,
                    "공격보정": atk_b,
                    "수비보정": def_b,
                    "경기": str(r.get("played", "0")), "승": str(r.get("win", "0")),
                    "무승부": str(r.get("draw", "0")), "패": str(r.get("loss", "0")),
                    "득점": str(r.get("goals_for", "0")), "실점": str(r.get("goals_against", "0")),
                    "득실": str(r.get("goal_diff", "0")), "승점": str(r.get("points", "0"))
                })

            # 💡 [방어 3] 세션 상태에 최종 확정 값 주입
            st.session_state["h_grade"] = h_grade
            st.session_state["h_atk_bonus"] = h_atk_b
            st.session_state["h_def_bonus"] = h_def_b

            st.session_state["a_grade"] = a_grade
            st.session_state["a_atk_bonus"] = a_atk_b
            st.session_state["a_def_bonus"] = a_def_b

            df_rankings = pd.DataFrame(rankings_list)
            st.dataframe(df_rankings[["리그순위", "팀", "국가코드", "리그명", "등급", "공격보정", "수비보정", "경기", "승", "무승부", "패", "득점", "실점", "득실", "승점"]], use_container_width=True, hide_index=True)
        else:
            st.session_state["h_grade"], st.session_state["h_atk_bonus"], st.session_state["h_def_bonus"] = "F", "0%", "0%"
            st.session_state["a_grade"], st.session_state["a_atk_bonus"], st.session_state["a_def_bonus"] = "F", "0%", "0%"
            st.info("💡 해당 경기에 수집된 순위 및 전적표 데이터(rankings)가 존재하지 않습니다. (가중치 0% 처리)")
    else:
        st.session_state["h_grade"], st.session_state["h_atk_bonus"], st.session_state["h_def_bonus"] = "F", "0%", "0%"
        st.session_state["a_grade"], st.session_state["a_atk_bonus"], st.session_state["a_def_bonus"] = "F", "0%", "0%"
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터가 아직 수집되지 않았습니다. (가중치 0% 처리)")
# ==========================================
# 💡 규칙 1번 탭 (v3 데이터 전용 단독 연동 및 공수 대칭 교차 보정 적용)
# ==========================================
with tabs[1]:
    st.markdown(f"#### [규칙 1번: 종합 최근 10경기 로그 및 A~E 등급별 공수 티어 산출] - {home_team} vs {away_team}")
    st.markdown("""
        <div class="step-box">
            <b>📌 규격 원칙 및 요약 설명:</b><br>
            • <b>전수 조사 및 LIFO 방식:</b> 홈/원정 통합 최근 공식 경기 10개를 최신순 역순(LIFO)으로 전수 조사하며, 골득실 평균을 산출하여 티어 산정표의 티어를 각 양팀에 부여합니다.<br>
            • <b>친선 경기 전면 배제:</b> 최근 경기 표본에서 모든 친선 경기를 영구 배제하며, 오직 공식 경기만을 채택합니다.<br>
            • <b>공수 대칭 교차 특수 룰:</b> 팀의 공수 판정 체급(A/E)과 상대 공수 티어의 교차 상성에 따라 득실점이 50% 할인(-50%) 또는 50% 할증(+50%)되어 대칭 반영됩니다.
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

    # v3 전용 딕셔너리에서 현재 대진 데이터 안전 발췌
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

    # 1차 임시 산출 결과로 발동 여부(is_triggered) 선행 판단 헬퍼 함수
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

    def local_make_df(matches, tname, def_gpg, def_cpg, def_rec, my_at="Tier C", my_de="Tier C"):
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
                        mm = parts[0].zfill(2)
                        dd = parts[1].zfill(2)
                        yyyy = parts[2]
                        formatted_mtime = f"{yyyy}.{mm}.{dd}"
            except Exception:
                formatted_mtime = mtime

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
                if tname in t1:
                    sc, cc = s1, s2
                elif tname in t2:
                    sc, cc = s2, s1
                else:
                    sc, cc = s1, s2
            else:
                sc, cc = s1, s2
                
            raw_scored_total += sc
            raw_conceded_total += cc
            
            if sc > cc:
                res = "승"
                w += 1
            elif sc == cc:
                res = "무"
                d += 1
            else:
                res = "패"
                l += 1
                
            tier_str = "정보 없음"
            mult_gf = 1.0
            mult_ga = 1.0
            rule_desc = "유지"
            
            tier_info = m.get("opponent_tier_info", "")
            if tier_info and "/" in tier_info:
                try:
                    oa, od = map(float, tier_info.split("/"))
                    at_name = atk_tier_nm(oa)
                    df_name = def_tier_nm(od)
                    tier_str = f"공격 {at_name} ({oa:.2f}) / 방어 {df_name} ({od:.2f})"
                    
                    # 💡 [마스터 규격] 공수 대칭 교차 보정 (할인 / 할증)
                    # 1. 내 공격 관점 교차 보정
                    if my_at == "Tier A" and df_name == "Tier E":
                        mult_gf = 0.5
                        rule_desc = "공격 A vs 상대수비 E (득점 50% 할인)"
                    elif my_at == "Tier E" and df_name == "Tier A":
                        mult_gf = 1.5
                        rule_desc = "공격 E vs 상대수비 A (득점 50% 할증)"
                        
                    # 2. 내 방어 관점 교차 보정
                    if my_de == "Tier A" and at_name == "Tier E":
                        mult_ga = 1.5
                        rule_desc = (" / " if mult_gf != 1.0 else "") + "방어 A vs 상대공격 E (실점 50% 할증)"
                    elif my_de == "Tier E" and at_name == "Tier A":
                        mult_ga = 0.5
                        rule_desc = (" / " if mult_gf != 1.0 else "") + "방어 E vs 상대공격 A (실점 50% 할인)"
                        
                    if mult_gf != 1.0 or mult_ga != 1.0:
                        tier_str += f" ⚠️ ({rule_desc})"
                    else:
                        tier_str += " (보정 없음 / 유지)"
                except:
                    pass
                    
            app_sc = sc * mult_gf
            app_cc = cc * mult_ga
            eff_scored += app_sc
            eff_conceded += app_cc
            
            seq = f"최신 ({idx+1})" if idx == 0 else str(idx+1)
            score_display = f"{s1} : {s2}" + (f" (보정 득실: {app_sc:.1f} : {app_cc:.1f})" if (mult_gf != 1.0 or mult_ga != 1.0) else " (유지)")
            
            rows.append({
                "LIFO 순서": seq,
                "경기 일시": formatted_mtime,
                "대회": translate_tournament_code(league),
                "대진": teams,
                "스코어": score_display,
                "결과": res,
                "상대 공수 티어": tier_str
            })
            
        cnt = len(matches)
        gpg = round(eff_scored / cnt, 2) if cnt > 0 else def_gpg
        cpg = round(eff_conceded / cnt, 2) if cnt > 0 else def_cpg
        rec = f"{cnt}전 {w}승 {d}무 {l}패" if cnt > 0 else def_rec
        
        return pd.DataFrame(rows), gpg, cpg, rec, raw_scored_total, raw_conceded_total

    # 1차 예비 산출로 홈/원정 기본 체급 파악 후 대칭 교차 보정 적용 산출
    h_df_pre, h_gpg_pre, h_cpg_pre, h_rec_pre, _, _ = local_make_df(h_matches, h_name, h_gpg_base, h_cpg_base, h_rec_base, "Tier C", "Tier C")
    h_at_pre, _ = atk_tier(h_gpg_pre)
    h_de_pre, _ = def_tier(h_cpg_pre)

    a_df_pre, a_gpg_pre, a_cpg_pre, a_rec_pre, _, _ = local_make_df(a_matches, a_name, a_gpg_base, a_cpg_base, a_rec_base, "Tier C", "Tier C")
    a_at_pre, _ = atk_tier(a_gpg_pre)
    a_de_pre, _ = def_tier(a_cpg_pre)

    # 최종 확정 산출 (각 팀의 확정 체급인 h_at_pre, h_de_pre 반영)
    h_df, h_gpg, h_cpg, h_rec, h_raw_s, h_raw_c = local_make_df(h_matches, h_name, h_gpg_base, h_cpg_base, h_rec_base, h_at_pre, h_de_pre)
    a_df, a_gpg, a_cpg, a_rec, a_raw_s, a_raw_c = local_make_df(a_matches, a_name, a_gpg_base, a_cpg_base, a_rec_base, a_at_pre, a_de_pre)

    h_at, h_atw = atk_tier(h_gpg)
    h_de, h_dew = def_tier(h_cpg)
    a_at, a_atw = atk_tier(a_gpg)
    a_de, a_dew = def_tier(a_cpg)

    h_goal_diff = h_raw_s - h_raw_c
    a_goal_diff = a_raw_s - a_raw_c

    # 홈 팀 1단계 출력
    st.markdown(f"##### 홈 팀 ({h_name}) 최근 전적 분석 로그 ")
    if not h_df.empty:
        st.dataframe(h_df, use_container_width=True, hide_index=True)
    else:
        st.info("📋 개별 경기 상세 데이터 없음")
        
    st.markdown(f"""<div class="calc-box">
        <b>{h_name} 규칙 1번 상세 산출 내역</b><br>
        • 최근 전적: <b>{h_rec}</b> (총 득점: <b>{h_raw_s:.1f}골</b> / 총 실점: <b>{h_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if h_goal_diff >= 0 else '#c62828'};">{h_goal_diff:+.1f}</b>)<br>
        • 보정 평균 득점: <b>{h_gpg:.2f}골/경기</b> / 보정 평균 실점: <b>{h_cpg:.2f}골/경기</b><br>
        • 공격 티어: <b>{h_at} ({h_atw})</b> | 방어 티어: <b>{h_de} ({h_dew})</b> | 공수 교차 보정 적용 완료
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # 원정 팀 1단계 출력
    st.markdown(f"##### 원정 팀 ({a_name}) 최근 전적 분석 로그 ")
    if not a_df.empty:
        st.dataframe(a_df, use_container_width=True, hide_index=True)
    else:
        st.info("📋 개별 경기 상세 데이터 없음")
        
    st.markdown(f"""<div class="calc-box">
        <b>{a_name} 규칙 1번 상세 산출 내역</b><br>
        • 최근 전적: <b>{a_rec}</b> (총 득점: <b>{a_raw_s:.1f}골</b> / 총 실점: <b>{a_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if a_goal_diff >= 0 else '#c62828'};">{a_goal_diff:+.1f}</b>)<br>
        • 보정 평균 득점: <b>{a_gpg:.2f}골/경기</b> / 보정 평균 실점: <b>{a_cpg:.2f}골/경기</b><br>
        • 공격 티어: <b>{a_at} ({a_atw})</b> | 방어 티어: <b>{a_de} ({a_dew})</b> | 공수 교차 보정 적용 완료
    </div>""", unsafe_allow_html=True)

# ==============================================================================
# 💡 규칙 2번 탭 (0단계 구장 판별 연동 및 V3/V5 최근 전적 풀 기반 원정 폼 필터링 적용)
# ==============================================================================
with tabs[2]:
    st.markdown(f"#### [규칙 2번: 구장별 Shift 검증 및 티어 보정] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
    <b>📌 규격 원칙 및 요약 설명:</b><br>
    • <b>구장별 전적(Stadium Form) 분석:</b> 일반 홈경기일 때는 홈팀의 홈 경기 구장 데이터를 사용하며, 중립경기일 때는 최근 전적 풀(최대 20경기)에서 홈팀의 원정/중립 성격 경기 기록을 필터링하여 안전하게 산출합니다. 원정팀은 항상 기본 원정 폼을 고정 사용합니다.<br>
    • <b>0단계 구장 판정 연동:</b> 홈구장 일치 여부에 따라 홈경기(초록색) 또는 중립경기(빨간색) 상태를 명시하고 원정 데이터를 분기 적용합니다.<br>
    • <b>공수 대칭 교차 특수 룰:</b> 구장별 전적 환경에서도 팀의 체급(A/E)과 상대 공수 티어의 교차 상성에 따라 득실점이 50% 할인 또는 할증 반영됩니다.
    </div>
    """, unsafe_allow_html=True)

    tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}

    if has_detailed_data:
        head_meta = detailed_info.get("head_info", {}) if 'detailed_info' in locals() else {}
        venue_val = str(head_meta.get("stadium", "")) or str(head_meta.get("venue", ""))
        home_stadium_val = str(head_meta.get("home_stadium", ""))
        
        is_neutral_venue = False
        if venue_val and home_stadium_val:
            if venue_val.strip().lower() != home_stadium_val.strip().lower():
                is_neutral_venue = True

        # 1. 홈팀 전적 추출 (중립 경기일 경우 최근 전적 풀에서 원정 성격 경기 필터링)
        s_home_matches = []
        if is_neutral_venue:
            # 최근 20경기 규모의 전체 최근 전적 풀(h_matches 등) 확보
            recent_all_pool = []
            if 'h_matches' in locals() and h_matches:
                recent_all_pool = h_matches
            elif stadium_form and "recent_matches" in stadium_form:
                recent_all_pool = stadium_form.get("recent_matches", [])

            neutral_home_away_matches = []
            for m in recent_all_pool:
                teams_str = str(m.get("teams", ""))
                # 대진 문자열을 분석하여 홈팀(h_name)이 원정 쪽이거나 포함되지 않은 경기 선별
                if " vs " in teams_str:
                    t_parts = [p.strip() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2 and h_name not in t_parts[0]:
                        neutral_home_away_matches.append(m)
                elif m.get("location") == "원정" or m.get("venue_type") == "away":
                    neutral_home_away_matches.append(m)
            
            # 만약 필터링된 결과가 부족하면 기본 away_matches 풀에서 보완
            if not neutral_home_away_matches:
                neutral_home_away_matches = stadium_form.get("away_matches", [])

            s_home_matches = neutral_home_away_matches[:10]
        else:
            s_home_matches = stadium_form.get("home_matches", [])[:10]

        # 2. 원정팀 전적 추출
        s_away_matches = stadium_form.get("away_matches", [])[:10]

        # 기본 평균 득실 산출 헬퍼
        def get_base_gpg_cpg(matches, tname):
            if not matches: return 0.0, 0.0
            s_sum, c_sum = 0.0, 0.0
            for m in matches:
                scores = m.get("ft_scores", ["0", "0"])
                try: s1, s2 = int(scores[0]), int(scores[1])
                except: s1 = s2 = 0
                teams = m.get("teams", "")
                sc, cc = s1, s2
                if " vs " in teams:
                    t1, t2 = teams.split(" vs ")
                    if tname in t1: sc, cc = s1, s2
                    elif tname in t2: sc, cc = s2, s1
                s_sum += sc
                c_sum += cc
            cnt = len(matches)
            return (s_sum / cnt if cnt > 0 else 0.0), (c_sum / cnt if cnt > 0 else 0.0)

        s_h_gpg_base, s_h_cpg_base = get_base_gpg_cpg(s_home_matches, h_name)
        s_a_gpg_base, s_a_cpg_base = get_base_gpg_cpg(s_away_matches, a_name)

        # 1차 예비 산출로 구장별 체급(공수 A/E 등) 파악
        _, pre_sh_gpg, pre_sh_cpg, _, _, _ = local_make_df(s_home_matches, h_name, s_h_gpg_base, s_h_cpg_base, "0전", "Tier C", "Tier C")
        _, pre_sa_gpg, pre_sa_cpg, _, _, _ = local_make_df(s_away_matches, a_name, s_a_gpg_base, s_a_cpg_base, "0전", "Tier C", "Tier C")
        
        pre_sh_at = atk_tier_nm(pre_sh_gpg)
        pre_sh_de = def_tier_nm(pre_sh_cpg)
        pre_sa_at = atk_tier_nm(pre_sa_gpg)
        pre_sa_de = def_tier_nm(pre_sa_cpg)

        # 구장별 폼 대칭 교차 보정 적용 최종 산출
        s_h_df, s_h_gpg, s_h_cpg, s_h_rec, s_h_raw_s, s_h_raw_c = local_make_df(s_home_matches, h_name, 0.0, 0.0, "0전 0승 0무 0패", pre_sh_at, pre_sh_de)
        s_a_df, s_a_gpg, s_a_cpg, s_a_rec, s_a_raw_s, s_a_raw_c = local_make_df(s_away_matches, a_name, 0.0, 0.0, "0전 0승 0무 0패", pre_sa_at, pre_sa_de)

        s_h_at, s_h_atw = atk_tier(s_h_gpg)
        s_h_de, s_h_dew = def_tier(s_h_cpg)
        s_a_at, s_a_atw = atk_tier(s_a_gpg)
        s_a_de, s_a_dew = def_tier(s_a_cpg)

        base_h_at = h_at if 'h_at' in locals() else "Tier C"
        base_h_de = h_de if 'h_de' in locals() else "Tier C"
        base_a_at = a_at if 'a_at' in locals() else "Tier C"
        base_a_de = a_de if 'a_de' in locals() else "Tier C"

        def get_tier_colored_html(base_tier, stadium_tier):
            b_val = tier_ranks.get(base_tier, 3)
            s_val = tier_ranks.get(stadium_tier, 3)
            if s_val > b_val:
                return f"<span style='color: #2e7d32; font-weight: bold;'>{stadium_tier} 📈</span>"
            elif s_val < b_val:
                return f"<span style='color: #c62828; font-weight: bold;'>{stadium_tier} 📉</span>"
            else:
                return f"<span>{stadium_tier}</span>"

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

        venue_status_badge = (
            "<span style='color: #c62828; font-weight: bold;'> (중립경기)</span>" 
            if is_neutral_venue 
            else "<span style='color: #2e7d32; font-weight: bold;'> (홈경기)</span>"
        )

        st.markdown(f"##### 홈 팀 ({h_name}) 구장별 전적 및 티어 변동 검증{venue_status_badge}", unsafe_allow_html=True)
        if not s_h_df.empty:
            st.dataframe(s_h_df, use_container_width=True, hide_index=True)
        else:
            st.info("📋 구장별 상세 전적 데이터 없음")

        st.markdown(f"""
        <div class="calc-box">
        <b>{h_name} 규칙 2번(구장별) Shift 보정 산출 내역</b><br>
        • 최근 전적: <b>{s_h_rec}</b> (총 득점: <b>{s_h_raw_s:.1f}골</b> / 총 실점: <b>{s_h_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if s_h_diff >= 0 else '#c62828'};">{s_h_diff:+.1f}</b>)<br>
        • 보정 평균 득점: <b>{s_h_gpg:.2f}골/경기</b> / 보정 평균 실점: <b>{s_h_cpg:.2f}골/경기</b><br>
        • 1단계 종합 체급: 공격 <b>{base_h_at}</b> / 방어 <b>{base_h_de}</b> &nbsp;|&nbsp; 구장 환경 체급: 공격 <b>{h_atk_color_str}</b> / 방어 <b>{h_def_color_str}</b><br>
        • <b>적용된 구장 Shift 보정치:</b> 공격 <b>{h_atk_shift_str}</b> / 방어 <b>{h_def_shift_str}</b>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown(f"##### 원정 팀 ({a_name}) 구장별 전적 및 티어 변동 검증")
        if not s_a_df.empty:
            st.dataframe(s_a_df, use_container_width=True, hide_index=True)
        else:
            st.info("📋 구장별 상세 전적 데이터 없음")

        st.markdown(f"""
        <div class="calc-box">
        <b>{a_name} 규칙 2번(구장별) Shift 보정 산출 내역</b><br>
        • 최근 전적: <b>{s_a_rec}</b> (총 득점: <b>{s_a_raw_s:.1f}골</b> / 총 실점: <b>{s_a_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if s_a_diff >= 0 else '#c62828'};">{s_a_diff:+.1f}</b>)<br>
        • 보정 평균 득점: <b>{s_a_gpg:.2f}골/경기</b> / 보정 평균 실점: <b>{s_a_cpg:.2f}골/경기</b><br>
        • 1단계 종합 체급: 공격 <b>{base_a_at}</b> / 방어 <b>{base_a_de}</b> &nbsp;|&nbsp; 구장 환경 체급: 공격 <b>{a_atk_color_str}</b> / 방어 <b>{a_def_color_str}</b><br>
        • <b>적용된 구장 Shift 보정치:</b> 공격 <b>{a_atk_shift_str}</b> / 방어 <b>{a_def_shift_str}</b>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터가 아직 수집되지 않았습니다.")


# --- [3단계: 전력누수·피로 매트릭스] ---
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

# ==============================================================================
    # [기능 1] 선수 등급(A~D) 정량 판정 기준표 출력 (HTML 표 렌더링)
    # ==============================================================================
    st.markdown("##### 선수 등급(A~D) 정량 판정 기준표")
    html_table = """
    <style>
    .custom-table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; font-size: 14px; }
    .custom-table th, .custom-table td { border: 1px solid #e0e0e0; padding: 10px 12px; text-align: left; }
    .custom-table th { background-color: #f5f5f5; font-weight: bold; }
    </style>
    <table class="custom-table">
    <thead><tr><th>전력 등급</th><th>포지션</th><th>정량적 스펙 및 평가 기준</th><th>보정 비율 (D=0, 급당 +4%)</th></tr></thead>
    <tbody>
    <tr><td><b>A 등급</b></td><td>공격수 / 미드필더 / 수비수</td><td>• 팀 내 최상위 핵심 자원 (출전율 및 공격포인트/클린시트 최상위)</td><td><b>± 12.0%</b><br>(공격/방어 기본 가중치)</td></tr>
    <tr><td><b>B 등급</b></td><td>공격수 / 미드필더 / 수비수</td><td>• 주전급 핵심 로테이션 자원</td><td><b>± 8.0%</b></td></tr>
    <tr><td><b>C 등급</b></td><td>공격수 / 미드필더 / 수비수</td><td>• 준주전 및 로테이션 자원</td><td><b>± 4.0%</b></td></tr>
    <tr><td><b>D 등급</b></td><td>공용</td><td>• 백업 및 후보 자원 (결장 시 수치 변화 미비)</td><td><b>0.0%</b></td></tr>
    </tbody>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)

    # ==============================================================================
    # [연동 순서 1 & 2단계] 마스터 상세 딕셔너리에서 해당 경기 및 매치코드 확정
    # ==============================================================================
    target_match_code_str = str(match_code).strip()
    clean_target_home = str(home_team).strip().replace(" ", "").lower()
    clean_target_away = str(away_team).strip().replace(" ", "").lower()

    master_matched_info = None
    if target_match_code_str and target_match_code_str in all_details_dict:
        master_matched_info = all_details_dict[target_match_code_str]
    else:
        for k, v in all_details_dict.items():
            if not isinstance(v, dict): continue
            v_code = str(v.get("match_code", "")).strip()
            v_h = str(v.get("home", "")).strip().replace(" ", "").lower()
            v_a = str(v.get("away", "")).strip().replace(" ", "").lower()
            if v_code == target_match_code_str or (clean_target_home in v_h and clean_target_away in v_a):
                master_matched_info = v
                if v_code:
                    target_match_code_str = v_code
                break

    # ==============================================================================
    # [연동 순서 3단계] V5 결장자 탐색 및 필터링
    # ==============================================================================
    raw_home_absentees = []
    raw_away_absentees = []
    home_squad_pool = []
    away_squad_pool = []

    if master_matched_info:
        v5_lineup_dict = v5_details_dict.get("lineup_details", v5_details_dict)
        v5_match_data = {}
        for k, v in v5_lineup_dict.items():
            if not isinstance(v, dict): continue
            v_code = str(v.get("match_code", k)).strip()
            v_h = str(v.get("home", "")).strip().replace(" ", "").lower()
            v_a = str(v.get("away", "")).strip().replace(" ", "").lower()
            if v_code == target_match_code_str or (clean_target_home in v_h and clean_target_away in v_a):
                v5_match_data = v
                break

        if v5_match_data:
            data_home_name = str(v5_match_data.get("home", "")).strip().replace(" ", "").lower()
            if clean_target_home in data_home_name or data_home_name in clean_target_home:
                h_raw_list = v5_match_data.get("home_absentees", [])
                a_raw_list = v5_match_data.get("away_absentees", [])
            else:
                h_raw_list = v5_match_data.get("away_absentees", [])
                a_raw_list = v5_match_data.get("home_absentees", [])

            raw_home_absentees = [p for p in h_raw_list if str(p.get("status", "")).strip() in ["결장", "부상", "징계", "누수", "출전의심/기타"] and str(p.get("name", "")).strip()]
            raw_away_absentees = [p for p in a_raw_list if str(p.get("status", "")).strip() in ["결장", "부상", "징계", "누수", "출전의심/기타"] and str(p.get("name", "")).strip()]

        # ==============================================================================
        # [연동 순서 4단계] V5-1 스쿼드 풀 확보 (squad_details)
        # ==============================================================================
        v5_1_squad_dict = v5_1_details_dict.get("squad_details", v5_1_details_dict)
        v5_1_match_data = {}
        for k, v in v5_1_squad_dict.items():
            if not isinstance(v, dict): continue
            v_code = str(v.get("match_code", k)).strip()
            v_h = str(v.get("home", "")).strip().replace(" ", "").lower()
            v_a = str(v.get("away", "")).strip().replace(" ", "").lower()
            if v_code == target_match_code_str or (clean_target_home in v_h and clean_target_away in v_a):
                v5_1_match_data = v
                break

        if v5_1_match_data:
            data_squad_home = str(v5_1_match_data.get("home", "")).strip().replace(" ", "").lower()
            if clean_target_home in data_squad_home or data_squad_home in clean_target_home:
                home_squad_pool = v5_1_match_data.get("home_squad", [])
                away_squad_pool = v5_1_match_data.get("away_squad", [])
            else:
                home_squad_pool = v5_1_match_data.get("away_squad", [])
                away_squad_pool = v5_1_match_data.get("home_squad", [])

    # ==============================================================================
    # [기능 3] 깔끔한 정제 규격 적용 조립 함수
    # ==============================================================================
    def build_clean_squad_dataframe(absentees_list, squad_list, team_label):
        if not absentees_list:
            df_empty = pd.DataFrame({
                "선수 실명": ["-", "[총합]"],
                "포지션": ["-", "-"],
                "변동 유형": ["-", "-"],
                "핵심 스펙 (평점·득점·도움 등)": ["특이 전력 누수/가산 없음", f"{team_label} 최종 가중치"],
                "출전 시간": ["-", "-"],
                "등급": ["-", "-"],
                "공격 보정": ["0.0%", "0.0%"],
                "방어 보정": ["0.0%", "0.0%"],
                "비고": ["정상 스쿼드 가동", "최종 누적 보정치 (0%)"]
            })
            return df_empty, 0.0, 0.0
        
        # V5-1 스쿼드 맵 구축 (오직 1개의 정확한 position 필드만 추출)
        squad_pos_map = {}
        for p in squad_list:
            if not isinstance(p, dict): continue
            p_name = str(p.get("name", "")).strip()
            p_pos = str(p.get("position", "")).strip()
            if p_name and p_pos:
                squad_pos_map[p_name] = p_pos
                squad_pos_map[p_name.replace(" ", "")] = p_pos

        rows = []
        tot_atk, tot_def = 0.0, 0.0
        
        for item in absentees_list:
            p_name = str(item.get("name", "-")).strip()
            
            # 5-1 스쿼드에서 정확한 단일 포지션 매핑 (없으면 기본값)
            p_pos = squad_pos_map.get(p_name, squad_pos_map.get(p_name.replace(" ", ""), "미드필더"))
            if not p_pos:
                p_pos = "미드필더"

            p_type = item.get("status", "결장")
            stats_dict = item.get("stats", {})
            
            # 💡 [요구사항 반영] 불필요한 문장 없이 important_stats에서 0이 아닌 유효 항목만 깔끔하게 조합
            imp_stats = stats_dict.get("important_stats", {})
            stat_parts = []
            for k, val in imp_stats.items():
                val_str = str(val).strip()
                # 0이거나 빈 값은 출력 생략 (단, 경기나 출전시간은 기본 표기 가능)
                if val_str and val_str != "0" and val_str != "0(0)":
                    stat_parts.append(f"{k}: {val_str}")
            
            if stat_parts:
                p_stats_str = " | ".join(stat_parts)
            else:
                # 데이터가 부족할 경우 방어용으로 평균 플레이타임(avg_play_time) 표기
                avg_time = stats_dict.get("avg_play_time", 0.0)
                p_stats_str = f"평균 플레이타임: {avg_time}분" if avg_time > 0 else "출전 기록 없음"

            total_time = stats_dict.get("total_play_time", 0)
            p_time_str = f"출전시간: {total_time}분" if total_time > 0 else "-"
            
            # 등급 및 가중치 산출
            raw_grade = str(stats_dict.get("grade", item.get("grade", "C"))).strip().upper()
            if "A" in raw_grade:
                p_grade = "A 등급"
                rate = 12.0
            elif "B" in raw_grade:
                p_grade = "B 등급"
                rate = 8.0
            elif "C" in raw_grade:
                p_grade = "C 등급"
                rate = 4.0
            else:
                p_grade = "D 등급"
                rate = 0.0

            p_memo = f"시즌 {stats_dict.get('matches_played', 0)}경기 출전 ({p_grade})"
            
            is_attacker = any(k in p_pos for k in ["공격수", "미드필더", "FW", "MF"])
            is_defender = any(k in p_pos for k in ["수비수", "골키퍼", "DF", "GK"])

            if p_type in ["결장", "부상", "징계", "누수", "출전의심/기타"]:
                if is_attacker:
                    atk_v = -rate
                    def_v = rate / 2.0
                elif is_defender:
                    atk_v = -rate / 2.0
                    def_v = rate
                else:
                    atk_v = -rate
                    def_v = rate / 2.0
            else:
                if is_attacker:
                    atk_v = rate
                    def_v = -rate / 2.0
                elif is_defender:
                    atk_v = rate / 2.0
                    def_v = -rate
                else:
                    atk_v = rate
                    def_v = -rate / 2.0

            tot_atk += atk_v
            tot_def += def_v
            rows.append({
                "선수 실명": p_name, 
                "포지션": p_pos, 
                "변동 유형": p_type, 
                "핵심 스펙 (평점·득점·도움 등)": p_stats_str, 
                "출전 시간": p_time_str, 
                "등급": p_grade,
                "공격 보정": f"{atk_v:+.1f}%", 
                "방어 보정": f"{def_v:+.1f}%", 
                "비고": "적용 완료"
            })
        
        rows.append({
            "선수 실명": "[총합]", "포지션": "-", "변동 유형": "-", "핵심 스펙 (평점·득점·도움 등)": f"{team_label} 최종 가중치",
            "출전 시간": "-", "등급": "-", "공격 보정": f"{tot_atk:+.1f}%", "방어 보정": f"{tot_def:+.1f}%", "비고": "최종 누적 보정치"
        })
        return pd.DataFrame(rows), tot_atk, tot_def

    # ==============================================================================
    # [기능 4] 홈/원정팀 최종 표(DataFrame) 출력
    # ==============================================================================
    st.markdown(f"##### 3-1: 홈 구단 - {home_team} 선수 전력 변동")
    if not raw_home_absentees:
        st.info(f"💡 [{home_team}] 해당 경기에 수집된 선수 전력 변동(결장자) 데이터가 없습니다. (정상 스쿼드 가동 가정)")
    table_3_1_home, h_r31_atk_val, h_r31_def_val = build_clean_squad_dataframe(raw_home_absentees, home_squad_pool, home_team)
    st.dataframe(table_3_1_home, use_container_width=True, hide_index=True)

    st.markdown(f"##### 3-1: 원정 구단 - {away_team} 선수 전력 변동")
    if not raw_away_absentees:
        st.info(f"💡 [{away_team}] 해당 경기에 수집된 선수 전력 변동(결장자) 데이터가 없습니다. (정상 스쿼드 가동 가정)")
    table_3_1_away, a_r31_atk_val, a_r31_def_val = build_clean_squad_dataframe(raw_away_absentees, away_squad_pool, away_team)
    st.dataframe(table_3_1_away, use_container_width=True, hide_index=True)

    st.markdown("---")

    
    # ==========================================
    # 3-2번 영역: 일정 이동 피로도 및 중요도 타임라인 & 팀별 리그 순위표 연동 (최적화 버전)
    # ==========================================
    st.markdown(f"##### [규칙 3-2번: 일정 이동피로도 및 일정중요도 판단] - {home_team} vs {away_team}")

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
                    label_mapping = {
                        "UEFA CL qualifying": "UEFA 챔피언스리그 진출권",
                        "UEFA EL qualifying": "UEFA 유로파리그 진출권",
                        "UEFA ECL qualifying": "UEFA 컨퍼런스리그 진출권",
                        "UEFA ECL offs": "컨퍼런스 플레이오프",
                        "승격팀": "직행 승격권",
                        "승격 플레이오프": "승격 플레이오프권",
                        "강등 플레이오프": "강등 플레이오프권",
                        "강등팀": "강등권",
                        "Championship Playoff": "우승 플레이오프",
                        "일반": "일반 리그"
                    }
                    kor_label = label_mapping.get(raw_label, raw_label)
                    matched_standings.append({
                        "league_name": league_name,
                        "rank": str(row.get("rank", "-")),
                        "team": row.get("team", target_team_name),
                        "tag_label": kor_label,
                        "경기수": str(row.get("경기수", "0")),
                        "승": str(row.get("승", "0")),
                        "무": str(row.get("무", "0")),
                        "패": str(row.get("패", "0")),
                        "득실": str(row.get("득실", "0")),
                        "승점": str(row.get("승점", "-"))
                    })
        return matched_standings

    def determine_match_importance(standing_info_list, league_raw_name):
        league_str = str(league_raw_name)
        if any(k in league_str for k in ["친선", "CF", "탈락", "탈락확정", "강등확정"]):
            return "중요도하", -10.0, 10.0
        if not standing_info_list:
            return "중요도중", 5.0, -5.0
        
        # 💡 [핵심 수정] 현재 경기 대회명과 일치하는 소속 리그 라벨만 우선 매칭하여 엉뚱한 타 대회(자국 리그 등) 진출권 버프 오적용 방지
        for standing_info in standing_info_list:
            l_name = str(standing_info.get("league_name", ""))
            # 현재 경기 리그명(예: 유로파리그, 챔피언스리그, 분데스리가 등)과 순위표의 소속 리그명이 서로 연관/일치하는지 검사
            if l_name in league_str or league_str in l_name or any(k in league_str and k in l_name for k in ["챔피언스", "유로파", "컨퍼런스", "분데스리가", "프리미어", "라리가", "세리에", "리그"]):
                label = str(standing_info.get("tag_label", ""))
                if any(k in label for k in ["탈락", "탈락확정", "강등확정"]):
                    return "중요도하", -10.0, 10.0
                if any(k in label for k in ["진출권", "플레이오프", "승격", "우승", "qualifying", "play-offs", "Playoff"]) or any(k in league_str for k in ["챔피언스", "유로파", "결승", "컵", "ACL", "CL"]):
                    return "중요도상", 15.0, -15.0

        # 만약 직접 일치하는 소속 리그 라벨이 없다면 기본 중요도(중) 부여
        return "중요도중", 5.0, -5.0

    home_standings_list = get_team_standing_info(home_team)
    away_standings_list = get_team_standing_info(away_team)

    standing_display_rows = []
    for hs in home_standings_list:
        standing_display_rows.append({
            "구분": f"홈 팀 ({home_team})", 
            "소속 리그": hs["league_name"], 
            "순위": f"{hs['rank']}위", 
            "중요도 라벨": hs["tag_label"], 
            "경기수": hs["경기수"], "승": hs["승"], "무": hs["무"], "패": hs["패"], "득실": hs["득실"], "승점": hs["승점"]
        })
    for as_info in away_standings_list:
        standing_display_rows.append({
            "구분": f"원정 팀 ({away_team})", 
            "소속 리그": as_info["league_name"], 
            "순위": f"{as_info['rank']}위", 
            "중요도 라벨": as_info["tag_label"], 
            "경기수": as_info["경기수"], "승": as_info["승"], "무": as_info["무"], "패": as_info["패"], "득실": as_info["득실"], "승점": as_info["승점"]
        })

    if standing_display_rows:
        st.markdown("##### 📌 양팀 실시간 리그 순위 및 중요도 판단 지표 (match_details_v4 연동)")
        st.dataframe(pd.DataFrame(standing_display_rows), use_container_width=True, hide_index=True)

    if has_detailed_data:
        meta_details = detailed_info.get("meta_details", {})
        fixtures_info = meta_details.get("fixtures", {})
        
        raw_home_fixes = list(fixtures_info.get("home", []))
        raw_away_fixes = list(fixtures_info.get("away", []))

        def parse_timeline_strictly_isolated(fix_list, recent_list, target_team_name, base_match_date, is_home_team, standing_info_list):
            base_dt = None
            try:
                base_clean = base_match_date.split(" ")[0].replace(".", "-").replace("/", "-")
                base_dt = datetime.strptime(base_clean[:10], "%Y-%m-%d")
            except Exception:
                base_dt = datetime.now()

            combined_pool = []
            seen_identifiers = set()
            for f in list(fix_list) + list(recent_list):
                m_t = str(f.get("match_time", ""))
                m_tm = str(f.get("teams", ""))
                uid = f"{m_t}_{m_tm}"
                if uid not in seen_identifiers:
                    combined_pool.append(f)
                    seen_identifiers.add(uid)

            past_arr, future_arr = [], []
            for f in combined_pool:
                m_time_str = str(f.get("match_time", ""))
                try:
                    c_clean = m_time_str.split(" ")[0].replace(".", "-").replace("/", "-")
                    c_dt = datetime.strptime(c_clean[:10], "%Y-%m-%d")
                except Exception:
                    continue
                if base_dt and c_dt:
                    d_diff = (c_dt - base_dt).days
                    if d_diff < 0:
                        past_arr.append((d_diff, f))
                    elif d_diff > 0:
                        future_arr.append((d_diff, f))

            past_arr = sorted(past_arr, key=lambda x: x[0], reverse=True)
            future_arr = sorted(future_arr, key=lambda x: x[0])

            def parse_single_fixture(f_item, d_diff_val):
                m_time_str = str(f_item.get("match_time", ""))
                league_raw_str = str(f_item.get("league", ""))
                league_title = translate_tournament_code(league_raw_str)
                teams_raw_str = str(f_item.get("teams", ""))
                
                cleaned_t = re.sub(r'\d{1,2}\.\d{1,2}\s+\d{4}', '', teams_raw_str)
                cleaned_t = re.sub(r'\d+\s*일|시작전', '', cleaned_t)
                p_list = [p.strip() for p in cleaned_t.split("vs") if p.strip()]
                t_clean_name = str(target_team_name).replace(" ", "")
                
                opponent_n, loc_kind = "상대미상", "원정"
                valid_t_list = [p for p in p_list if not re.search(r'\d', p) and p.replace(" ", "")]

                if len(valid_t_list) >= 2:
                    t_a, t_b = valid_t_list[0], valid_t_list[1]
                    if t_clean_name in t_a.replace(" ", ""):
                        opponent_n, loc_kind = t_b, "홈"
                    else:
                        opponent_n, loc_kind = t_a, "원정"
                elif len(valid_t_list) == 1:
                    if t_clean_name not in valid_t_list[0].replace(" ", ""):
                        opponent_n = valid_t_list[0]

                imp_lbl, _, _ = determine_match_importance(standing_info_list, league_raw_str)
                date_s = m_time_str.split(" ")[0].replace("-", ".").replace("/", ".")
                row_formatted_desc = f"{date_s} / vs {opponent_n}<br>{league_title} / {imp_lbl} / {loc_kind}"
                return {"desc": row_formatted_desc, "loc_type": loc_kind, "diff_days": d_diff_val}

            chrono_sorted_past = sorted(past_arr, key=lambda x: x[0])
            past_7d_collected, past_4d_collected = [], []

            for d_d, f_item in chrono_sorted_past:
                abs_d_val = abs(d_d)
                if 4 < abs_d_val <= 7:
                    past_7d_collected.append(parse_single_fixture(f_item, d_d)["desc"])
                elif 1 <= abs_d_val <= 4:
                    past_4d_collected.append(parse_single_fixture(f_item, d_d)["desc"])

            cell_7d = past_7d_collected[0] if past_7d_collected else "휴식"
            cell_4d = past_4d_collected[0] if past_4d_collected else "휴식"

            current_fatigue_acc = 0
            if cell_4d != "휴식":
                if "원정" in cell_4d:
                    current_fatigue_acc += 1
                if cell_7d != "휴식" and "원정" in cell_7d:
                    current_fatigue_acc += 1

            my_loc_type = "홈" if is_home_team else "원정"
            if current_fatigue_acc > 0 and my_loc_type == "원정":
                final_match_fatigue_stage = current_fatigue_acc + 1
            elif current_fatigue_acc > 0:
                final_match_fatigue_stage = current_fatigue_acc
            else:
                final_match_fatigue_stage = 1 if my_loc_type == "원정" else 0

            future_4d_list = [parse_single_fixture(f, d)["desc"] for d, f in future_arr if 0 < d <= 4]
            future_7d_list = [parse_single_fixture(f, d)["desc"] for d, f in future_arr if 4 < d <= 7]

            return cell_7d, cell_4d, future_4d_list, future_7d_list, final_match_fatigue_stage

        isolated_home_recent = list(h_matches) if 'h_matches' in locals() and isinstance(h_matches, list) else []
        isolated_away_recent = list(a_matches) if 'a_matches' in locals() and isinstance(a_matches, list) else []
        
        home_p7, home_p4, home_f4, home_f7, h_last_fatigue = parse_timeline_strictly_isolated(raw_home_fixes, isolated_home_recent, home_team, match_date, True, home_standings_list)
        away_p7, away_p4, away_f4, away_f7, a_last_fatigue = parse_timeline_strictly_isolated(raw_away_fixes, isolated_away_recent, away_team, match_date, False, away_standings_list)

        h_fut_c1 = home_f4[0] if home_f4 else "휴식"
        h_fut_c2 = home_f7[0] if home_f7 else "휴식"
        a_fut_c1 = away_f4[0] if away_f4 else "휴식"
        a_fut_c2 = away_f7[0] if away_f7 else "휴식"

        h_imp_label, h_imp_atk, h_imp_def = determine_match_importance(home_standings_list, tournament_display)
        a_imp_label, a_imp_atk, a_imp_def = determine_match_importance(away_standings_list, tournament_display)

        date_str_short = match_date.split()[0].replace("-", ".").replace("/", ".")
        home_match_cell = f"{date_str_short} / {home_team} vs {away_team}<br>{tournament_display} / {h_imp_label} / 홈"
        away_match_cell = f"{date_str_short} / {home_team} vs {away_team}<br>{tournament_display} / {a_imp_label} / 원정"

        st.markdown(f"##### 표 3-2: {home_team} vs {away_team} 일정 및 피로도·중요도 매트릭스")
        
        timeline_table_html = f"""
        <style>
        .custom-timeline-wrap {{width: 100%; overflow-x: auto; margin-top: 10px; margin-bottom: 20px; border: 1px solid #e0e0e0; border-radius: 6px;}}
        .custom-timeline-table {{width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; background-color: white; min-width: 900px;}}
        .custom-timeline-table th, .custom-timeline-table td {{border: 1px solid #e0e0e0; padding: 10px 8px; vertical-align: middle; white-space: nowrap;}}
        .custom-timeline-table th {{background-color: #f5f5f5; font-weight: bold; color: #333;}}
        .custom-timeline-table tr:hover {{background-color: #fafafa;}}
        </style>
        <div class="custom-timeline-wrap">
        <table class="custom-timeline-table">
        <thead>
        <tr>
        <th>팀명</th>
        <th>7일이내(과거)</th>
        <th>4일이내(과거)</th>
        <th style="background-color: #e3f2fd;">해당 경기</th>
        <th>향후 4일이내</th>
        <th>향후 7일이내</th>
        <th>보정사항 (중요도/피로누적)</th>
        </tr>
        </thead>
        <tbody>
        <tr>
        <td style="font-weight: bold; background-color: #fafafa;">홈 팀<br>({home_team})</td>
        <td>{home_p7}</td><td>{home_p4}</td>
        <td style="background-color: #f7fbff; font-weight: bold;">{home_match_cell}</td>
        <td>{h_fut_c1}</td><td>{h_fut_c2}</td>
        <td>{h_imp_label} / 피로누적 {h_last_fatigue}단계</td>
        </tr>
        <tr>
        <td style="font-weight: bold; background-color: #fafafa;">원정 팀<br>({away_team})</td>
        <td>{away_p7}</td><td>{away_p4}</td>
        <td style="background-color: #f7fbff; font-weight: bold;">{away_match_cell}</td>
        <td>{a_fut_c1}</td><td>{a_fut_c2}</td>
        <td>{a_imp_label} / 피로누적 {a_last_fatigue}단계</td>
        </tr>
        </tbody>
        </table>
        </div>
        """
        st.markdown(timeline_table_html, unsafe_allow_html=True)

        h_fa, h_fd = -5 * h_last_fatigue, 5 * h_last_fatigue
        a_fa, a_fd = -5 * a_last_fatigue, 5 * a_last_fatigue

        h_tot_calc_atk = h_imp_atk + h_fa
        h_tot_calc_def = h_imp_def + h_fd
        a_tot_calc_atk = a_imp_atk + a_fa
        a_tot_calc_def = a_imp_def + a_fd

        st.markdown(f"""
        <div class="calc-box">
            <b>규칙 3번 상세 산출 내역 및 보정 합산:</b><br>
            • <b>{home_team}:</b> {h_imp_label}(공격 {h_imp_atk:+g}%, 방어 {h_imp_def:+g}%), 피로누적 {h_last_fatigue}단계(공격 {h_fa}%, 방어 +{h_fd}%)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;➔ <b>총 가중치:</b> 공격 {h_tot_calc_atk:+g}%, 방어 {h_tot_calc_def:+g}%<br><br>
            • <b>{away_team}:</b> {a_imp_label}(공격 {a_imp_atk:+g}%, 방어 {a_imp_def:+g}%), 피로누적 {a_last_fatigue}단계(공격 {a_fa}%, 방어 +{a_fd}%)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;➔ <b>총 가중치:</b> 공격 {a_tot_calc_atk:+g}%, 방어 {a_tot_calc_def:+g}%
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터(fixtures)가 아직 수집되지 않았습니다.")
        st.info("💡 크롤러 대상 기간에 포함되지 않은 경기이므로, 일정 누수 및 피로도 산출 내역을 표시할 수 없습니다.")

# --- [4단계] --- 
with tabs[4]:
    st.markdown(f"#### [규칙 4번: 역대 공식 맞대결 상성 전수 로그 및 단방향 10% 룰] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
        <b>📌 규칙 4번 규격 원칙 및 요약 설명:</b><br>
        • <b>전수 조사 대상:</b> 역대 공식 맞대결 최근 10경기 전수 조사 (5경기 미만일 시 동등 팀으로 간주)<br>
        • <b>친선전 전면 배제:</b> 친선 경기는 전면 배제하고 오직 공식 A매치 및 대회 맞대결 기록만을 표본으로 채택합니다.<br>
        • <b>단방향 10% 룰 (Single-Direction Rule):</b> 통산 승률 50% 이상인 상성 우세 팀에게 공격력 +10% 및 방어력 -10% 단방향 상성 보정을 동시 부여합니다 (열세 또는 동등 팀은 0% 고정).<br>
        • <b>'단방향'인 이유:</b> 상대 팀 수치를 깎아내리는 방식이 아니라, 승률 50% 이상으로 상성 우위를 입증한 우세 팀에게만 보정(+10% / -10%)을 더해주고 열세 팀은 0%로 고정하기 때문입니다.
    </div>
    """, unsafe_allow_html=True)

    # 💡 상세 데이터가 존재할 때만 크롤링된 H2H 표 및 산출 내역 동적 렌더링
    if has_detailed_data:
        meta_details = detailed_info.get("meta_details", {})
        h2h_info = meta_details.get("h2h", {})
        h2h_matches = h2h_info.get("matches", [])
        h2h_summary = h2h_info.get("summary", [])
        
        st.markdown(f"##### {home_team} 기준 역대 공식 맞대결 최근 경기 전수 표")
        
        if h2h_matches:
            h2h_table_data = []
            home_wins = 0
            draws = 0
            away_wins = 0
            total_games = len(h2h_matches)
            
            for idx, m in enumerate(h2h_matches):
                row_cols = m.get("row_data", [])
                if len(row_cols) >= 4:
                    # 💡 대회 압축어 한글 변환 함수 적용
                    raw_match_info = row_cols[0]
                    match_date_str = translate_tournament_code(raw_match_info)
                    
                    h_team_name = row_cols[1]     # 홈팀
                    score_str = row_cols[2]       # 스코어 ("3-3")
                    a_team_name = row_cols[3]     # 원정팀
                    
                    # 경기 결과 판정 (선택된 홈팀 기준)
                    res_label = "-"
                    try:
                        scores = score_str.replace("：", "-").split("-")
                        h_score = int(scores[0].strip())
                        a_score = int(scores[1].strip())
                        
                        if h_team_name == home_team:
                            if h_score > a_score:
                                res_label = "승"
                                home_wins += 1
                            elif h_score < a_score:
                                res_label = "패"
                                away_wins += 1
                            else:
                                res_label = "무"
                                draws += 1
                        else:
                            if h_score > a_score:
                                res_label = "패"
                                away_wins += 1
                            elif h_score < a_score:
                                res_label = "승"
                                home_wins += 1
                            else:
                                res_label = "무"
                                draws += 1
                    except Exception:
                        pass
                    
                    match_seq_label = f"{idx + 1} (최신)" if idx == 0 else (f"{idx + 1} (과거)" if idx == total_games - 1 else str(idx + 1))
                    
                    h2h_table_data.append({
                        "H2H 순서": match_seq_label,
                        "경기 기록": match_date_str,
                        "대진 기록": f"{h_team_name} vs {a_team_name}",
                        "최종 스코어": score_str.replace("-", " : "),
                        "경기 결과 판정": res_label
                    })
            
            if h2h_table_data:
                df_h2h = pd.DataFrame(h2h_table_data)
                st.dataframe(df_h2h, use_container_width=True, hide_index=True)
            
            # 💡 통산 승률 산출식 반영 (승률(%) = [승수 / 총 경기 수] x 100)
            home_win_rate = (home_wins / total_games * 100) if total_games > 0 else 0
            away_win_rate = (away_wins / total_games * 100) if total_games > 0 else 0
            
            # 💡 단방향 10% 룰 적용 판정 로직 (5경기 이상 & 승률 50% 이상 기준)
            if total_games >= 5:
                if home_win_rate >= 50.0:
                    r4_desc = f"🔥 <b>[상성 우세 보정 적용]</b> {home_team} 승률 50% 이상 달성 (공격력 +10% / 방어력 -10% 단방향 보정 부여)"
                elif away_win_rate >= 50.0:
                    r4_desc = f"🔥 <b>[상성 우세 보정 적용]</b> {away_team} 승률 50% 이상 달성 (공격력 +10% / 방어력 -10% 단방향 보정 부여)"
                else:
                    r4_desc = "⚖️ <b>판정 결과: 양팀 승률 50% 미만 또는 우세 없음 (공격/방어 보정 0% 고정)</b>"
            else:
                r4_desc = "⚖️ <b>판정 결과: 맞대결 표본 5경기 미만으로 동등 팀 간주 (공격/방어 보정 0% 고정)</b>"

            summary_text = f"• 맞대결 통계 요약 원문: {', '.join(h2h_summary)}<br>" if h2h_summary else ""

            st.markdown(f"""
            <div class="calc-box">
                <b>규칙 4번 상세 산출 내역 및 계산 공식:</b><br>
                {summary_text}
                • <b>{home_team} 산출식:</b> [{home_wins}승 / 총 {total_games}전] x 100 = <b>승률 {home_win_rate:.1f}%</b><br>
                • <b>{away_team} 산출식:</b> [{away_wins}승 / 총 {total_games}전] x 100 = <b>승률 {away_win_rate:.1f}%</b><br>
                • <b>단방향 10% 룰 적용 결과:</b> {r4_desc}
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.info("💡 해당 경기에 수집된 역대 맞대결(h2h) 상세 기록이 존재하지 않습니다.")
    else:
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터가 아직 수집되지 않았습니다. (3~4일 이후 경기 등)")
        st.info("💡 크롤러 대상 기간에 포함되지 않은 경기이므로, H2H 상대전적 상성 산출 내역을 표시할 수 없습니다.")

# ==========================================
# 💡 [안전 방어 장치] 규칙 4번 변수 누락 방지 초기화
# ==========================================
if 'home_win_rate' not in locals():
    home_win_rate = 0.0
if 'away_win_rate' not in locals():
    away_win_rate = 0.0

if 'h_last_fatigue' not in locals():
    h_last_fatigue = 0
if 'a_last_fatigue' not in locals():
    a_last_fatigue = 0

# 글로벌 변수 할당 안전 처리
global h_r4_atk_val, h_r4_def_val, a_r4_atk_val, a_r4_def_val
if home_win_rate >= 50.0:
    h_r4_atk_val = 10.0
    h_r4_def_val = -10.0
else:
    h_r4_atk_val = 0.0
    h_r4_def_val = 0.0

if away_win_rate >= 50.0:
    a_r4_atk_val = 10.0
    a_r4_def_val = -10.0
else:
    a_r4_atk_val = 0.0
    a_r4_def_val = 0.0

with tabs[5]:
    st.markdown(f"#### [규칙 5번: 최종 보정 및 1차 기본 기대 득실점 산출] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
        <b>📌 규격 원칙 및 요약 설명:</b><br>
        • 0단계(country.json 등급 보정) 및 1단계 공수 기본 기대치부터 규칙 1~4까지의 모든 보정치를 누적 합산합니다.<br>
        • 최종 누적 보정치와 독자 공수 한계선을 바탕으로 기하평균 공수 교차 상쇄 결합 연산을 수행하여 최종 1차 기본 기대 득실점을 도출합니다.
    </div>
    """, unsafe_allow_html=True)

    if has_detailed_data:
        # 1. 0단계 연동 가중치 안전 추출 (정보 없으면 0% 방어)
        h_grade_val = st.session_state.get("h_grade", "F")
        h_atk_bonus_str = st.session_state.get("h_atk_bonus", "0%")
        h_def_bonus_str = st.session_state.get("h_def_bonus", "0%")

        a_grade_val = st.session_state.get("a_grade", "F")
        a_atk_bonus_str = st.session_state.get("a_atk_bonus", "0%")
        a_def_bonus_str = st.session_state.get("a_def_bonus", "0%")

        def parse_pct(val_str):
            if isinstance(val_str, (int, float)):
                return float(val_str)
            if isinstance(val_str, str):
                cleaned = val_str.replace('%', '').replace('+', '').strip()
                try:
                    return float(cleaned)
                except:
                    return 0.0
            return 0.0

        h_step0_atk = parse_pct(h_atk_bonus_str) if h_grade_val != "F" else 0.0
        h_step0_def = parse_pct(h_def_bonus_str) if h_grade_val != "F" else 0.0
        a_step0_atk = parse_pct(a_atk_bonus_str) if a_grade_val != "F" else 0.0
        a_step0_def = parse_pct(a_def_bonus_str) if a_grade_val != "F" else 0.0

        # 2. 1단계 기본 기대치 안전 추출
        h_base_g = h_gpg if 'h_gpg' in locals() else 0.0
        h_base_c = h_cpg if 'h_cpg' in locals() else 0.0
        a_base_g = a_gpg if 'a_gpg' in locals() else 0.0
        a_base_c = a_cpg if 'a_cpg' in locals() else 0.0

        # 3. 규칙별 보정치 안전 정의 (정보 없을 시 0.0% 방어)
        h_atw = h_atw if 'h_atw' in locals() else "0%"
        h_dew = h_dew if 'h_dew' in locals() else "0%"
        a_atw = a_atw if 'a_atw' in locals() else "0%"
        a_dew = a_dew if 'a_dew' in locals() else "0%"

        h_r1_atk = parse_pct(h_atw)
        h_r1_def = parse_pct(h_dew)
        a_r1_atk = parse_pct(a_atw)
        a_r1_def = parse_pct(a_dew)

        h_r2_atk = h_atk_val if 'h_atk_val' in locals() else 0.0
        h_r2_def = h_def_val if 'h_def_val' in locals() else 0.0
        a_r2_atk = a_atk_val if 'a_atk_val' in locals() else 0.0
        a_r2_def = a_def_val if 'a_def_val' in locals() else 0.0

        h_r31_atk = h_r31_atk_val if 'h_r31_atk_val' in locals() else 0.0
        h_r31_def = h_r31_def_val if 'h_r31_def_val' in locals() else 0.0
        a_r31_atk = a_r31_atk_val if 'a_r31_atk_val' in locals() else 0.0
        a_r31_def = a_r31_def_val if 'a_r31_def_val' in locals() else 0.0

        # 💡 [규칙 3-2 중요도 가중치 연동 코드]
        h_imp_atk_val = h_imp_atk if 'h_imp_atk' in locals() else 0.0
        h_imp_def_val = h_imp_def if 'h_imp_def' in locals() else 0.0
        a_imp_atk_val = a_imp_atk if 'a_imp_atk' in locals() else 0.0
        a_imp_def_val = a_imp_def if 'a_imp_def' in locals() else 0.0

        # 이동 피로도 단계 가중치 연동
        h_fatigue_stage = h_last_fatigue if 'h_last_fatigue' in locals() else 0
        a_fatigue_stage = a_last_fatigue if 'a_last_fatigue' in locals() else 0
        
        h_r32_atk = (-5 * h_fatigue_stage)
        h_r32_def = (5 * h_fatigue_stage)
        a_r32_atk = (-5 * a_fatigue_stage)
        a_r32_def = (5 * a_fatigue_stage)

        # 규칙 3번 전체 통합 합산 (3-1 전력누수 + 3-2 중요도 + 3-2 이동피로도)
        h_r3_tot_atk = h_r31_atk + h_imp_atk_val + h_r32_atk
        h_r3_tot_def = h_r31_def + h_imp_def_val + h_r32_def
        a_r3_tot_atk = a_r31_atk + a_imp_atk_val + a_r32_atk
        a_r3_tot_def = a_r31_def + a_imp_def_val + a_r32_def

        h_r4_atk = h_r4_atk_val if 'h_r4_atk_val' in locals() else 0.0
        h_r4_def = h_r4_def_val if 'h_r4_def_val' in locals() else 0.0
        a_r4_atk = a_r4_atk_val if 'a_r4_atk_val' in locals() else 0.0
        a_r4_def = a_r4_def_val if 'a_r4_def_val' in locals() else 0.0

        # 최종 누적 보정치 합산 (0단계 및 규칙 1~4 통합)
        h_tot_atk_pct = h_step0_atk + h_r1_atk + h_r2_atk + h_r3_tot_atk + h_r4_atk
        h_tot_def_pct = h_step0_def + h_r1_def + h_r2_def + h_r3_tot_def + h_r4_def
        a_tot_atk_pct = a_step0_atk + a_r1_atk + a_r2_atk + a_r3_tot_atk + a_r4_atk
        a_tot_def_pct = a_step0_def + a_r1_def + a_r2_def + a_r3_tot_def + a_r4_def

        h_max_g = h_base_g * (1 + h_tot_atk_pct / 100.0)
        h_min_c = h_base_c * (1 + h_tot_def_pct / 100.0)
        a_max_g = a_base_g * (1 + a_tot_atk_pct / 100.0)
        a_min_c = a_base_c * (1 + a_tot_def_pct / 100.0)

        h_final_exp_g = max(0.2, (h_max_g + (2.0 - a_min_c)) / 2.0)
        h_final_exp_c = max(0.2, (h_min_c + (2.0 - a_max_g)) / 2.0)
        a_final_exp_g = max(0.2, (a_max_g + (2.0 - h_min_c)) / 2.0)
        a_final_exp_c = max(0.2, (a_min_c + (2.0 - h_max_g)) / 2.0)

        # --------------------------------------------------------------------------
        # 📊 [5-1 표] 렌더링
        # --------------------------------------------------------------------------
        st.markdown(f"##### 📊 [5-1 표] 최종 보정 득실점 산출 매트릭스 ({home_team} vs {away_team})")
        table_data_51 = [
            {"구분 항목": "1단계: 공수 기본 기대치", f"홈 팀 ({home_team})": f"평균 득점 {h_base_g:.2f} / 평균 실점 {h_base_c:.2f}", f"원정 팀 ({away_team})": f"평균 득점 {a_base_g:.2f} / 평균 실점 {a_base_c:.2f}", "보정 및 산출 연산 근거": "대륙/국가 기본 공수 스케일 수치"},
            {"구분 항목": "0단계 (country.json 등급 연동)", f"홈 팀 ({home_team})": f"공격 {h_step0_atk:+.1f}% / 방어 {h_step0_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_step0_atk:+.1f}% / 방어 {a_step0_def:+.1f}%", "보정 및 산출 연산 근거": "리그 순위표 등급별 공수 보정치 (정보 없을 시 0%)"},
            {"구분 항목": "규칙 1 (7경기 LIFO 가중치)", f"홈 팀 ({home_team})": f"공격 {h_r1_atk:+.1f}% / 방어 {h_r1_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r1_atk:+.1f}% / 방어 {a_r1_def:+.1f}%", "보정 및 산출 연산 근거": "최근 10경기 상대 티어 가중치"},
            {"구분 항목": "규칙 2 (구장 환경 보정)", f"홈 팀 ({home_team})": f"공격 {h_r2_atk:+.1f}% / 방어 {h_r2_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r2_atk:+.1f}% / 방어 {a_r2_def:+.1f}%", "보정 및 산출 연산 근거": "홈/원정 구장 Shift 변동성"},
            {"구분 항목": "규칙 3-1 (선수 전력 누수)", f"홈 팀 ({home_team})": f"공격 {h_r31_atk:+.1f}% / 방어 {h_r31_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r31_atk:+.1f}% / 방어 {a_r31_def:+.1f}%", "보정 및 산출 연산 근거": "핵심 자원 누수/가산 (반감 규칙 반영)"},
            {"구분 항목": "규칙 3-2 (일정 중요도 판단)", f"홈 팀 ({home_team})": f"공격 {h_imp_atk_val:+.1f}% / 방어 {h_imp_def_val:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_imp_atk_val:+.1f}% / 방어 {a_imp_def_val:+.1f}%", "보정 및 산출 연산 근거": "진출권/강등권 태그 기반 중요도 (정보 없을 시 0%)"},
            {"구분 항목": "규칙 3-2 (이동 피로도 누적)", f"홈 팀 ({home_team})": f"공격 {h_r32_atk:+.1f}% / 방어 {h_r32_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r32_atk:+.1f}% / 방어 {a_r32_def:+.1f}%", "보정 및 산출 연산 근거": "원정 이동 거리 및 연전 피로도 (단계별 5%)"},
            {"구분 항목": "규칙 4 (H2H 상성 보정)", f"홈 팀 ({home_team})": f"공격 {h_r4_atk:+.1f}% / 방어 {h_r4_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r4_atk:+.1f}% / 방어 {a_r4_def:+.1f}%", "보정 및 산출 연산 근거": "최근 10전 단방향 상성 우세 여부"},
            {"구분 항목": "최종 누적 보정치 합계", f"홈 팀 ({home_team})": f"공격 {h_tot_atk_pct:+.1f}% / 방어 {h_tot_def_pct:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_tot_atk_pct:+.1f}% / 방어 {a_tot_def_pct:+.1f}%", "보정 및 산출 연산 근거": "0단계 및 규칙 1~4 보정치 최종 누적 합산"},
            {"구분 항목": "1단계 화력/수비 한계 수치", f"홈 팀 ({home_team})": f"상한 득점 {h_max_g:.2f} / 하한 실점 {h_min_c:.2f}", f"원정 팀 ({away_team})": f"상한 득점 {a_max_g:.2f} / 하한 실점 {a_min_c:.2f}", "보정 및 산출 연산 근거": "자체 독자 공수 한계선 (단위: 골)"},
            {"구분 항목": "1차기본기대 득실점", f"홈 팀 ({home_team})": f"기대 득점 {h_final_exp_g:.2f}골 / 예상 실점 {h_final_exp_c:.2f}골", f"원정 팀 ({away_team})": f"기대 득점 {a_final_exp_g:.2f}골 / 예상 실점 {a_final_exp_c:.2f}골", "보정 및 산출 연산 근거": "기하평균 공수 교차 상쇄 결합 연산"}
        ]
        st.dataframe(pd.DataFrame(table_data_51), use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------
        # 📊 [5-2 표] 렌더링 (2단계 체급 연동 + 승패 정방향 교정 + 최신순 시계열 정렬 완성 규격)
        # --------------------------------------------------------------------------
        st.markdown("---")
        st.markdown(f"##### 📊 [5-2 표] 동급 티어 실전 7경기 교차 검증 매트릭스 ({home_team} vs {away_team})")

        # 💡 [핵심 연동] 2단계(구장별 폼)에서 산출된 최종 체급(s_h_at, s_h_de, s_a_at, s_a_de)을 우선 연동하여 매칭 및 교차 보정에 반영
        h_opp_at = s_a_at if 's_a_at' in locals() else (a_current_at if 'a_current_at' in locals() else "Tier C")
        h_opp_de = s_a_de if 's_a_de' in locals() else (a_current_de if 'a_current_de' in locals() else "Tier C")
        a_opp_at = s_h_at if 's_h_at' in locals() else (h_current_at if 'h_current_at' in locals() else "Tier C")
        a_opp_de = s_h_de if 's_h_de' in locals() else (h_current_de if 'h_current_de' in locals() else "Tier C")

        home_raw_pool = []
        away_raw_pool = []
        target_v3_match = v3_details_dict.get(str(match_code), {}) if 'v3_details_dict' in locals() else {}
        stadium_form_block = target_v3_match.get("meta_details", {}).get("stadium_form", {}) if target_v3_match else {}
        if stadium_form_block:
            home_raw_pool = stadium_form_block.get("home_matches", [])
            away_raw_pool = stadium_form_block.get("away_matches", [])
        if not home_raw_pool:
            home_raw_pool = s_home_matches if 's_home_matches' in locals() and s_home_matches else (h_matches if 'h_matches' in locals() else [])
        if not away_raw_pool:
            away_raw_pool = s_away_matches if 's_away_matches' in locals() and s_away_matches else (a_matches if 'a_matches' in locals() else [])

        def get_real_matches_without_friendlies(match_list):
            if not match_list or not isinstance(match_list, list):
                return []
            valid = []
            for fix in match_list:
                league_raw = str(fix.get("league", ""))
                league_lower = league_raw.lower()
                if any(keyword in league_lower for keyword in ["친선", "friendly", "int cf", "club friendlies", "friendlies"]):
                    continue
                scores_arr = fix.get("ft_scores", [])
                score_str = str(fix.get("score", "") or fix.get("result", ""))
                if not score_str and (scores_arr and len(scores_arr) >= 2):
                    score_str = f"{scores_arr[0]} : {scores_arr[1]}"
                if not score_str or (":" not in score_str and "-" not in score_str and not scores_arr):
                    continue
                valid.append(fix)
            return valid

        def filter_matched_tier_games(match_list, target_at_name, target_de_name):
            valid_pool = get_real_matches_without_friendlies(match_list)
            if not valid_pool:
                return []

            tier_score_map = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
            t_at_val = tier_score_map.get(target_at_name, 3)
            t_de_val = tier_score_map.get(target_de_name, 3)

            scored_pool = []
            for m in valid_pool:
                tier_info = m.get("opponent_tier_info", "")
                oa, od = 1.3, 1.2
                if tier_info and "/" in tier_info:
                    try:
                        parts_o = tier_info.split("/")
                        oa = float(parts_o[0].strip())
                        od = float(parts_o[1].strip())
                    except:
                        pass
                op_at_name = atk_tier_nm(oa)
                op_de_name = def_tier_nm(od)
                
                op_at_val = tier_score_map.get(op_at_name, 3)
                op_de_val = tier_score_map.get(op_de_name, 3)

                diff_at = abs(t_at_val - op_at_val)
                diff_de = abs(t_de_val - op_de_val)
                match_score = diff_at + diff_de

                has_extreme_target = (target_at_name in ["Tier A", "Tier E"] or target_de_name in ["Tier A", "Tier E"])
                has_extreme_opp = (op_at_name in ["Tier A", "Tier E"] or op_de_name in ["Tier A", "Tier E"])
                
                if has_extreme_target and has_extreme_opp:
                    if target_at_name == op_at_name or target_de_name == op_de_name:
                        match_score -= 2.5

                scored_pool.append((match_score, m))

            # 1. 티어 매칭 점수가 가장 좋은 순서로 우선 정렬 후 상위 7경기 추출
            scored_pool.sort(key=lambda x: x[0])
            sorted_matches = [item[1] for item in scored_pool[:7]]
            
            # 💡 [핵심 교정] 최종 선별된 7경기를 경기 일시(match_time) 기준 최신순(내림차순)으로 정렬하여 시계열 흐름 반영
            try:
                sorted_matches.sort(key=lambda x: str(x.get("match_time", "")), reverse=True)
            except:
                pass

            return sorted_matches

        home_matched_7 = filter_matched_tier_games(home_raw_pool, h_opp_at, h_opp_de)
        away_matched_7 = filter_matched_tier_games(away_raw_pool, a_opp_at, a_opp_de)

        def build_team_52_dataframe(match_list, team_label, my_at, my_de):
            rows = []
            cnt = len(match_list)
            if cnt == 0:
                return pd.DataFrame([{"순서": "데이터 없음", "경기 일시": "-", "대회 명칭": "-", "장소": "-", "상대 팀": f"[{team_label}] 조건 부합 경기 없음", "상대 티어": "-", "최종 스코어": "-", "결과": "-", "비고": "0득점 / 0실점"}]), 0, 0, 0.0, 0.0, False
            
            total_gf, total_ga = 0.0, 0.0
            any_rule_applied = False

            for i, m in enumerate(match_list, 1):
                m_date = str(m.get("match_time", "-")).split(" ")[0].replace("-", ".")
                raw_league = str(m.get("league", "-"))
                m_league = translate_tournament_code(raw_league)
                m_score = str(m.get("score", "") or m.get("result", "0 : 0"))
                scores_arr = m.get("ft_scores", [])
                if scores_arr and len(scores_arr) >= 2:
                    m_score = f"{scores_arr[0]} : {scores_arr[1]}"
                m_loc = str(m.get("location", "공식"))
                
                # 💡 [정밀 교정] 대진 문자열(teams)을 분석하여 해당 팀이 홈인지 원정인지 판정 및 상대 팀 추출
                teams_str = str(m.get("teams", ""))
                is_team_home = True
                m_opp = ""
                if " vs " in teams_str:
                    t_parts = [p.strip() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2:
                        if team_label.strip() in t_parts[1] and team_label.strip() not in t_parts[0]:
                            is_team_home = False
                            m_opp = t_parts[0]
                        else:
                            m_opp = t_parts[1]
                if not m_opp:
                    m_opp = str(m.get("opponent", "") or m.get("team", "")).strip()
                if not m_opp:
                    m_opp = "상대 팀명 미확인"

                raw_s1, raw_s2 = 0, 0
                try:
                    parts = m_score.replace("-", ":").split(":")
                    if len(parts) >= 2:
                        raw_s1 = int(parts[0].strip())
                        raw_s2 = int(parts[1].strip())
                except:
                    pass

                # 💡 [핵심 교정] 원정 경기일 경우 스코어 득실을 내 팀 관점에 맞게 정상적으로 스위치
                if not is_team_home and " vs " in teams_str:
                    gf = raw_s2
                    ga = raw_s1
                else:
                    gf = raw_s1
                    ga = raw_s2

                oa, od = 1.3, 1.2
                tier_info = m.get("opponent_tier_info", "")
                if tier_info and "/" in tier_info:
                    try:
                        parts_o = tier_info.split("/")
                        oa = float(parts_o[0].strip())
                        od = float(parts_o[1].strip())
                    except:
                        pass
                at_name = atk_tier_nm(oa)
                df_name = def_tier_nm(od)
                m_opp_tier = f"{at_name} / {df_name}"

                original_gf = float(gf)
                original_ga = float(ga)
                mult_gf = 1.0
                mult_ga = 1.0
                rule_desc = ""

                # [5-2 표 독립 공수 대칭 교차 보정 규격]
                if my_at == "Tier A" and df_name == "Tier E":
                    mult_gf = 0.5
                    rule_desc = "공격 A vs 상대수비 E (득점 50% 할인)"
                elif my_at == "Tier E" and df_name == "Tier A":
                    mult_gf = 1.5
                    rule_desc = "공격 E vs 상대수비 A (득점 50% 할증)"
                    
                if my_de == "Tier A" and at_name == "Tier E":
                    mult_ga = 1.5
                    rule_desc = (rule_desc + " / " if rule_desc else "") + "방어 A vs 상대공격 E (실점 50% 할증)"
                elif my_de == "Tier E" and at_name == "Tier A":
                    mult_ga = 0.5
                    rule_desc = (rule_desc + " / " if rule_desc else "") + "방어 E vs 상대공격 A (실점 50% 할인)"

                app_gf = gf * mult_gf
                app_ga = ga * mult_ga

                if mult_gf != 1.0 or mult_ga != 1.0:
                    any_rule_applied = True

                total_gf += app_gf
                total_ga += app_ga
                
                # 💡 교정된 정방향 득실 기준으로 승/무/패 판정
                w_l = "승" if app_gf > app_ga else ("패" if app_gf < app_ga else "무")
                seq_txt = f"{i} (최신)" if i == 1 else (f"{i} (과거)" if i == cnt else str(i))
                
                if mult_gf != 1.0 or mult_ga != 1.0:
                    note_str = f"{int(original_gf)}득점 / {original_ga}실점 ⚠️ [{rule_desc} ➔ 보정: {app_gf:.1f}득점 / {app_ga:.1f}실점]"
                else:
                    note_str = f"{int(original_gf)}득점 / {int(original_ga)}실점"

                rows.append({
                    "순서": seq_txt, "경기 일시": m_date, "대회 명칭": m_league, "장소": m_loc, "상대 팀": m_opp,
                    "상대 티어 (A~E 등급 연동)": m_opp_tier, "최종 스코어": m_score, "결과": w_l, "비고 (득점 / 실점)": note_str
                })

            avg_gf = total_gf / cnt if cnt > 0 else 0.0
            avg_ga = total_ga / cnt if cnt > 0 else 0.0
            return pd.DataFrame(rows), total_gf, total_ga, avg_gf, avg_ga, any_rule_applied

        # 홈/원정 팀 체급 추출 (없으면 기본 C)
        home_my_at = h_current_at if 'h_current_at' in locals() else "Tier C"
        home_my_de = h_current_de if 'h_current_de' in locals() else "Tier C"
        away_my_at = a_current_at if 'a_current_at' in locals() else "Tier C"
        away_my_de = a_current_de if 'a_current_de' in locals() else "Tier C"

        st.markdown(f"##### 🏠 홈 팀: {home_team} (상대({away_team}) 연동 체급: 공격 {h_opp_at} / 방어 {h_opp_de})")
        h_df_52, h_tgf, h_tga, h_agf, h_aga, h_rule_active = build_team_52_dataframe(home_matched_7, home_team, home_my_at, home_my_de)
        if h_rule_active:
            st.info(f"⚡ **[공수 대칭 교차 보정 안내]** {home_team} 팀은 실전 7경기 검증 과정에서 상대 공수 티어와의 교차 상성에 따라 **득실점 할인/할증 보정**이 독립 반영되었습니다.")
        st.dataframe(h_df_52, use_container_width=True, hide_index=True)
        st.markdown(f"📌 **{home_team} 최근 7경기 총합:** {h_tgf:.1f}득점 / {h_tga:.1f}실점 &nbsp;|&nbsp; <span style='color: #d32f2f; font-weight: bold;'>실전 평균: 평균 득점 {h_agf:.2f}골 / 평균 실점 {h_aga:.2f}골</span>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"##### ✈️ 원정 팀: {away_team} (상대({home_team}) 연동 체급: 공격 {a_opp_at} / 방어 {a_opp_de})")
        a_df_52, a_tgf, a_tga, a_agf, a_aga, a_rule_active = build_team_52_dataframe(away_matched_7, away_team, away_my_at, away_my_de)
        if h_rule_active:
            st.info(f"⚡ **[공수 대칭 교차 보정 안내]** {away_team} 팀은 실전 7경기 검증 과정에서 상대 공수 티어와의 교차 상성에 따라 **득실점 할인/할증 보정**이 독립 반영되었습니다.")
        st.dataframe(a_df_52, use_container_width=True, hide_index=True)
        st.markdown(f"📌 **{away_team} 최근 7경기 총합:** {a_tgf:.1f} 득점 / {a_tga:.1f} 실점 &nbsp;|&nbsp; <span style='color: #d32f2f; font-weight: bold;'>실전 평균: 평균 득점 {a_agf:.2f} 골 / 평균 실점 {a_aga:.2f} 골</span>", unsafe_allow_html=True)
        # --------------------------------------------------------------------------
        # 📊 [5-3 표] 렌더링
        # --------------------------------------------------------------------------
        if 'h_current_at' not in locals(): h_current_at = 'Tier C'
        if 'a_current_at' not in locals(): a_current_at = 'Tier C'
        h_tier_val = tier_ranks.get(h_current_at, 3)
        a_tier_val = tier_ranks.get(a_current_at, 3)
        tier_diff = abs(h_tier_val - a_tier_val)

        h_base = h_final_exp_g
        a_base = a_final_exp_g
        h_conceded_base = h_final_exp_c
        a_conceded_base = a_final_exp_c

        h_over_factor = 0.0
        a_over_factor = 0.0
        over_factor_desc = "0% 적용 (표준/저득점형)"

        if tier_diff >= 2:
            if h_tier_val > a_tier_val:
                add_rate = 0.10 + (tier_diff - 2) * 0.10
                h_over_factor = add_rate
                over_factor_desc = f"체급 격차형 ({tier_diff}단계 차이): 홈 팀 공격력 + {int(add_rate*100)}% 가산"
            else:
                add_rate = 0.10 + (tier_diff - 2) * 0.10
                a_over_factor = add_rate
                over_factor_desc = f"체급 격차형 ({tier_diff}단계 차이): 원정 팀 공격력 + {int(add_rate*100)}% 가산"
        elif (h_base + a_base > 3.2) or (h_conceded_base >= 1.50 or a_conceded_base >= 1.50):
            h_over_factor = 0.15
            a_over_factor = 0.15
            over_factor_desc = "동급 난타전형: 양 팀 화력 보존 및 수비 불안 반영 (+15% 가산)"

        h_final = h_base * (1 + h_over_factor)
        a_final = a_base * (1 + a_over_factor)
        total_expected_goals = h_final + a_final

        st.markdown("---")
        st.markdown(f"##### 📊 [5-3 표] 다득점/체급차 변동성 보정 (Over Factor) 산출 매트릭스 ({home_team} vs {away_team})")
        table_data_53 = [
            {"구분 항목": "변동성 보정 유형 판정", f"홈 팀 ({home_team})": over_factor_desc, f"원정 팀 ({away_team})": over_factor_desc, "산출 근거 및 공식": "final = base * (1 + OverFactor)"},
            {"구분 항목": "다득점 가산 비율 (Over Factor)", f"홈 팀 ({home_team})": f"+ {int(h_over_factor*100)}%", f"원정 팀 ({away_team})": f"+ {int(a_over_factor*100)}%", "산출 근거 및 공식": "티어 격차 및 난타전 조건 연동"},
            {"구분 항목": "최종 보정 기대 득실점 (final)", f"홈 팀 ({home_team})": f"보정 득점 {h_final:.2f} 골", f"원정 팀 ({away_team})": f"보정 득점 {a_final:.2f} 골", "산출 근거 및 공식": "base 대비 최종 가산 반영 완료"}
        ]
        st.dataframe(pd.DataFrame(table_data_53), use_container_width=True, hide_index=True)

        # --------------------------------------------------------------------------
        # 📊 [5-4 표] 렌더링
        # --------------------------------------------------------------------------
        if total_expected_goals < 2.2:
            poisson_zone_name = "저득점 통제 구역 (total < 2.2)"
            matrix_range = "0 ~ 3골 범위 (4×4 행렬)"
        elif total_expected_goals <= 3.2 and tier_diff < 2:
            poisson_zone_name = "표준 득점 구역 (2.2 ~ 3.2)"
            matrix_range = "0 ~ 4골 범위 (5×5 행렬 - 기본)"
        else:
            poisson_zone_name = "다득점 변동 구역 (total > 3.2 또는 격차 2단계 이상)"
            matrix_range = "0 ~ 6골 / 0 ~ 7골 동적 확장 행렬"

        st.markdown("---")
        st.markdown(f"##### 📊 [5-4 표] 이원화 동적 골 범위 행렬 확정 매트릭스 ({home_team} vs {away_team})")
        table_data_54 = [
            {"구분 항목": "총 기대 득점 (개별 final)", f"홈 팀 ({home_team})": f"{h_final:.2f}골", f"원정 팀 ({away_team})": f"{a_final:.2f}골", "확정 구획 범주": poisson_zone_name, "푸아송 연산 행렬 범위": matrix_range},
            {"구분 항목": "양 팀 합계 (total)", f"홈 팀 ({home_team})": f"{total_expected_goals:.2f}골", f"원정 팀 ({away_team})": f"{total_expected_goals:.2f}골", "확정 구획 범주": poisson_zone_name, "푸아송 연산 행렬 범위": matrix_range}
        ]
        st.dataframe(pd.DataFrame(table_data_54), use_container_width=True, hide_index=True)

    else:
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터가 아직 수집되지 않았습니다.")
        st.info("💡 크롤러 대상 기간에 포함되지 않은 경기이므로, 규칙 5번 산출 내역을 표시할 수 없습니다.")

import math

# --------------------------------------------------------------------------
# 🧮 [규칙 6] 푸아송 분포 및 승무패 확률 / 예측 순위 정밀 연산 블록 (최종 완벽 수정본)
# --------------------------------------------------------------------------
def poisson_prob(lmbda, k):
    if lmbda <= 0 and k == 0:
        return 1.0
    try:
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    except:
        return 0.0

base_h_lambda = h_final_exp_g if 'h_final_exp_g' in locals() and h_final_exp_g is not None else 1.0
base_a_lambda = a_final_exp_g if 'a_final_exp_g' in locals() and a_final_exp_g is not None else 1.0

# 💡 안전 방어: h_final과 a_final이 누락되었을 경우 기본값 1.0으로 방어
safe_h_final = float(h_final) if 'h_final' in locals() and h_final is not None else 1.0
safe_a_final = float(a_final) if 'a_final' in locals() and a_final is not None else 1.0

total_exp_goals = safe_h_final + safe_a_final

if total_exp_goals < 2.2:
    matrix_max_k = 3
elif total_exp_goals <= 3.2 and (tier_diff if 'tier_diff' in locals() else 0) < 2:
    matrix_max_k = 4
else:
    matrix_max_k = 6

win_loss_probs = []
for h_g in range(matrix_max_k + 1):
    for a_g in range(matrix_max_k + 1):
        p_h = poisson_prob(base_h_lambda, h_g)
        p_a = poisson_prob(base_a_lambda, a_g)
        joint_prob = p_h * p_a
        win_loss_probs.append({"home_score": h_g, "away_score": a_g, "prob": joint_prob})

score_probs = []
for h_g in range(matrix_max_k + 1):
    for a_g in range(matrix_max_k + 1):
        p_h = poisson_prob(safe_h_final, h_g)
        p_a = poisson_prob(safe_a_final, a_g)
        joint_prob = p_h * p_a
        score_probs.append({"home_score": h_g, "away_score": a_g, "prob": joint_prob})

calc_home_win = sum(item["prob"] for item in win_loss_probs if item["home_score"] > item["away_score"]) * 100
calc_away_win = sum(item["prob"] for item in win_loss_probs if item["home_score"] < item["away_score"]) * 100
calc_draw = sum(item["prob"] for item in win_loss_probs if item["home_score"] == item["away_score"]) * 100

h_target_52 = h_agf if 'h_agf' in locals() and h_agf is not None else 1.0
a_target_52 = a_agf if 'a_agf' in locals() and a_agf is not None else 1.0

# [1순위] 규칙 5-2 결과에 가장 적합한 결과값 최우선 선정 (기존 로직 완벽 유지)
scored_candidates = []
for item in score_probs:
    hg, ag, prob = item["home_score"], item["away_score"], item["prob"]
    v52_distance = abs(hg - h_target_52) + abs(ag - a_target_52)
    fitness_score = v52_distance - (prob * 3.0)
    scored_candidates.append({"home_score": hg, "away_score": ag, "prob": prob, "fitness": fitness_score})

sorted_by_fitness = sorted(scored_candidates, key=lambda x: x["fitness"])
best_match_52 = sorted_by_fitness[0]

# [2순위] 1순위를 제외한 푸아송 확률 제일 높은 단일 스코어 선정 (기존 로직 완벽 유지)
sorted_by_prob = sorted(score_probs, key=lambda x: x["prob"], reverse=True)
second_match = None
for s in sorted_by_prob:
    if not (s["home_score"] == best_match_52["home_score"] and s["away_score"] == best_match_52["away_score"]):
        second_match = s
        break
if not second_match:
    second_match = sorted_by_prob[1] if len(sorted_by_prob) > 1 else best_match_52

# [3순위] 각 점수 차이별 확률 합산 후 가장 많이 차지한 점수 차이 구도 및 산출근거 생성
diff_probs = {}
for item in score_probs:
    diff = item["home_score"] - item["away_score"]
    diff_probs[diff] = diff_probs.get(diff, 0.0) + item["prob"]

sorted_diffs = sorted(diff_probs.items(), key=lambda x: x[1], reverse=True)

# 1위 구도 (3순위 메인)
top_diff_item = sorted_diffs[0] if sorted_diffs else (0, 0.1)
d_val, d_prob_val = top_diff_item[0], top_diff_item[1] * 100

if d_val > 0:
    s3_name = f"{home_team} {d_val}점차 승리"
elif d_val < 0:
    s3_name = f"{away_team} {abs(d_val)}점차 승리"
else:
    s3_name = "무승부 공방"

s3_desc = f"{s3_name} ({d_prob_val:.1f}%)"

# 차순위 구도들을 산출근거 문자열로 조합 (예: 2점차 승 21.3%, 무승부 13.3% 등)
calc_basis_parts = []
for diff_key, p_val in sorted_diffs[1:3]:
    pct = p_val * 100
    if diff_key > 0:
        p_name = f"{home_team} {diff_key}점차승"
    elif diff_key < 0:
        p_name = f"{away_team} {abs(diff_key)}점차승"
    else:
        p_name = "무승부"
    calc_basis_parts.append(f"{p_name} ({pct:.1f}%)")

s3_calc_basis = ", ".join(calc_basis_parts) if calc_basis_parts else "기타 점수차 구도 분산"

h_pred_1st = f"{best_match_52['home_score']}골"
a_pred_1st = f"{best_match_52['away_score']}골"
p1_rate = best_match_52["prob"] * 100
score_1st_str = f"{best_match_52['home_score']} : {best_match_52['away_score']}"

h_pred_2nd = f"{second_match['home_score']}골"
a_pred_2nd = f"{second_match['away_score']}골"
p2_rate = second_match["prob"] * 100
score_2nd_str = f"{second_match['home_score']} : {second_match['away_score']}"

# --------------------------------------------------------------------------
# 📊 [규칙 6번 렌더링] (안전 방어 통합 적용본)
# --------------------------------------------------------------------------
with tabs[6]:
    # 🛡️ [안전 방어 보장] 데이터 유실 시 기본값으로 방어하여 NameError 원천 차단
    safe_h_exp_g = h_final_exp_g if 'h_final_exp_g' in locals() and h_final_exp_g is not None else 1.0
    safe_h_exp_c = h_final_exp_c if 'h_final_exp_c' in locals() and h_final_exp_c is not None else 1.0
    safe_a_exp_g = a_final_exp_g if 'a_final_exp_g' in locals() and a_final_exp_g is not None else 1.0
    safe_a_exp_c = a_final_exp_c if 'a_final_exp_c' in locals() and a_final_exp_c is not None else 1.0

    safe_h_final = h_final if 'h_final' in locals() and h_final is not None else 1.0
    safe_a_final = a_final if 'a_final' in locals() and a_final is not None else 1.0
    safe_tot_goals = total_expected_goals if 'total_expected_goals' in locals() and total_expected_goals is not None else 2.0

    safe_h_agf = h_agf if 'h_agf' in locals() and h_agf is not None else 1.0
    safe_h_aga = h_aga if 'h_aga' in locals() and h_aga is not None else 1.0
    safe_a_agf = a_agf if 'a_agf' in locals() and a_agf is not None else 1.0
    safe_a_aga = a_aga if 'a_aga' in locals() and a_aga is not None else 1.0

    safe_home_win = calc_home_win if 'calc_home_win' in locals() and calc_home_win is not None else 33.3
    safe_draw = calc_draw if 'calc_draw' in locals() and calc_draw is not None else 33.3
    safe_away_win = calc_away_win if 'calc_away_win' in locals() and calc_away_win is not None else 33.3

    safe_h_over = int(h_over_factor * 100) if 'h_over_factor' in locals() and h_over_factor is not None else 0
    safe_a_over = int(a_over_factor * 100) if 'a_over_factor' in locals() and a_over_factor is not None else 0

    st.markdown(f"#### [규칙 6번: 예상 스코어 순위 산출 및 최종 통합 흐름 매트릭스] - {home_team} vs {away_team}")
    st.markdown("""<div class="step-box">
        <b>📌 예상스코어 순위 산출 방법 규격:</b><br>
        • <b>승무패 수리 확률:</b> 푸아송 매트릭스 전수 조합을 바탕으로 최종 승/무/패 확률을 산출합니다.<br>
        • <b>1순위 (최적합):</b> 규칙 5-2 실전 평균 결과값에 가장 적합한 최적 스코어를 선정합니다.<br>
        • <b>2순위 (차선책):</b> 1순위를 제외한 단일 푸아송 확률이 가장 높은 스코어를 선정합니다.<br>
        • <b>3순위 (대안책):</b> 각 점수 차이별 확률을 합산하여 가장 많이 차지한 점수 차이 구도를 표시합니다.
    </div>""", unsafe_allow_html=True)

    st.markdown("##### 📈 최종 승무패 수리 확률 분포")
    col_w1, col_w2, col_w3 = st.columns(3)
    with col_w1:
        st.markdown(f"""<div style="background-color: #f1f8e9; padding: 12px; border-radius: 8px; border: 1px solid #c8e6c9; text-align: center;">
            <p style="margin: 0; font-size: 13px; color: #2e7d32; font-weight: bold;">🏠 {home_team} 승리</p>
            <p style="margin: 4px 0; font-size: 20px; font-weight: bold; color: #1b5e20;">{safe_home_win:.1f}%</p>
        </div>""", unsafe_allow_html=True)
    with col_w2:
        st.markdown(f"""<div style="background-color: #fffde7; padding: 12px; border-radius: 8px; border: 1px solid #fff9c4; text-align: center;">
            <p style="margin: 0; font-size: 13px; color: #f57f17; font-weight: bold;">⚖️ 무승부 공방</p>
            <p style="margin: 4px 0; font-size: 20px; font-weight: bold; color: #f57f17;">{safe_draw:.1f}%</p>
        </div>""", unsafe_allow_html=True)
    with col_w3:
        st.markdown(f"""<div style="background-color: #e3f2fd; padding: 12px; border-radius: 8px; border: 1px solid #bbdefb; text-align: center;">
            <p style="margin: 0; font-size: 13px; color: #1565c0; font-weight: bold;">✈️ {away_team} 승리</p>
            <p style="margin: 4px 0; font-size: 20px; font-weight: bold; color: #0d47a1;">{safe_away_win:.1f}%</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 🏆 최종 예상 스코어 및 순위 산출 결과 요약")
    
    summary_cards_html = f"""
    <style>
    .score-summary-wrap {{
        display: flex;
        flex-direction: row;
        gap: 12px;
        width: 100%;
        margin-top: 8px;
        margin-bottom: 16px;
        box-sizing: border-box;
    }}
    .score-box-item {{
        flex: 1;
        background-color: #f8f9fa;
        padding: 14px 12px;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-width: 0;
    }}
    .score-box-header {{
        text-align: left;
        font-size: 13px;
        font-weight: bold;
        margin-bottom: 8px;
    }}
    .score-box-main {{
        font-size: 20px;
        font-weight: bold;
        color: #111;
        margin: 10px 0;
        word-break: break-all;
    }}
    .score-box-footer {{
        font-size: 11px;
        color: #666;
        text-align: right;
        margin-top: 4px;
        border-top: 1px solid #eee;
        padding-top: 6px;
    }}
    @media (max-width: 768px) {{
        .score-summary-wrap {{
            flex-direction: column;
        }}
    }}
    </style>
    <div class="score-summary-wrap">
        <div class="score-box-item">
            <div class="score-box-header" style="color: #1f77b4;">🥇 예측 1순위 (최적합)</div>
            <div class="score-box-main">{score_1st_str if 'score_1st_str' in locals() else '1 : 1'}</div>
            <div class="score-box-footer">확률: <b>{p1_rate:.2f}%</b> (5-2 결과 최적합)</div>
        </div>
        <div class="score-box-item">
            <div class="score-box-header" style="color: #ff7f0e;">🥈 예측 2순위 (차선책)</div>
            <div class="score-box-main">{score_2nd_str if 'score_2nd_str' in locals() else '0 : 0'}</div>
            <div class="score-box-footer">확률: <b>{p2_rate:.2f}%</b> (최고 확률 단일)</div>
        </div>
        <div class="score-box-item">
            <div class="score-box-header" style="color: #2ca02c;">🥉 예측 3순위 (대안책)</div>
            <div class="score-box-main" style="font-size: 16px;">{s3_desc if 's3_desc' in locals() else '무승부 (30.0%)'}</div>
            <div class="score-box-footer">합산 비중: <b>{d_prob_val:.1f}%</b> (점수차 총합)</div>
        </div>
    </div>
    """
    st.markdown(summary_cards_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 예시표 6: 최종 통합 흐름 매트릭스 및 예상 스코어 산출 표")
    
    try:
        h_p1_val, a_p1_val = [s.strip() for s in score_1st_str.split(":")]
    except:
        h_p1_val, a_p1_val = "-", "-"
        
    try:
        h_p2_val, a_p2_val = [s.strip() for s in score_2nd_str.split(":")]
    except:
        h_p2_val, a_p2_val = "-", "-"

    ex6_df = pd.DataFrame({
        "규칙 단계": ["규칙 5-1", "규칙 5-2", "규칙 5-3", "규칙 5-4", "규칙 6", "규칙 6", "규칙 6", "규칙 6"],
        "구분 및 연산 항목": [
            "1차 기본 기대 득실점 (base)", 
            "동급 티어 실전 5경기 교차 검증", 
            "다득점 변동성 보정 (Over Factor)", 
            "이원화 동적 골 범위 행렬 확정", 
            "최종 승무패 수리 확률", 
            "최종 스코어 예측 1순위 (최적합)", 
            "최종 스코어 예측 2순위 (차선책)", 
            "최종 스코어 예측 3순위 (대안책)"
        ],
        f"홈 팀 ({home_team})": [
            f"기대 득점 {safe_h_exp_g:.2f}골 / 예상 실점 {safe_h_exp_c:.2f}골",
            f"평균 득점 {safe_h_agf:.2f}골 / 평균 실점 {safe_h_aga:.2f}골",
            f"{safe_h_over}% 적용 (최종 = {safe_h_final:.2f})",
            f"{poisson_zone_name if 'poisson_zone_name' in locals() else '일반 구역'}",
            f"승리 확률 {safe_home_win:.1f}%",
            f"{h_p1_val}골",
            f"{h_p2_val}골",
            s3_desc if 's3_desc' in locals() else "-"
        ],
        f"원정 팀 ({away_team})": [
            f"기대 득점 {safe_a_exp_g:.2f}골 / 예상 실점 {safe_a_exp_c:.2f}골",
            f"평균 득점 {safe_a_agf:.2f}골 / 평균 실점 {safe_a_aga:.2f}골",
            f"{safe_a_over}% 적용 (최종 = {safe_a_final:.2f})",
            f"총 기대득점(total): {safe_tot_goals:.2f}골",
            f"승리 확률 {safe_away_win:.1f}%",
            f"{a_p1_val}골",
            f"{a_p2_val}골",
            f"{d_prob_val:.1f}%" if 'd_prob_val' in locals() else "0.0%"
        ],
        "단계별 산출 근거 및 푸아송 확률": [
            "기하평균 공수 교차 상쇄 결합 연산",
            "동급 A/B티어 최근 5경기 실전 평균",
            over_factor_desc if 'over_factor_desc' in locals() else "보정 없음",
            matrix_range if 'matrix_range' in locals() else "표준 범위",
            f"무승부 확률 {safe_draw:.1f}%",
            f"푸아송 확률 {p1_rate:.2f}% (5-2 결과 최적합)" if 'p1_rate' in locals() else "푸아송 확률 0.00%",
            f"푸아송 확률 {p2_rate:.2f}% (1순위 제외 최고 확률)" if 'p2_rate' in locals() else "푸아송 확률 0.00%",
            s3_calc_basis if 's3_calc_basis' in locals() else "-"
        ]
    })
    st.dataframe(ex6_df, use_container_width=True, hide_index=True)
# ==========================================
# 0단계 ~ 6단계 탭 영역 (기존 로직 그대로 유지)
# ==========================================

    # (생략 없이 기존 0단계 코드 유지)

# ==========================================
# 7번 탭: 요약 리포트 (Match Code 기반 대진별 멀티 비교 대시보드) - 3-2 완전 제거 및 순정 원복 버전
# ==========================================
with tabs[7]:
    st.markdown("### 📋 [규칙 7] 배트맨 프로젝트 마스터 규격 멀티 경기 비교 대시보드")
    st.markdown("0~6단계 화면에서 사용하는 **모든 기본 딕셔너리(`v3_details_dict`, `all_details_dict`, `country.json`)** 데이터가 엔진(`engine.py`)으로 주입되어 실시간 연동됩니다.")

    # 🚀 백엔드 엔진 임포트
    try:
        from engine import compute_match_prediction_master
        engine_available = True
    except Exception as e:
        engine_available = False
        st.error(f"⚠️ engine.py 모듈을 불러오는 중 오류가 발생했습니다: {e}")

    if "multi_selected_matches" not in st.session_state:
        st.session_state["multi_selected_matches"] = []

    # 📌 1. 패널 (경기 선택 및 담기)
    with st.expander("📌 [패널 열기/닫기] 단계별 경기 선택 및 담기", expanded=False):
        date_keys = list(daily_matches.keys()) if 'daily_matches' in globals() and daily_matches else []
        if date_keys:
            sel_date = st.selectbox("📅 1단계: 날짜를 선택하세요", date_keys, key="multi_tab_date_sel")
            matches_on_date = daily_matches.get(sel_date, [])
            
            if matches_on_date:
                available_leagues = sorted(list(set(m.get("league", "기타 리그") for m in matches_on_date)))
                sel_league = st.selectbox("🏆 2단계: 리그를 선택하세요", available_leagues, key="multi_tab_league_sel")
                
                league_filtered_matches = [m for m in matches_on_date if m.get("league", "기타 리그") == sel_league]
                
                if league_filtered_matches:
                    st.markdown(f"###### ⚽ [{sel_date} / {sel_league}] 분석할 경기를 여러 개 체크하세요")
                    temp_checked_matches = []
                    
                    for idx, m_item in enumerate(league_filtered_matches):
                        m_code = m_item.get('match_code', '')
                        m_time = m_item.get('time', '00:00')
                        h_t = m_item.get('home', '홈팀')
                        a_t = m_item.get('away', '원정팀')
                        
                        m_label = f"[{m_time}] {h_t} vs {a_t}"
                        item_to_add = m_item.copy()
                        item_to_add['date'] = sel_date
                        item_to_add['league'] = sel_league
                        
                        if st.checkbox(m_label, key=f"step_chk_{sel_date}_{sel_league}_{m_code}_{idx}"):
                            temp_checked_matches.append(item_to_add)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_b1, col_b2 = st.columns([1, 1])
                    with col_b1:
                        if st.button("📥 체크한 경기 목록에 담기", use_container_width=True):
                            for m in temp_checked_matches:
                                if m not in st.session_state["multi_selected_matches"]:
                                    st.session_state["multi_selected_matches"].append(m)
                            st.success("선택한 경기들이 비교 대시에 담겼습니다!")
                            st.rerun()
                    with col_b2:
                        if st.button("🗑️ 전체 비우기 (초기화)", use_container_width=True):
                            st.session_state["multi_selected_matches"] = []
                            st.rerun()
                else:
                    st.info("해당 리그에 속한 경기 데이터가 없습니다.")
            else:
                st.info("선택한 날짜에 등록된 경기 일정이 없습니다.")
        else:
            st.warning("⚠️ 로드된 경기 스케줄 데이터가 존재하지 않습니다.")

    # 📌 2. 담긴 대진 리스트 관리
    st.markdown("---")
    st.markdown("##### 🏟️ 현재 담긴 비교 대진 리스트")
    if not st.session_state["multi_selected_matches"]:
        st.info("아직 담긴 경기가 없습니다. 위 패널에서 경기를 담아주세요.")
    else:
        matches_to_keep = []
        for i, m_item in enumerate(st.session_state["multi_selected_matches"]):
            h_t = m_item.get('home', '홈')
            a_t = m_item.get('away', '원정')
            l_t = m_item.get('league', '리그')
            
            c_col1, c_col2 = st.columns([5, 1])
            with c_col1:
                st.markdown(f"- **{h_t} vs {a_t}** ({l_t})")
            with c_col2:
                if st.button("❌ 빼기", key=f"remove_step_item_{i}", use_container_width=True):
                    continue 
            matches_to_keep.append(m_item)
        
        if len(matches_to_keep) != len(st.session_state["multi_selected_matches"]):
            st.session_state["multi_selected_matches"] = matches_to_keep
            st.rerun()

        # 🚀 3. 대진별 독립 수리 엔진 연산 및 통합 비교 표 (기본 3번 및 v3 기준)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 🏆 담긴 경기 대진별 독립 수리 엔진 연산 및 통합 비교 표")

        multi_summary_data = []
        engine_results_store = {} 

        for m_item in st.session_state["multi_selected_matches"]:
            h_name = str(m_item.get('home', '홈')).strip()
            a_name = str(m_item.get('away', '원정')).strip()
            league_name = m_item.get('league', '-')
            m_code = str(m_item.get('match_code', '')).strip()
            
            merged_target_detail = {
                "head_info": {},
                "meta_details": {
                    "rankings": [],
                    "recent_form": {"home_summary": {}, "away_summary": {}, "home_matches": [], "away_matches": []},
                    "stadium_form": {"home_matches": [], "away_matches": []},
                    "h2h": {"summary": [], "matches": []},
                    "fixtures": {"home": [], "away": []},
                    "home_squad_changes": [],
                    "away_squad_changes": []
                }
            }

            source_candidates = []
            
            if m_code and m_code in v3_details_dict:
                source_candidates.append(v3_details_dict[m_code])
            if m_code and m_code in all_details_dict:
                source_candidates.append(all_details_dict[m_code])
            
            clean_h = h_name.replace(" ", "").lower()
            clean_a = a_name.replace(" ", "").lower()
            
            dicts_to_search = [v3_details_dict, all_details_dict]
            
            for dict_obj in dicts_to_search:
                for k, v in dict_obj.items():
                    v_home = str(v.get("home", "")).strip().replace(" ", "").lower()
                    v_away = str(v.get("away", "")).strip().replace(" ", "").lower()
                    if v_home == clean_h and v_away == clean_a:
                        if v not in source_candidates:
                            source_candidates.append(v)

            for src in source_candidates:
                if isinstance(src.get("head_info"), dict):
                    merged_target_detail["head_info"].update(src["head_info"])
                
                src_meta = src.get("meta_details", {})
                if isinstance(src_meta, dict):
                    if src_meta.get("rankings"):
                        merged_target_detail["meta_details"]["rankings"] = src_meta["rankings"]
                    
                    src_rf = src_meta.get("recent_form", {})
                    if src_rf:
                        if src_rf.get("home_matches"): merged_target_detail["meta_details"]["recent_form"]["home_matches"] = src_rf["home_matches"]
                        if src_rf.get("away_matches"): merged_target_detail["meta_details"]["recent_form"]["away_matches"] = src_rf["away_matches"]
                        if src_rf.get("home_summary"): merged_target_detail["meta_details"]["recent_form"]["home_summary"] = src_rf["home_summary"]
                        if src_rf.get("away_summary"): merged_target_detail["meta_details"]["recent_form"]["away_summary"] = src_rf["away_summary"]

                    src_sf = src_meta.get("stadium_form", {})
                    if src_sf:
                        merged_target_detail["meta_details"]["stadium_form"] = src_sf

                    src_h2h = src_meta.get("h2h", {})
                    if src_h2h:
                        if src_h2h.get("matches"): merged_target_detail["meta_details"]["h2h"]["matches"] = src_h2h["matches"]
                        if src_h2h.get("summary"): merged_target_detail["meta_details"]["h2h"]["summary"] = src_h2h["summary"]

                    src_fix = src_meta.get("fixtures", {})
                    if src_fix:
                        if src_fix.get("home"): merged_target_detail["meta_details"]["fixtures"]["home"] = src_fix["home"]
                        if src_fix.get("away"): merged_target_detail["meta_details"]["fixtures"]["away"] = src_fix["away"]

                    if src_meta.get("home_squad_changes"):
                        merged_target_detail["meta_details"]["home_squad_changes"] = src_meta["home_squad_changes"]
                    if src_meta.get("away_squad_changes"):
                        merged_target_detail["meta_details"]["away_squad_changes"] = src_meta["away_squad_changes"]

                for key_name in ["h_gpg", "h_cpg", "a_gpg", "a_cpg", "h_agf", "a_agf"]:
                    if key_name in src:
                        merged_target_detail[key_name] = src[key_name]

            match_key = f"{h_name} vs {a_name}"

            if engine_available and source_candidates:
                res = compute_match_prediction_master(
                    target_detail=merged_target_detail,
                    home_name=h_name,
                    away_name=a_name,
                    league_name=league_name
                )
                
                if res.get("status"):
                    engine_results_store[match_key] = {
                        "res": res,
                        "target_detail": merged_target_detail,
                        "m_item": m_item
                    }
                    
                    h_win = res.get("home_win_pct", 0.0)
                    draw = res.get("draw_pct", 0.0)
                    a_win = res.get("away_win_pct", 0.0)
                    prob_str = f"홈 {h_win:.1f}% / 무 {draw:.1f}% / 원정 {a_win:.1f}%"
                    
                    s1 = f"{res.get('score_1st')} ({res.get('p1_rate'):.1f}%)"
                    s2 = f"{res.get('score_2nd')} ({res.get('p2_rate'):.1f}%)"
                    s3 = res.get("s3_desc", "-")
                    status_lbl = "✅ 연산 완료"
                else:
                    prob_str = "-"
                    s1, s2, s3 = "-", "-", "-"
                    status_lbl = f"⚠️ 연산 실패 ({res.get('msg', '데이터 부족')})"
            else:
                prob_str = "-"
                s1, s2, s3 = "-", "-", "-"
                status_lbl = "⚠️ 정밀 데이터 미수집"

            multi_summary_data.append({
                "대진 경기": match_key,
                "리그": league_name,
                "상태": status_lbl,
                "승무패 수리 확률": prob_str,
                "🥇 1순위 (최적합)": s1,
                "🥈 2순위 (차선책)": s2,
                "🥉 3순위 (대안책)": s3
            })
        
        df_multi_res = pd.DataFrame(multi_summary_data)
        st.dataframe(df_multi_res, use_container_width=True, hide_index=True)

        # ==================================================================
        # 🔍 [디버그 센터] 경기별 세부 가중치 및 0~6단계 연산 내역 상세보기
        # ==================================================================
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 🔍 [디버그 센터] 경기별 세부 가중치 및 0~6단계 연산 내역 상세보기")
        st.markdown("각 대진별로 수집된 메타 데이터와 적용된 규칙별 보정치 가중치를 펼쳐서 오차 원인을 정밀하게 진단하세요.")

        def format_weight_val(v):
            try:
                f_v = float(v)
            except:
                f_v = 0.0
            if f_v == 0.0:
                return ":red[+0.0%]"
            else:
                return f"**{f_v:+.1f}%**"

        for m_item in st.session_state["multi_selected_matches"]:
            h_name = str(m_item.get('home', '홈')).strip()
            a_name = str(m_item.get('away', '원정')).strip()
            match_key = f"{h_name} vs {a_name}"
            
            with st.expander(f"📌 [상세보기] {match_key} 세부 가중치 및 연산 로그", expanded=False):
                if match_key in engine_results_store:
                    store_data = engine_results_store[match_key]
                    debug_res = store_data["res"]
                    raw_detail = store_data["target_detail"]
                    meta_dbg = raw_detail.get("meta_details", {})
                    
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        st.markdown("###### 🏠 홈팀 연산 요약 및 가중치")
                        st.markdown(f"- **기본 기대 득실 (GPG/CPG):** {raw_detail.get('h_gpg', 1.2)} / {raw_detail.get('h_cpg', 1.1)}")
                        st.markdown(f"- **최종 승무패 확률:** 홈 승률 **{debug_res.get('home_win_pct', 0):.1f}%**")
                        st.markdown(f"- **예측 1순위 스코어:** `{debug_res.get('score_1st')}` ({debug_res.get('p1_rate', 0):.1f}%)")
                    
                    with col_d2:
                        st.markdown("###### ✈️ 원정팀 연산 요약 및 가중치")
                        st.markdown(f"- **기본 기대 득실 (GPG/CPG):** {raw_detail.get('a_gpg', 1.1)} / {raw_detail.get('a_cpg', 1.2)}")
                        st.markdown(f"- **최종 승무패 확률:** 원정 승률 **{debug_res.get('away_win_pct', 0):.1f}%**")
                        st.markdown(f"- **예측 2순위 스코어:** `{debug_res.get('score_2nd')}` ({debug_res.get('p2_rate', 0):.1f}%)")
                    
                    st.markdown("---")
                    st.markdown("###### 🎛️ [항목별 세부 가중치 산출 내역 (공격 / 방어)]")
                    w_col1, w_col2 = st.columns(2)
                    
                    with w_col1:
                        st.markdown("**🏠 홈팀 단계별 보정 백분율**")
                        st.markdown(f"- **0단계 (Country):** {format_weight_val(debug_res.get('h_step0_atk', 0.0))} / {format_weight_val(debug_res.get('h_step0_def', 0.0))}")
                        st.markdown(f"- **규칙 1 (LIFO):** {format_weight_val(debug_res.get('h_r1_atk', 0.0))} / {format_weight_val(debug_res.get('h_r1_def', 0.0))}")
                        st.markdown(f"- **규칙 2 (구장 Shift):** {format_weight_val(debug_res.get('h_r2_atk', 0.0))} / {format_weight_val(debug_res.get('h_r2_def', 0.0))}")
                        st.markdown(f"- **규칙 3 (누수·피로):** {format_weight_val(debug_res.get('h_r3_tot_atk', 0.0))} / {format_weight_val(debug_res.get('h_r3_tot_def', 0.0))}")
                        st.markdown(f"- **규칙 4 (H2H 상성):** {format_weight_val(debug_res.get('h_r4_atk', 0.0))} / {format_weight_val(debug_res.get('h_r4_def', 0.0))}")
                        st.markdown(f"- **총 누적 보정치:** {format_weight_val(debug_res.get('h_tot_atk_pct', 0.0))} / {format_weight_val(debug_res.get('h_tot_def_pct', 0.0))}")
                    
                    with w_col2:
                        st.markdown("**✈️ 원정팀 단계별 보정 백분율**")
                        st.markdown(f"- **0단계 (Country):** {format_weight_val(debug_res.get('a_step0_atk', 0.0))} / {format_weight_val(debug_res.get('a_step0_def', 0.0))}")
                        st.markdown(f"- **규칙 1 (LIFO):** {format_weight_val(debug_res.get('a_r1_atk', 0.0))} / {format_weight_val(debug_res.get('a_r1_def', 0.0))}")
                        st.markdown(f"- **규칙 2 (구장 Shift):** {format_weight_val(debug_res.get('a_r2_atk', 0.0))} / {format_weight_val(debug_res.get('a_r2_def', 0.0))}")
                        st.markdown(f"- **규칙 3 (누수·피로):** {format_weight_val(debug_res.get('a_r3_tot_atk', 0.0))} / {format_weight_val(debug_res.get('a_r3_tot_def', 0.0))}")
                        st.markdown(f"- **규칙 4 (H2H 상성):** {format_weight_val(debug_res.get('a_r4_atk', 0.0))} / {format_weight_val(debug_res.get('a_r4_def', 0.0))}")
                        st.markdown(f"- **총 누적 보정치:** {format_weight_val(debug_res.get('a_tot_atk_pct', 0.0))} / {format_weight_val(debug_res.get('a_tot_def_pct', 0.0))}")

                    st.markdown("---")
                    st.markdown("###### 📊 원본 메타 데이터 수집 현황 (오차 진단용)")
                    m_dbg_col1, m_dbg_col2, m_dbg_col3, m_dbg_col4 = st.columns(4)
                    with m_dbg_col1:
                        st.metric("순위표(Rankings)", f"{len(meta_dbg.get('rankings', []))}개")
                    with m_dbg_col2:
                        rf_h = len(meta_dbg.get('recent_form', {}).get('home_matches', []))
                        rf_a = len(meta_dbg.get('recent_form', {}).get('away_matches', []))
                        st.metric("LIFO 최근 경기", f"홈 {rf_h} / 원정 {rf_a}")
                    with m_dbg_col3:
                        st.metric("맞대결(H2H) 전적", f"{len(meta_dbg.get('h2h', {}).get('matches', []))}경기")
                    with m_dbg_col4:
                        sq_h = len(meta_dbg.get('home_squad_changes', []))
                        sq_a = len(meta_dbg.get('away_squad_changes', []))
                        st.metric("선수 누수(Squad)", f"홈 {sq_h} / 원정 {sq_a}")
                    
                    st.markdown(f"**💡 3차 차점 분석 묘사:** {debug_res.get('s3_desc', '-')}")
                else:
                    st.warning("⚠️ 해당 대진의 연산 결과 데이터가 존재하지 않습니다. (정밀 데이터 미수집 상태)")
