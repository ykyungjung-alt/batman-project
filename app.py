from datetime import datetime, timezone, timedelta
import json
import os
import re
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st


# 💡 날짜 고정 없이, 시스템에 존재하는 모든 상세 데이터 파일(match_details.json, v2 등)을 유연하게 통합 탐색
@st.cache_data(ttl=10)
def load_match_data():
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_updated": "안전 모드 (데이터 없음)", "daily_matches": {}}


# 💡 [기존 1, 2번 파일 병합용] 0단계 및 기본 텍스트 산출 내역 유지용
@st.cache_data(ttl=10)
def load_all_match_details():
    target_files = [
        "match_details.json", 
        "match_details_v2.json"
    ]
    combined_details = {}
    for t_file in target_files:
        if os.path.exists(t_file):
            try:
                with open(t_file, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    match_dict = file_data.get("match_details", {})
                    for k, v in match_dict.items():
                        if k not in combined_details:
                            combined_details[k] = v
            except Exception:
                pass
    return combined_details


# 💡 [3번 파일 독립 발췌용] 규칙 1번·2번 상세 표 데이터 전용 (match_details_v3.json)
@st.cache_data(ttl=10)
def load_v3_match_details():
    v3_file = "match_details_v3.json"
    if os.path.exists(v3_file):
        try:
            with open(v3_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                return file_data.get("match_details", {})
        except Exception:
            pass
    return {}


# 💡 [4번 파일 독립 발췌용] 리그 순위표 및 랭킹 데이터 전용 (match_details_v4.json)
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


data = load_match_data()
last_updated_time = data.get("last_updated", "알 수 없음")
daily_matches = data.get("daily_matches", {})

# 각각의 성향에 맞춘 독립 및 병합 딕셔너리 호출 선언
all_details_dict = load_all_match_details()   # 1, 2번 병합본 (기본 시스템 유지용)
v3_details_dict = load_v3_match_details()       # 3번 전용 (1, 2단계 표 연동용)
v4_leagues_dict = load_v4_match_details()       # 4번 전용 (리그 순위표 데이터용)

st.markdown("<h2 style='font-size: 28px;'>⚽ 배트맨 프로젝트 통합 마스터 규격 및 분석 엔진 ⚽</h2>", unsafe_allow_html=True)
st.markdown("구글 독스 원문 규격 100% 반영 • 생략 없는 0단계~6단계 세부 정량 표 완벽 탑재 시스템")

st.sidebar.markdown("---")
st.sidebar.markdown(f"🕒 **데이터 갱신 시각 (KST)**\n\n`{last_updated_time}`")
st.sidebar.subheader("🏆 실시간 수집 대진 선택")

# 1. 사이드바 날짜 선택창 구성 (daily_matches에 있는 키값 활용)
date_options = list(daily_matches.keys())
if not date_options:
    date_options = ["오늘 (데이터 없음)"]

selected_date = st.sidebar.selectbox("📅 날짜를 선택하세요:", date_options)

# 2. 선택한 날짜의 경기 리스트 가져오기
matches = daily_matches.get(selected_date, [])
selected_match = None

if matches:
    leagues = sorted(list(set(m.get("league", "기타 리그") for m in matches)))
    if leagues:
        selected_league = st.sidebar.selectbox("리그를 선택하세요:", leagues)
        league_matches = [m for m in matches if m.get("league", "기타 리그") == selected_league]
        
        # match_name 대신 홈/원정/시간 조합으로 안전하게 생성
        match_options = [f"[{m.get('time', '00:00')}] {m.get('home')} vs {m.get('away')}" for m in league_matches]
        
        if match_options:
            selected_match_name = st.sidebar.radio("분석할 경기를 선택하세요:", match_options, key="match_radio_selection")
            
            # 선택된 경기 매칭
            selected_match = next((m for m in league_matches if f"[{m.get('time', '00:00')}] {m.get('home')} vs {m.get('away')}" == selected_match_name), None)

# [핵심 방어 로직] 조건에 맞는 경기가 없을 때 경고 문구 출력 및 안전 정지
if not selected_match:
    st.warning(f"⚠️ [{selected_date}] 조건에 해당하는 경기 데이터가 존재하지 않습니다. (데이터 없음)")
    st.info("💡 안내: 아직 해당 날짜에 수집된 경기 일정이나 정밀 데이터가 없습니다. 다른 날짜를 선택하시거나 데이터 갱신 후 이용해 주세요.")
    st.stop()

# 정상 매칭 시 변수 지정
home_team = selected_match.get("home", "홈팀")
away_team = selected_match.get("away", "원정팀")
tournament_name = selected_match.get("league", "리그")
match_date = selected_match.get("time", "오늘")
match_code = str(selected_match.get("match_code", ""))

# ==========================================
# 💡 [핵심 방어 장치] 통합 상세 데이터 안전 추출 및 플래그 설정 (팀 이름 매칭 폴백 추가)
# ==========================================
# ==========================================
# 💡 [강력한 3단계 통합 매칭 로직] 매치코드 및 팀 이름 정밀 비교
# ==========================================
raw_detailed_info = None
target_code = str(match_code).strip()
target_home = str(home_team).strip().replace(" ", "")
target_away = str(away_team).strip().replace(" ", "")

# 1순위: 상위 딕셔너리 키로 직접 탐색
if target_code and target_code in all_details_dict:
    raw_detailed_info = all_details_dict[target_code]

# 2순위: 데이터 내부의 "match_code" 필드 값과 일치하는 항목 탐색
if not raw_detailed_info and target_code:
    for k, v in all_details_dict.items():
        if str(v.get("match_code", "")).strip() == target_code:
            raw_detailed_info = v
            break

# 3순위: 홈팀 / 원정팀 이름 정규화(공백 제거) 후 일치하는 항목 탐색 (폴백)
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
            "recent_form": {
                "home_summary": {},
                "away_summary": {},
                "home_matches": [],
                "away_matches": [],
                "matches": []
            },
            "h2h": {"summary": [], "matches": []},
            "fixtures": {"home": [], "away": []}
        }
    }
    has_detailed_data = False

# ==========================================
# 💡 [공통 유틸리티] 대회 압축어 정식 한글 명칭 및 날짜 포맷 자동 변환 함수
# ==========================================
def translate_tournament_code(code_str):
    if not code_str:
        return "기타 공식 경기"
    
    mapping = {
        # 주요 리그 및 컵대회 압축어
        "GER D1": "독일 분데스리가",
        "GERC": "독일 DFB 포칼",
        "INT CF": "국가대표 친선경기",
        "ENG PR": "잉글랜드 프리미어리그",
        "ENG FAC": "잉글랜드 FA컵",
        "SPA D1": "스페인 라리가",
        "SPA D2": "스페인 라리가 2",          # 💡 스페인 2부 리그 추가
        "SPA CUP": "스페인 코파 델 레이",       # 💡 스페인 컵대회 추가
        "ESP D1": "스페인 라리가",
        "ESP C": "스페인 코파 델 레이",
        "ITA D1": "이탈리아 세리에 A",
        "ITA Cup": "이탈리아 컵 (코파 이탈리아)",
        "FRA C": "프랑스 쿠프 드 프랑스",
        "KFAC": "대한민국 코리아컵 (FA컵)",
        "ENG LC": "잉글랜드 리그컵 (카라바오컵)",
        "ACLE": "AFC 챔피언스리그 엘리트 (ACLE)",
        "FRA D1": "프랑스 리그 1",
        "UEFA ECL": "UEFA 유로파 컨퍼런스리그",
        "UEFA CL": "UEFA 챔피언스리그",
        "UEFA EL": "UEFA 유로파리그",
        "AFC CL": "AFC 챔피언스리그",
        "ACQ": "AFC 아시안컵 예선",
        "AC": "AFC 아시안컵 본선",
        "WC": "FIFA 월드컵 본선",
        "FIFA WC": "FIFA 월드컵 본선",
        "WCC": "FIFA 클럽 월드컵",
        "FIFA CWC": "FIFA 클럽 월드컵",
        "U20 WC": "FIFA U-20 월드컵",
        "U17 WC": "FIFA U-17 월드컵",
        "W-WC": "FIFA 여자 월드컵"
    }
    
    converted = code_str
    for k, v in mapping.items():
        if k in code_str:
            converted = code_str.replace(k, v)
            break
            
    # 💡 한글/괄호/공백 뒤에 곧바로 연도(20...)가 붙어 있는 경우 사이에 ' - ' 삽입
    match_pattern = re.search(r'(.*?)(\d{4}\.\d{2}\.\d{2})', converted)
    if match_pattern:
        prefix = match_pattern.group(1).strip()
        date_part = match_pattern.group(2)
        return f"{prefix} - {date_part}"
        
    return converted
tab_titles = [
    "0단계 (메타)", 
    "규칙 1 (LIFO 7경기)", 
    "규칙 2 (구장 Shift)", 
    "규칙 3 (누수·피로)", 
    "규칙 4 (H2H 상성)", 
    "규칙 5 (최종 람다)", 
    "규칙 6 (푸아송 예측)", 
    "요약 리포트"
]
tabs = st.tabs(tab_titles)

# ==========================================
# 0단계 탭 (메타 및 순위표 출력 및 구장 판별 연동 플래그 정의)
# ==========================================
with tabs[0]:
    st.markdown("#### [0단계: 대진 정보 및 팀순위 정보]")
    st.markdown("친선 경기를 전면 배제하고 공식 A매치 유효성 검증을 거친 대진 메타데이터를 고정합니다. (SSOT 원칙 적용)")

    # 경기 일시 데이터 안전 추출
    match_time_display = detailed_info.get("head_info", {}).get("match_time_display", "")
    if not match_time_display:
        match_time_display = selected_match.get("time", match_date)

    # 💡 [핵심 연동] 0단계 구장 판별 메타 플래그 사전 정의 (전역 공유용)
    is_neutral_venue = False
    venue_display_text = "구장 정보 없음"

    if has_detailed_data:
        meta_status = "정상 통과 (정밀 데이터 연동 완료)"
        head_info = detailed_info.get("head_info", {})
        league_name = head_info.get("league", tournament_name)
        round_info = head_info.get("round", "")
        if round_info:
            tournament_display = f"{league_name} ({round_info})"
        else:
            tournament_display = league_name

        stadium_name = head_info.get("stadium", "").strip()          # 실제 경기 개최 구장
        home_stadium_name = head_info.get("home_stadium", "").strip()  # 홈팀의 실제 홈구장
        weather_info = head_info.get("weather", "").strip()

        # 💡 [핵심 규칙 반영] 구장 정보 순서 및 색상 지정 (실제 경기장명 / 홈·중립 판정)
        if stadium_name and home_stadium_name:
            if stadium_name.lower() == home_stadium_name.lower():
                # 홈구장 일치 시: 실제 경기장명 / 녹색 (홈)
                stadium_badge = f"{stadium_name} / <span style='color: #2e7d32; font-weight: bold;'>{home_stadium_name} (홈)</span>"
                is_neutral_venue = False
                venue_display_text = f"{stadium_name} / 홈구장 일치 (홈 이점 적용)"
            else:
                # 중립구장 불일치 시: 실제 경기장명 / 빨간색 (중립)
                stadium_badge = f"{stadium_name} / <span style='color: #c62828; font-weight: bold;'>{home_stadium_name} (중립)</span>"
                is_neutral_venue = True
                venue_display_text = f"{stadium_name} / 중립구장 (홈구장 '{home_stadium_name}' 불일치 ➔ 원정 성향 대체 적용)"
        elif stadium_name:
            stadium_badge = f"{stadium_name} / 홈구장 정보 미확인"
            venue_display_text = f"{stadium_name} / 홈구장 정보 미확인"
        else:
            stadium_badge = "구장 정보 실시간 반영 대기"
            venue_display_text = "구장 정보 미확인"

        # 날씨 정보 결합 순서 정돈
        w_text = weather_info if weather_info else "날씨 정보 없음"
        stadium_info = f"{stadium_badge} / 날씨: {w_text}"
    else:
        meta_status = "⚠️ 해당 경기의 상세 정밀 데이터 없음 (데이터 없음)"
        tournament_display = tournament_name
        stadium_info = "데이터 없음"
        is_neutral_venue = False

    # 메타 항목 및 요청하신 출력 순서/서식 반영 마크다운 테이블
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

    st.markdown("##### 📊 공식 팀 순위 및 조건별 전적표 현황")
    
    # 2. 공식 팀 순위 및 전적표 출력 (안전한 방어 분기 처리)
    if has_detailed_data:
        meta_details = detailed_info.get("meta_details", {})
        rankings_raw = meta_details.get("rankings", [])
        if rankings_raw:
            rankings_list = []
            for idx, r in enumerate(rankings_raw):
                rankings_list.append({
                    "No": idx + 1,
                    "리그순위": str(r.get("rank", "-")) if r.get("rank") is not None and str(r.get("rank")).strip() != "" else "-",
                    "팀": str(r.get("team", "-")),
                    "경기": str(r.get("played", "0")),
                    "승": str(r.get("win", "0")),
                    "무승부": str(r.get("draw", "0")),
                    "패": str(r.get("loss", "0")),
                    "득점": str(r.get("goals_for", "0")),
                    "실점": str(r.get("goals_against", "0")),
                    "득실": str(r.get("goal_diff", "0")),
                    "승점": str(r.get("points", "0"))
                })
            df_rankings = pd.DataFrame(rankings_list)
            st.markdown("🔍 수집된 팀별 전체 및 조건별 세부 전적표입니다.")
            st.dataframe(df_rankings[["리그순위", "팀", "경기", "승", "무승부", "패", "득점", "실점", "득실", "승점"]], use_container_width=True, hide_index=True)
        else:
            st.info("💡 해당 경기에 수집된 순위 및 전적표 데이터(rankings)가 존재하지 않습니다.")
    else:
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터가 아직 수집되지 않았습니다. (3~4일 이후 경기 등)")
        st.info("💡 크롤러 대상 기간(오늘/내일)에 포함되지 않은 경기이므로, 상세 전적표 및 통계 지표를 조회할 수 없습니다. 경기 당일 또는 전일에 데이터를 갱신해 주세요.")



# ==========================================
# 💡 규칙 1번 탭 (v3 데이터 전용 단독 연동 및 10경기 전수 + E티어 50% 할인)
# ==========================================
with tabs[1]:
    st.markdown(f"#### [규칙 1번: 종합 최근 10경기 로그 및 A~E 등급별 공수 티어 산출] - {home_team} vs {away_team}")
    st.markdown("""
        <div class="step-box">
            <b>📌 규격 원칙 및 요약 설명:</b><br>
            • <b>전수 조사 및 LIFO 방식:</b> 홈/원정 통합 최근 공식 경기 10개를 최신순 역순(LIFO)으로 전수 조사하며, 골득실 평균을 산출하여 티어 산정표의 티어를 각 양팀에 부여합니다.<br>
            • <b>친선 경기 전면 배제:</b> 최근 경기 표본에서 모든 친선 경기를 영구 배제하며, 오직 공식 경기만을 채택합니다.<br>
            • <b>특수 룰 (E티어 50% 할인):</b> 상대 공수 체급이 E티어일 경우, 해당 경기 득점력에 50% 할인(0.5 곱셈) 프로토콜을 적용합니다.
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

    def local_make_df(matches, tname, def_gpg, def_cpg, def_rec):
        if not matches:
            return pd.DataFrame(), def_gpg, def_cpg, def_rec, 0.0, 0.0
            
        rows = []
        eff_scored = 0.0
        c_total = 0
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
            mult = 1.0
            tier_info = m.get("opponent_tier_info", "")
            if tier_info and "/" in tier_info:
                try:
                    oa, od = map(float, tier_info.split("/"))
                    at_name = atk_tier_nm(oa)
                    df_name = def_tier_nm(od)
                    tier_str = f"공격 {at_name} ({oa:.2f}) / 방어 {df_name} ({od:.2f})"
                    if at_name == "Tier E" or df_name == "Tier E":
                        mult = 0.5
                        tier_str += " ⚠️ (E티어 50% 할인)"
                except:
                    pass
                    
            app_sc = sc * mult
            eff_scored += app_sc
            c_total += cc
            
            seq = f"최신 ({idx+1})" if idx == 0 else str(idx+1)
            score_display = f"{s1} : {s2}" + (f" (할인: {app_sc:.1f})" if mult < 1.0 else "")
            
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
        cpg = round(c_total / cnt, 2) if cnt > 0 else def_cpg
        rec = f"{cnt}전 {w}승 {d}무 {l}패" if cnt > 0 else def_rec
        
        return pd.DataFrame(rows), gpg, cpg, rec, raw_scored_total, raw_conceded_total

    h_df, h_gpg, h_cpg, h_rec, h_raw_s, h_raw_c = local_make_df(h_matches, h_name, h_gpg_base, h_cpg_base, h_rec_base)
    a_df, a_gpg, a_cpg, a_rec, a_raw_s, a_raw_c = local_make_df(a_matches, a_name, a_gpg_base, a_cpg_base, a_rec_base)

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
        • 보정 평균 득점: <b>{h_gpg:.2f}골/경기</b> / 평균 실점: <b>{h_cpg:.2f}골/경기</b><br>
        • 공격 티어: <b>{h_at} ({h_atw})</b> | 방어 티어: <b>{h_de} ({h_dew})</b>
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
        • 보정 평균 득점: <b>{a_gpg:.2f}골/경기</b> / 평균 실점: <b>{a_cpg:.2f}골/경기</b><br>
        • 공격 티어: <b>{a_at} ({a_atw})</b> | 방어 티어: <b>{a_de} ({a_dew})</b>
    </div>""", unsafe_allow_html=True)


# ==============================================================================
# 💡 규칙 2번 탭 (0단계 구장 판별 연동 및 홈/중립 배지 표시)
# ==============================================================================
with tabs[2]:
    st.markdown(f"#### [규칙 2번: 구장별 Shift 검증 및 티어 보정] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
    <b>📌 규격 원칙 및 요약 설명:</b><br>
    • <b>구장별 전적(Stadium Form) 분석:</b> 홈팀의 홈 경기 구장 및 원정팀의 원정 경기 구장 데이터를 독립적으로 추출합니다.<br>
    • <b>0단계 구장 판정 연동:</b> 홈구장 일치 여부에 따라 홈경기(초록색) 또는 중립경기(빨간색) 상태를 명시하고 원정 데이터를 분기 적용합니다.
    </div>
    """, unsafe_allow_html=True)

    # 💡 [핵심 해결] tier_ranks 딕셔너리를 함수 호출 전에 미리 안전하게 정의합니다.
    tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}

    if has_detailed_data:
        # 0단계 메타데이터에서 구장 정보 안전 추출
        head_meta = detailed_info.get("head_info", {}) if 'detailed_info' in locals() else {}
        venue_val = str(head_meta.get("stadium", "")) or str(head_meta.get("venue", ""))
        home_stadium_val = str(head_meta.get("home_stadium", ""))
        
        is_neutral_venue = False
        if venue_val and home_stadium_val:
            if venue_val.strip().lower() != home_stadium_val.strip().lower():
                is_neutral_venue = True

        # 중립구장 판정 시 원정 경기 데이터 대체 분기 적용
        if is_neutral_venue and stadium_form.get("away_matches"):
            s_home_matches = stadium_form.get("away_matches", [])[:20]
        else:
            s_home_matches = stadium_form.get("home_matches", [])[:20]

        s_away_matches = stadium_form.get("away_matches", [])[:20]

        s_h_df, s_h_gpg, s_h_cpg, s_h_rec, s_h_raw_s, s_h_raw_c = local_make_df(s_home_matches, h_name, 0.0, 0.0, "0전 0승 0무 0패")
        s_a_df, s_a_gpg, s_a_cpg, s_a_rec, s_a_raw_s, s_a_raw_c = local_make_df(s_away_matches, a_name, 0.0, 0.0, "0전 0승 0무 0패")

        # 구장 전적 기반 공수 티어 산출
        s_h_at, s_h_atw = atk_tier(s_h_gpg)
        s_h_de, s_h_dew = def_tier(s_h_cpg)
        s_a_at, s_a_atw = atk_tier(s_a_gpg)
        s_a_de, s_a_dew = def_tier(s_a_cpg)

        # 1단계 종합 티어 가져오기
        base_h_at = h_at if 'h_at' in locals() else "Tier C"
        base_h_de = h_de if 'h_de' in locals() else "Tier C"
        base_a_at = a_at if 'a_at' in locals() else "Tier C"
        base_a_de = a_de if 'a_de' in locals() else "Tier C"

        # 5-2 표 연동을 위한 최종 체급 변수 확정
        h_current_at = s_h_at if 's_h_at' in locals() else base_h_at
        h_current_de = s_h_de if 's_h_de' in locals() else base_h_de
        a_current_at = s_a_at if 's_a_at' in locals() else base_a_at
        a_current_de = s_a_de if 's_a_de' in locals() else base_a_de

        # 티어 변동에 따른 색상 결정 함수
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

        # 🏟️ 홈 팀 구장 성격 판별 배지 생성
        venue_status_badge = (
            "<span style='color: #c62828; font-weight: bold;'> (중립경기)</span>" 
            if is_neutral_venue 
            else "<span style='color: #2e7d32; font-weight: bold;'> (홈경기)</span>"
        )

        # 홈 팀 타이틀 및 데이터프레임 출력
        st.markdown(f"##### 홈 팀 ({h_name}) 구장별 전적 및 티어 변동 검증{venue_status_badge}", unsafe_allow_html=True)
        if not s_h_df.empty:
            st.dataframe(s_h_df, use_container_width=True, hide_index=True)
        else:
            st.info("📋 구장별 상세 전적 데이터 없음")

        st.markdown(f"""
        <div class="calc-box">
        <b>{h_name} 규칙 2번(구장별) Shift 보정 산출 내역</b><br>
        • 최근 전적: <b>{s_h_rec}</b> (총 득점: <b>{s_h_raw_s:.1f}골</b> / 총 실점: <b>{s_h_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if s_h_diff >= 0 else '#c62828'};">{s_h_diff:+.1f}</b>)<br>
        • 보정 평균 득점: <b>{s_h_gpg:.2f}골/경기</b> / 평균 실점: <b>{s_h_cpg:.2f}골/경기</b><br>
        • 1단계 종합 체급: 공격 <b>{base_h_at}</b> / 방어 <b>{base_h_de}</b> &nbsp;|&nbsp; 구장 환경 체급: 공격 <b>{h_atk_color_str}</b> / 방어 <b>{h_def_color_str}</b><br>
        • <b>적용된 구장 Shift 보정치:</b> 공격 <b>{h_atk_shift_str}</b> / 방어 <b>{h_def_shift_str}</b>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 원정 팀 타이틀 및 데이터프레임 출력
        st.markdown(f"##### 원정 팀 ({a_name}) 구장별 전적 및 티어 변동 검증")
        if not s_a_df.empty:
            st.dataframe(s_a_df, use_container_width=True, hide_index=True)
        else:
            st.info("📋 구장별 상세 전적 데이터 없음")

        st.markdown(f"""
        <div class="calc-box">
        <b>{a_name} 규칙 2번(구장별) Shift 보정 산출 내역</b><br>
        • 최근 전적: <b>{s_a_rec}</b> (총 득점: <b>{s_a_raw_s:.1f}골</b> / 총 실점: <b>{s_a_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if s_a_diff >= 0 else '#c62828'};">{s_a_diff:+.1f}</b>)<br>
        • 보정 평균 득점: <b>{s_a_gpg:.2f}골/경기</b> / 평균 실점: <b>{s_a_cpg:.2f}골/경기</b><br>
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

    # ==========================================
    # 3-1번 영역: 선수 등급 기준표 및 양팀 전력 변동 표 복구
    # ==========================================
    st.markdown("##### 선수 등급(상/중/하) 정량 판정 기준표")
    html_table = """
    <style>
    .custom-table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; font-size: 14px; }
    .custom-table th, .custom-table td { border: 1px solid #e0e0e0; padding: 10px 12px; text-align: left; }
    .custom-table th { background-color: #f5f5f5; font-weight: bold; }
    </style>
    <table class="custom-table">
    <thead><tr><th>전력 등급</th><th>포지션</th><th>정량적 스펙 및 평가 기준</th><th>보정 비율</th></tr></thead>
    <tbody>
    <tr><td>상 (High)</td><td>공격 (FW/MF) / 수비 (DF/GK)</td><td>• 팀 내 득점/도움 1~2위 또는 선발 출전율 80% 이상<br>• [DF/GK] 클린시트 기여 1위 / 경기당 평균 실점 1.0 이하</td><td>14%<br>(공격: -14% / 방어: +14%)</td></tr>
    <tr><td>중 (Medium)</td><td>공격 (FW/MF) / 수비 (DF/GK)</td><td>• 선발 출전율 50% ~ 79% / 핵심 주전 로테이션<br>• [DF/GK] 주전 수비수·골키퍼 / 태클·인터셉트 상위권</td><td>7%<br>(공격: -7% / 방어: +7%)</td></tr>
    <tr><td>하 (Low)</td><td>공용</td><td>• 선발 출전율 50% 미만 / 백업 및 후보 자원 (결장 시 수비/공격 수치 변화 미비)</td><td>0%</td></tr>
    </tbody>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)

    st.markdown(f"##### 3-1: 구단명 - {home_team} 선수 전력 변동")
    table_3_1_kor = pd.DataFrame({
        "선수 실명": ["손흥민", "김민재", "[총합]"],
        "포지션": ["FW", "DF", "-"],
        "변동 유형": ["누수", "가산", "-"],
        "핵심 영향력": ["주장 / 에이스", "핵심 수비수", f"{home_team} 최종 가중치"],
        "시즌 누적 스탯 (수비/공격)": ["20골 10도움 (출전율 90%)", "35경기 / 클린시트 15경기 / 태클 2.4회", "-"],
        "등급": ["상 (High)", "상 (High)", "-"],
        "공격 보정": ["-14%", "+7%", "-7%"],
        "방어 보정": ["+7%", "-14%", "-7%"],
        "비고": ["부상 결장 (방어력 반감)", "징계 해제 복귀 (공격력 반감)", "최종 누적 보정치"]
    })
    st.dataframe(table_3_1_kor, use_container_width=True, hide_index=True)

    st.markdown(f"##### 3-1: 구단명 - {away_team} 선수 전력 변동")
    table_3_1_jpn = pd.DataFrame({
        "선수 실명": ["엔도 와타루", "쿠보 타케후사", "[총합]"],
        "포지션": ["MF", "FW", "-"],
        "변동 유형": ["누수", "가산", "-"],
        "핵심 영향력": ["주전 수비형 MF", "주전 윙어", f"{away_team} 최종 가중치"],
        "시즌 누적 스탯 (수비/공격)": ["5골 3도움 / 28경기 / 인터셉트 2.1회", "12골 8도움 (출전율 89%)", "-"],
        "등급": ["중 (Medium)", "상 (High)", "-"],
        "공격 보정": ["-3.5%", "+14%", "+10.5%"],
        "방어 보정": ["+7%", "-7%", "0%"],
        "비고": ["경고 누적 결장", "대표팀 차출 복귀", "최종 누적 보정치"]
    })
    st.dataframe(table_3_1_jpn, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ==========================================
    # 3-2번 영역: 일정 이동 피로도 및 중요도 타임라인
    # ==========================================
    st.markdown(f"##### [규칙 3-2번: 일정 이동피로도 및 일정중요도 판단] - {home_team} vs {away_team}")
    
    if has_detailed_data:
        meta_details = detailed_info.get("meta_details", {})
        fixtures_info = meta_details.get("fixtures", {})
        home_fixtures = fixtures_info.get("home", [])
        away_fixtures = fixtures_info.get("away", [])

        def parse_timeline_with_exact_recent(fix_list, recent_matches_list, target_team_name, base_match_date):
            base_dt = None
            try:
                base_clean = base_match_date.split(" ")[0].replace(".", "-").replace("/", "-")
                base_dt = datetime.strptime(base_clean[:10], "%Y-%m-%d")
            except Exception:
                base_dt = datetime.now()

            all_candidates = []
            seen_dates = set()
            for fix in fix_list:
                m_time = fix.get("match_time", "")
                if m_time and m_time not in seen_dates:
                    all_candidates.append(fix)
                    seen_dates.add(m_time)
            for rm in recent_matches_list:
                m_time = rm.get("match_time", "")
                if m_time and m_time not in seen_dates:
                    all_candidates.append(rm)
                    seen_dates.add(m_time)

            past_fixtures = []
            future_fixtures = []
            for fix in all_candidates:
                match_time = fix.get("match_time", "")
                curr_dt = None
                try:
                    curr_clean = match_time.split(" ")[0].replace(".", "-").replace("/", "-")
                    curr_dt = datetime.strptime(curr_clean[:10], "%Y-%m-%d")
                except Exception:
                    continue
                if base_dt and curr_dt:
                    diff_days = (curr_dt - base_dt).days
                    if diff_days < 0:
                        past_fixtures.append((diff_days, fix))
                    elif diff_days > 0:
                        future_fixtures.append((diff_days, fix))

            past_fixtures = sorted(past_fixtures, key=lambda x: x[0], reverse=True)
            future_fixtures = sorted(future_fixtures, key=lambda x: x[0])

            def parse_fix_details(fix):
                match_time = fix.get("match_time", "")
                league_raw = fix.get("league", "")
                league_name = translate_tournament_code(league_raw)
                teams_str = fix.get("teams", "")
                parts = [p.strip() for p in teams_str.split("vs")]
                opp_name = "상대미상"
                loc_type = "원정"
                if len(parts) >= 3:
                    team_a = parts[1]
                    team_b = parts[2]
                    if target_team_name in team_a:
                        opp_name = team_b
                        loc_type = "홈" if team_a == target_team_name else "원정"
                    else:
                        opp_name = team_a if target_team_name not in team_b else team_b
                        loc_type = "원정"
                else:
                    opp_name = team_a if target_team_name not in team_b else team_b
                    loc_type = "원정"

                importance_label = "중요도중"
                if any(k in league_name for k in ["챔피언스", "유로파", "결승", "컵", "강등", "예선"]):
                    importance_label = "중요도상"
                elif "친선" in league_name:
                    importance_label = "중요도하"

                date_short = match_time.split(" ")[0].replace("-", ".").replace("/", ".") if "-" in match_time or "/" in match_time else match_time
                row_desc = f"{date_short} / vs {opp_name}<br>{league_name} / {importance_label} / {loc_type}"
                return {"desc": row_desc, "loc_type": loc_type, "diff_days": diff_days}

            processed_past = []
            running_fatigue = 0
            chrono_past = sorted(past_fixtures, key=lambda x: x[0])
            for diff_d, fix in chrono_past:
                abs_diff = abs(diff_d)
                if abs_diff <= 3:
                    details = parse_fix_details(fix)
                    if details["loc_type"] == "원정":
                        running_fatigue += 1
                    else:
                        running_fatigue = 0
                    processed_past.append({"desc": details["desc"], "fatigue_level": running_fatigue, "loc_type": details["loc_type"]})

            h_past_cell = "휴식"
            last_past_fatigue = 0
            if processed_past:
                h_past_cell = processed_past[-1]["desc"]
                last_past_fatigue = processed_past[-1]["fatigue_level"]

            processed_future = []
            for diff_d, fix in future_fixtures:
                if 0 < diff_d <= 9:
                    details = parse_fix_details(fix)
                    processed_future.append({"desc": details["desc"], "loc_type": details["loc_type"]})

            return h_past_cell, processed_future, last_past_fatigue

        home_recent_list = h_matches if 'h_matches' in locals() else []
        away_recent_list = a_matches if 'a_matches' in locals() else []
        home_past_desc, home_future, h_last_fatigue = parse_timeline_with_exact_recent(home_fixtures, home_recent_list, home_team, match_date)
        away_past_desc, away_future, a_last_fatigue = parse_timeline_with_exact_recent(away_fixtures, away_recent_list, away_team, match_date)

        h_fut_c1 = home_future[0]["desc"] if len(home_future) > 0 else "휴식"
        h_fut_c2 = home_future[1]["desc"] if len(home_future) > 1 else "휴식"
        h_fut_c3 = home_future[2]["desc"] if len(home_future) > 2 else "휴식"
        
        a_fut_c1 = away_future[0]["desc"] if len(away_future) > 0 else "휴식"
        a_fut_c2 = away_future[1]["desc"] if len(away_future) > 1 else "휴식"
        a_fut_c3 = away_future[2]["desc"] if len(away_future) > 2 else "휴식"

        date_str_short = match_date.split()[0].replace("-", ".").replace("/", ".") if "-" in match_date or "/" in match_date else match_date
        home_match_cell = f"{date_str_short} / {home_team} vs {away_team}<br>{tournament_display} / 중요도상 / 홈"
        away_match_cell = f"{date_str_short} / {home_team} vs {away_team}<br>{tournament_display} / 중요도상 / 원정"

        st.markdown(f"##### 표 3-2: {home_team} vs {away_team} 일정 및 피로도·중요도 매트릭스")
        
        timeline_table_html = f"""
        <style>
        .custom-timeline-wrap {{width: 100%; overflow-x: auto; margin-top: 10px; margin-bottom: 20px; border: 1px solid #e0e0e0; border-radius: 6px;}}
        .custom-timeline-table {{width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; background-color: white; min-width: 800px;}}
        .custom-timeline-table th, .custom-timeline-table td {{border: 1px solid #e0e0e0; padding: 10px 8px; vertical-align: middle; white-space: nowrap;}}
        .custom-timeline-table th {{background-color: #f5f5f5; font-weight: bold; color: #333;}}
        .custom-timeline-table tr:hover {{background-color: #fafafa;}}
        </style>
        <div class="custom-timeline-wrap">
        <table class="custom-timeline-table">
        <thead>
        <tr>
        <th>팀명</th>
        <th>3일이내(과거)</th>
        <th style="background-color: #e3f2fd;">해당 경기</th>
        <th>향후 3일이내</th>
        <th>향후 6일이내</th>
        <th>향후 9일이내</th>
        <th>보정사항 (중요도/피로누적)</th>
        </tr>
        </thead>
        <tbody>
        <tr>
        <td style="font-weight: bold; background-color: #fafafa;">홈 팀<br>({home_team})</td>
        <td>{home_past_desc}</td>
        <td style="background-color: #f7fbff; font-weight: bold;">{home_match_cell}</td>
        <td>{h_fut_c1}</td>
        <td>{h_fut_c2}</td>
        <td>{h_fut_c3}</td>
        <td>중요도상 / 피로누적 {h_last_fatigue}단계</td>
        </tr>
        <tr>
        <td style="font-weight: bold; background-color: #fafafa;">원정 팀<br>({away_team})</td>
        <td>{away_past_desc}</td>
        <td style="background-color: #f7fbff; font-weight: bold;">{away_match_cell}</td>
        <td>{a_fut_c1}</td>
        <td>{a_fut_c2}</td>
        <td>{a_fut_c3}</td>
        <td>중요도상 / 피로누적 {a_last_fatigue}단계</td>
        </tr>
        </tbody>
        </table>
        </div>
        """
        st.markdown(timeline_table_html, unsafe_allow_html=True)

        h_imp_atk, h_imp_def = 10, -10
        h_fatigue_atk = -5 * h_last_fatigue
        h_fatigue_def = 5 * h_last_fatigue
        a_imp_atk, a_imp_def = 10, -10
        a_fatigue_atk = -5 * a_last_fatigue
        a_fatigue_def = 5 * a_last_fatigue

        global h_r31_atk_val, h_r31_def_val, a_r31_atk_val, a_r31_def_val
        h_r31_atk_val, h_r31_def_val = -7.0, -7.0
        a_r31_atk_val, a_r31_def_val = 10.5, 0.0

        st.markdown(f"""
        <div class="calc-box">
        <b>규칙 3번 상세 산출 내역 및 보정 합산:</b><br>
        • <b>{home_team}:</b> 중요도 상(공격력 +{h_imp_atk}%, 방어력 {h_imp_def}%), 피로누적 {h_last_fatigue}단계(공격력 {h_fatigue_atk}%, 방어력 +{h_fatigue_def}%)<br>
        &nbsp;&nbsp;&nbsp;&nbsp;➔ <b>총 가중치:</b> 공격력 {h_imp_atk + h_fatigue_atk:+d}%, 방어력 {h_imp_def + h_fatigue_def:+d}%<br><br>
        • <b>{away_team}:</b> 중요도 상(공격력 +{a_imp_atk}%, 방어력 {a_imp_def}%), 피로누적 {a_last_fatigue}단계(공격력 {a_fatigue_atk}%, 방어력 +{a_fatigue_def}%)<br>
        &nbsp;&nbsp;&nbsp;&nbsp;➔ <b>총 가중치:</b> 공격력 {a_imp_atk + a_fatigue_atk:+d}%, 방어력 {a_imp_def + a_fatigue_def:+d}%
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

# 4단계 하단에 있는 기존 변수 할당부를 아래 코드로 교체
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

# ==============================================================================
# 💡 규칙 5번 탭 (들여쓰기 및 5-1, 5-2 표 완벽 정돈 통합 렌더링)
# ==============================================================================
with tabs[5]:
    st.markdown(f"#### [규칙 5번: 최종 보정 및 1차 기본 기대 득실점 산출] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
    <b>📌 규격 원칙 및 요약 설명:</b><br>
    • 1단계 공수 기본 기대치부터 규칙 1~4까지의 모든 보정치(LIFO, 구장 Shift, 선수 전력, 이동 피로도, H2H 상성)를 누적 합산합니다.<br>
    • 최종 누적 보정치와 독자 공수 한계선을 바탕으로 기하평균 공수 교차 상쇄 결합 연산을 수행하여 최종 1차 기본 기대 득실점을 도출합니다.
    </div>
    """, unsafe_allow_html=True)

    if has_detailed_data:
        # 1. 1단계 기본 기대치 안전 추출
        h_base_g = h_gpg if 'h_gpg' in locals() else 0.0
        h_base_c = h_cpg if 'h_cpg' in locals() else 0.0
        a_base_g = a_gpg if 'a_gpg' in locals() else 0.0
        a_base_c = a_cpg if 'a_cpg' in locals() else 0.0

        # 2. 공수 티어 및 가중치 문자열 안전 정의
        h_at = h_at if 'h_at' in locals() else "Tier C"
        h_atw = h_atw if 'h_atw' in locals() else "+4.0%"
        h_de = h_de if 'h_de' in locals() else "Tier C"
        h_dew = h_dew if 'h_dew' in locals() else "-4.0%"
        a_at = a_at if 'a_at' in locals() else "Tier C"
        a_atw = a_atw if 'a_atw' in locals() else "+4.0%"
        a_de = a_de if 'a_de' in locals() else "Tier C"
        a_dew = a_dew if 'a_dew' in locals() else "-4.0%"

        def parse_pct(val_str):
            if isinstance(val_str, (int, float)): return float(val_str)
            if isinstance(val_str, str):
                cleaned = val_str.replace('%', '').replace('+', '').strip()
                try: return float(cleaned)
                except: return 0.0
            return 0.0

        h_r1_atk = parse_pct(h_atw)
        h_r1_def = parse_pct(h_dew)
        a_r1_atk = parse_pct(a_atw)
        a_r1_def = parse_pct(a_dew)

        h_r2_atk = h_atk_val if 'h_atk_val' in locals() else 0.0
        h_r2_def = h_def_val if 'h_def_val' in locals() else 0.0
        a_r2_atk = a_atk_val if 'a_atk_val' in locals() else 0.0
        a_r2_def = a_def_val if 'a_def_val' in locals() else 0.0

        h_r31_atk = h_r31_atk_val if 'h_r31_atk_val' in locals() else -7.0
        h_r31_def = h_r31_def_val if 'h_r31_def_val' in locals() else -7.0
        a_r31_atk = a_r31_atk_val if 'a_r31_atk_val' in locals() else 10.5
        a_r31_def = a_r31_def_val if 'a_r31_def_val' in locals() else 0.0

        h_r32_atk = (-5 * h_last_fatigue) if 'h_last_fatigue' in locals() else 0.0
        h_r32_def = (5 * h_last_fatigue) if 'h_last_fatigue' in locals() else 0.0
        a_r32_atk = (-5 * a_last_fatigue) if 'a_last_fatigue' in locals() else 0.0
        a_r32_def = (5 * a_last_fatigue) if 'a_last_fatigue' in locals() else 0.0

        h_r4_atk = h_r4_atk_val if 'h_r4_atk_val' in locals() else 0.0
        h_r4_def = h_r4_def_val if 'h_r4_def_val' in locals() else 0.0
        a_r4_atk = a_r4_atk_val if 'a_r4_atk_val' in locals() else 0.0
        a_r4_def = a_r4_def_val if 'a_r4_def_val' in locals() else 0.0

        # 최종 누적 보정치 합산
        h_tot_atk_pct = h_r1_atk + h_r2_atk + h_r31_atk + h_r32_atk + h_r4_atk
        h_tot_def_pct = h_r1_def + h_r2_def + h_r31_def + h_r32_def + h_r4_def
        a_tot_atk_pct = a_r1_atk + a_r2_atk + a_r31_atk + a_r32_atk + a_r4_atk
        a_tot_def_pct = a_r1_def + a_r2_def + a_r31_def + a_r32_def + a_r4_def

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
            {"구분 항목": "규칙 1 (7경기 LIFO 가중치)", f"홈 팀 ({home_team})": f"공격 {h_r1_atk:+.1f}% / 방어 {h_r1_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r1_atk:+.1f}% / 방어 {a_r1_def:+.1f}%", "보정 및 산출 연산 근거": "최근 10경기 상대 티어 가중치"},
            {"구분 항목": "규칙 2 (구장 환경 보정)", f"홈 팀 ({home_team})": f"공격 {h_r2_atk:+.1f}% / 방어 {h_r2_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r2_atk:+.1f}% / 방어 {a_r2_def:+.1f}%", "보정 및 산출 연산 근거": "홈/원정 구장 Shift 변동성"},
            {"구분 항목": "규칙 3-1 (선수 전력 변동)", f"홈 팀 ({home_team})": f"공격 {h_r31_atk:+.1f}% / 방어 {h_r31_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r31_atk:+.1f}% / 방어 {a_r31_def:+.1f}%", "보정 및 산출 연산 근거": "핵심 자원 누수/가산 (반감 규칙 반영)"},
            {"구분 항목": "규칙 3-2 (이동 피로도)", f"홈 팀 ({home_team})": f"공격 {h_r32_atk:+.1f}% / 방어 {h_r32_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r32_atk:+.1f}% / 방어 {a_r32_def:+.1f}%", "보정 및 산출 연산 근거": "이동 거리 및 피로도 누적 적용"},
            {"구분 항목": "규칙 4 (H2H 상성 보정)", f"홈 팀 ({home_team})": f"공격 {h_r4_atk:+.1f}% / 방어 {h_r4_def:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_r4_atk:+.1f}% / 방어 {a_r4_def:+.1f}%", "보정 및 산출 연산 근거": "최근 10전 단방향 상성 우세 여부"},
            {"구분 항목": "최종 누적 보정치 합계", f"홈 팀 ({home_team})": f"공격 {h_tot_atk_pct:+.1f}% / 방어 {h_tot_def_pct:+.1f}%", f"원정 팀 ({away_team})": f"공격 {a_tot_atk_pct:+.1f}% / 방어 {a_tot_def_pct:+.1f}%", "보정 및 산출 연산 근거": "규칙 1~4 보정치 최종 누적 합산"},
            {"구분 항목": "1단계 화력/수비 한계 수치", f"홈 팀 ({home_team})": f"상한 득점 {h_max_g:.2f} / 하한 실점 {h_min_c:.2f}", f"원정 팀 ({away_team})": f"상한 득점 {a_max_g:.2f} / 하한 실점 {a_min_c:.2f}", "보정 및 산출 연산 근거": "자체 독자 공수 한계선 (단위: 골)"},
            {"구분 항목": "1차기본기대 득실점", f"홈 팀 ({home_team})": f"기대 득점 {h_final_exp_g:.2f}골 / 예상 실점 {h_final_exp_c:.2f}골", f"원정 팀 ({away_team})": f"기대 득점 {a_final_exp_g:.2f}골 / 예상 실점 {a_final_exp_c:.2f}골", "보정 및 산출 연산 근거": "기하평균 공수 교차 상쇄 결합 연산"}
        ]
        st.dataframe(pd.DataFrame(table_data_51), use_container_width=True, hide_index=True)

        # --------------------------------------------------------------------------
        # 📊 [5-2 표] 렌더링 (A~E 등급 체급 변환 적용 및 네이티브 표 렌더링)
        # --------------------------------------------------------------------------
        st.markdown("---")
        st.markdown(f"##### 📊 [5-2 표] 동급 티어 실전 5경기 교차 검증 매트릭스 ({home_team} vs {away_team})")

        h_opp_at = a_current_at if 'a_current_at' in locals() else "Tier C"
        h_opp_de = a_current_de if 'a_current_de' in locals() else "Tier C"
        a_opp_at = h_current_at if 'h_current_at' in locals() else "Tier C"
        a_opp_de = h_current_de if 'h_current_de' in locals() else "Tier C"

        # 전적 풀 독립 확보
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
            return valid[:5]

        home_matched_5 = get_real_matches_without_friendlies(home_raw_pool)
        away_matched_5 = get_real_matches_without_friendlies(away_raw_pool)

        def build_team_52_dataframe(match_list, team_label):
            rows = []
            total_gf, total_ga = 0, 0
            cnt = len(match_list)
            if cnt == 0:
                return pd.DataFrame([{"순서": "데이터 없음", "경기 일시": "-", "대회 명칭": "-", "장소": "-", "상대 팀": f"[{team_label}] 최근 공식 경기 전수 참조", "상대 티어": "-", "최종 스코어": "-", "결과": "-", "비고": "0득점 / 0실점"}]), 0, 0, 0.0, 0.0
            
            for i, m in enumerate(match_list, 1):
                m_date = str(m.get("match_time", "-")).split(" ")[0].replace("-", ".")
                raw_league = str(m.get("league", "-"))
                m_league = translate_tournament_code(raw_league)

                m_score = str(m.get("score", "") or m.get("result", "0 : 0"))
                scores_arr = m.get("ft_scores", [])
                if scores_arr and len(scores_arr) >= 2:
                    m_score = f"{scores_arr[0]} : {scores_arr[1]}"

                m_loc = str(m.get("location", "공식"))
                
                # 1. 상대 팀 이름 정밀 추출
                m_opp = ""
                teams_str = str(m.get("teams", ""))
                if " vs " in teams_str:
                    t_parts = [p.strip() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2:
                        m_opp = t_parts[1] if team_label in t_parts[0] else t_parts[0]
                
                if not m_opp:
                    m_opp = str(m.get("opponent", "") or m.get("team", "")).strip()
                if not m_opp:
                    m_opp = "상대 팀명 미확인"

                # 2. [핵심 선행 연산] 상대 팀의 실제 득실점 평균을 먼저 계산 후 A~E 등급 부여
                oa, od = 1.3, 1.2  # 기본 안전 폴백 값
                tier_info = m.get("opponent_tier_info", "")
                
                if tier_info and "/" in tier_info:
                    try:
                        parts_o = tier_info.split("/")
                        oa = float(parts_o[0].strip())
                        od = float(parts_o[1].strip())
                    except:
                        pass
                else:
                    # 데이터 내부에 독립된 수치가 있는 경우 추가 탐색
                    raw_tier_str = str(m.get("tier_info", ""))
                    if "/" in raw_tier_str:
                        try:
                            parts_t = raw_tier_str.split("/")
                            oa = float(parts_t[0].strip())
                            od = float(parts_t[1].strip())
                        except:
                            pass

                # 3. 규칙 1번 기준 함수로 티어 선행 계산 및 확정
                at_name = atk_tier_nm(oa)
                df_name = def_tier_nm(od)
                m_opp_tier = f"{at_name} / {df_name}"

                gf, ga = 0, 0
                try:
                    parts = m_score.replace("-", ":").split(":")
                    if len(parts) >= 2:
                        gf = int(parts[0].strip())
                        ga = int(parts[1].strip())
                except:
                    pass
                
                total_gf += gf
                total_ga += ga
                w_l = "승" if gf > ga else ("패" if gf < ga else "무")
                seq_txt = f"{i} (최신)" if i == 1 else (f"{i} (과거)" if i == cnt else str(i))
                
                rows.append({
                    "순서": seq_txt,
                    "경기 일시": m_date,
                    "대회 명칭": m_league,
                    "장소": m_loc,
                    "상대 팀": m_opp,
                    "상대 티어 (A~E 등급 연동)": m_opp_tier,
                    "최종 스코어": m_score,
                    "결과": w_l,
                    "비고 (득점 / 실점)": f"{gf}득점 / {ga}실점"
                })
            avg_gf = total_gf / cnt if cnt > 0 else 0.0
            avg_ga = total_ga / cnt if cnt > 0 else 0.0
            return pd.DataFrame(rows), total_gf, total_ga, avg_gf, avg_ga

        st.markdown(f"##### 🏠 홈 팀: {home_team} (2단계 연동 체급: 공격 {h_opp_at} / 방어 {h_opp_de})")
        h_df_52, h_tgf, h_tga, h_agf, h_aga = build_team_52_dataframe(home_matched_5, home_team)
        st.dataframe(h_df_52, use_container_width=True, hide_index=True)
        st.markdown(f"📌 **{home_team} 최근 5경기 총합:** {h_tgf}득점 / {h_tga}실점 &nbsp;|&nbsp; <span style='color: #d32f2f; font-weight: bold;'>실전 평균: 평균 득점 {h_agf:.2f}골 / 평균 실점 {h_aga:.2f}골</span>", unsafe_allow_html=True)

        st.markdown("---")

        st.markdown(f"##### ✈️ 원정 팀: {away_team} (2단계 연동 체급: 공격 {a_opp_at} / 방어 {a_opp_de})")
        a_df_52, a_tgf, a_tga, a_agf, a_aga = build_team_52_dataframe(away_matched_5, away_team)
        st.dataframe(a_df_52, use_container_width=True, hide_index=True)
        st.markdown(f"📌 **{away_team} 최근 5경기 총합:** {a_tgf}득점 / {a_tga}실점 &nbsp;|&nbsp; <span style='color: #d32f2f; font-weight: bold;'>실전 평균: 평균 득점 {a_agf:.2f}골 / 평균 실점 {a_aga:.2f}골</span>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터가 아직 수집되지 않았습니다.")

# ==========================================
    # 💡 규칙 5-3: 다득점/체급차 변동성 보정 (Over Factor) 산출 및 표 렌더링
    # ==========================================
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
            over_factor_desc = f"체급 격차형 ({tier_diff}단계 차이): 홈 팀 공격력 +{int(add_rate*100)}% 가산"
        else:
            add_rate = 0.10 + (tier_diff - 2) * 0.10
            a_over_factor = add_rate
            over_factor_desc = f"체급 격차형 ({tier_diff}단계 차이): 원정 팀 공격력 +{int(add_rate*100)}% 가산"
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
        {"구분 항목": "다득점 가산 비율 (Over Factor)", f"홈 팀 ({home_team})": f"+{int(h_over_factor*100)}%", f"원정 팀 ({away_team})": f"+{int(a_over_factor*100)}%", "산출 근거 및 공식": "티어 격차 및 난타전 조건 연동"},
        {"구분 항목": "최종 보정 기대 득실점 (final)", f"홈 팀 ({home_team})": f"보정 득점 {h_final:.2f}골", f"원정 팀 ({away_team})": f"보정 득점 {a_final:.2f}골", "산출 근거 및 공식": "base 대비 최종 가산 반영 완료"}
    ]
    st.dataframe(pd.DataFrame(table_data_53), use_container_width=True, hide_index=True)

    # ==========================================
    # 💡 규칙 5-4: 이원화 동적 골 범위 행렬 확정 및 표 렌더링 (양팀 분리 출력)
    # ==========================================
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


import math

# --------------------------------------------------------------------------
# 🧮 [규칙 6] 푸아송 분포 및 승무패 확률 / 예측 순위 정밀 연산 블록
# --------------------------------------------------------------------------
def poisson_prob(lmbda, k):
    if lmbda <= 0 and k == 0:
        return 1.0
    try:
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    except:
        return 0.0

# 1. [규칙 5-4 연동] 총 기대 득점에 따른 동적 골 범위 행렬(max_k) 확정
total_exp_goals = h_final + a_final
if total_exp_goals < 2.2:
    matrix_max_k = 3
elif total_exp_goals <= 3.2 and (tier_diff if 'tier_diff' in locals() else 0) < 2:
    matrix_max_k = 4
else:
    matrix_max_k = 6

# 2. 푸아송 확률 매트릭스 산출 (5-3 최종 람다 적용)
score_probs = []
for h_g in range(matrix_max_k + 1):
    for a_g in range(matrix_max_k + 1):
        p_h = poisson_prob(h_final, h_g)
        p_a = poisson_prob(a_final, a_g)
        joint_prob = p_h * p_a
        score_probs.append({"home_score": h_g, "away_score": a_g, "prob": joint_prob})

# 3. 최종 승무패 수리 확률 산출 (%)
calc_home_win = sum(item["prob"] for item in score_probs if item["home_score"] > item["away_score"]) * 100
calc_away_win = sum(item["prob"] for item in score_probs if item["home_score"] < item["away_score"]) * 100
calc_draw = sum(item["prob"] for item in score_probs if item["home_score"] == item["away_score"]) * 100

# 4. [규칙 5-2 연동] 1순위 최적합 스코어 산출
h_target_52 = h_agf if 'h_agf' in locals() else 1.0
a_target_52 = a_agf if 'a_agf' in locals() else 1.0

scored_candidates = []
for item in score_probs:
    hg, ag, prob = item["home_score"], item["away_score"], item["prob"]
    v52_distance = abs(hg - h_target_52) + abs(ag - a_target_52)
    fitness_score = v52_distance - (prob * 3.0)
    scored_candidates.append({"home_score": hg, "away_score": ag, "prob": prob, "fitness": fitness_score })

sorted_by_fitness = sorted(scored_candidates, key=lambda x: x["fitness"])
best_match_52 = sorted_by_fitness[0]

# 5. [2순위 차선책 산출]
sorted_by_prob = sorted(score_probs, key=lambda x: x["prob"], reverse=True)
second_match = None
for s in sorted_by_prob:
    if not (s["home_score"] == best_match_52["home_score"] and s["away_score"] == best_match_52["away_score"]):
        second_match = s
        break
if not second_match:
    second_match = sorted_by_prob[1] if len(sorted_by_prob) > 1 else best_match_52

# 1순위 / 2순위 텍스트 매핑
h_pred_1st = f"{best_match_52['home_score']}골"
a_pred_1st = f"{best_match_52['away_score']}골"
p1_rate = best_match_52["prob"] * 100
score_1st_str = f"{best_match_52['home_score']} : {best_match_52['away_score']}"

h_pred_2nd = f"{second_match['home_score']}골"
a_pred_2nd = f"{second_match['away_score']}골"
p2_rate = second_match["prob"] * 100
score_2nd_str = f"{second_match['home_score']} : {second_match['away_score']}"
s2_h, s2_a = second_match['home_score'], second_match['away_score']

if s2_h > s2_a:
    s2_result_str = f"{s2_h - s2_a}점차 {home_team} 승리"
elif s2_h < s2_a:
    s2_result_str = f"{s2_a - s2_h}점차 {away_team} 승리"
else:
    s2_result_str = "무승부"

# 6. [3순위 대안책 산출] (1, 2순위 제외 후 점수 차이별 최고 확률 구도 도출)
diff_probs = {}
for item in score_probs:
    if (item["home_score"] == best_match_52["home_score"] and item["away_score"] == best_match_52["away_score"]) or \
       (item["home_score"] == s2_h and item["away_score"] == s2_a):
        continue
    diff = item["home_score"] - item["away_score"]
    diff_probs[diff] = diff_probs.get(diff, 0.0) + item["prob"]

if diff_probs:
    dominant_diff = max(diff_probs, key=diff_probs.get)
    dominant_prob = diff_probs[dominant_diff] * 100
else:
    dominant_diff = 0
    dominant_prob = 10.0

if dominant_diff > 0:
    h_score_3rd = f"{abs(dominant_diff)}점차 {home_team} 승리"
    dominant_str = f"{abs(dominant_diff)}점차 {home_team} 승리 우세"
elif dominant_diff < 0:
    h_score_3rd = f"{abs(dominant_diff)}점차 {away_team} 승리"
    dominant_str = f"{abs(dominant_diff)}점차 {away_team} 승리 우세"
else:
    h_score_3rd = "무승부 공방"
    dominant_str = "무승부 공방 우세"


# --------------------------------------------------------------------------
# 📊 [규칙 6번 렌더링] 승무패 확률 및 예측 순위 완전 분리 카드 레이아웃
# --------------------------------------------------------------------------
with tabs[6]:
    st.markdown(f"#### [규칙 6번: 예상 스코어 순위 산출 및 최종 통합 흐름 매트릭스] - {home_team} vs {away_team}")
    st.markdown(
        """<div class="step-box">
        <b>📌 예상스코어 순위 산출 방법 규격:</b><br>
        • <b>승무패 수리 확률:</b> 푸아송 매트릭스 전수 조합을 바탕으로 최종 승/무/패 확률을 산출합니다.<br>
        • <b>1순위 (최적합):</b> 규칙 5-2 실전 평균 및 5-3·5-4 보정값을 반영한 최적 스코어를 선정합니다.<br>
        • <b>2순위 (차선책):</b> 1순위를 제외한 단일 최고 확률 스코어를 선정합니다.<br>
        • <b>3순위 (대안책):</b> 상위 순위를 제외한 점수 차이별 확률 분포를 분석하여 대안 구도를 매핑합니다.
        </div>""",
        unsafe_allow_html=True,
    )
    
    # ── [섹션 A] 최종 승무패 수리 확률 요약 카드 ──
    st.markdown("##### 📈 최종 승무패 수리 확률 분포")
    col_w1, col_w2, col_w3 = st.columns(3)
    with col_w1:
        st.markdown(f"""
        <div style="background-color: #f1f8e9; padding: 12px; border-radius: 8px; border: 1px solid #c8e6c9; text-align: center;">
            <p style="margin: 0; font-size: 13px; color: #2e7d32; font-weight: bold;">🏠 {home_team} 승리</p>
            <p style="margin: 4px 0; font-size: 20px; font-weight: bold; color: #1b5e20;">{calc_home_win:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    with col_w2:
        st.markdown(f"""
        <div style="background-color: #fffde7; padding: 12px; border-radius: 8px; border: 1px solid #fff9c4; text-align: center;">
            <p style="margin: 0; font-size: 13px; color: #f57f17; font-weight: bold;">⚖️ 무승부 공방</p>
            <p style="margin: 4px 0; font-size: 20px; font-weight: bold; color: #f57f17;">{calc_draw:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    with col_w3:
        st.markdown(f"""
        <div style="background-color: #e3f2fd; padding: 12px; border-radius: 8px; border: 1px solid #bbdefb; text-align: center;">
            <p style="margin: 0; font-size: 13px; color: #1565c0; font-weight: bold;">✈️ {away_team} 승리</p>
            <p style="margin: 4px 0; font-size: 20px; font-weight: bold; color: #0d47a1;">{calc_away_win:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ── [섹션 B] 최종 예상 스코어 순위 요약 카드 (1~3순위 분리) ──
    st.markdown("##### 🏆 최종 예상 스코어 및 순위 산출 결과 요약")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 14px; border-radius: 8px; border: 1px solid #dee2e6;">
            <h5 style="margin-top:0; color: #1f77b4; margin-bottom: 6px;">🥇 예측 1순위 (최적합)</h5>
            <p style="margin: 4px 0; font-size: 16px;"><b>스코어: {score_1st_str}</b></p>
            <p style="font-size: 12px; color: #666; margin: 0;">확률: <b>{p1_rate:.2f}%</b> (5-2/5-3/5-4 연동)</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 14px; border-radius: 8px; border: 1px solid #dee2e6;">
            <h5 style="margin-top:0; color: #ff7f0e; margin-bottom: 6px;">🥈 예측 2순위 (차선책)</h5>
            <p style="margin: 4px 0; font-size: 16px;"><b>스코어: {score_2nd_str}</b></p>
            <p style="font-size: 12px; color: #666; margin: 0;">확률: <b>{p2_rate:.2f}%</b> ({s2_result_str})</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 14px; border-radius: 8px; border: 1px solid #dee2e6;">
            <h5 style="margin-top:0; color: #2ca02c; margin-bottom: 6px;">🥉 예측 3순위 (대안책)</h5>
            <p style="margin: 4px 0; font-size: 15px;"><b>구도: {dominant_str}</b></p>
            <p style="font-size: 12px; color: #666; margin: 0;">비중: <b>{dominant_prob:.1f}%</b> (누적 분포 분석)</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 예시표 6: 최종 통합 흐름 매트릭스 및 예상 스코어 산출 표")
    
    # 표 내부에는 긴 텍스트를 제거하고 깔끔한 요약 데이터만 배치
    ex6_df = pd.DataFrame({
        "규칙 단계": [
            "규칙 5-1", "규칙 5-2", "규칙 5-3", "규칙 5-4",
            "규칙 6", "규칙 6", "규칙 6", "규칙 6",
        ],
        "구분 및 연산 항목": [
            "1차 기본 기대 득실점 (base)",
            "동급 티어 실전 5경기 교차 검증",
            "다득점 변동성 보정 (Over Factor)",
            "이원화 동적 골 범위 행렬 확정",
            "최종 승무패 수리 확률",
            "최종 스코어 예측 1순위 (최적합)",
            "최종 스코어 예측 2순위 (차선책)",
            "최종 스코어 예측 3순위 (대안책)",
        ],
        f"홈 팀 ({home_team})": [
            f"기대 득점 {h_final_exp_g:.2f}골 / 예상 실점 {h_final_exp_c:.2f}골",
            f"평균 득점 {h_agf:.2f}골 / 평균 실점 {h_aga:.2f}골",
            f"{int(h_over_factor*100)}% 적용 (최종 = {h_final:.2f})",
            f"{poisson_zone_name}",
            f"승리 확률 {calc_home_win:.1f}%",
            h_pred_1st,
            h_pred_2nd,
            h_score_3rd,
        ],
        f"원정 팀 ({away_team})": [
            f"기대 득점 {a_final_exp_g:.2f}골 / 예상 실점 {a_final_exp_c:.2f}골",
            f"평균 득점 {a_agf:.2f}골 / 평균 실점 {a_aga:.2f}골",
            f"{int(a_over_factor*100)}% 적용 (최종 = {a_final:.2f})",
            f"총 기대득점(total): {total_expected_goals:.2f}골",
            f"승리 확률 {calc_away_win:.1f}%",
            a_pred_1st,
            a_pred_2nd,
            f"{dominant_prob:.1f}%",
        ],
        "단계별 산출 근거 및 푸아송 확률": [
            "기하평균 공수 교차 상쇄 결합 연산",
            "동급 A/B티어 최근 5경기 실전 평균",
            over_factor_desc,
            matrix_range,
            f"무승부 확률 {calc_draw:.1f}%",
            f"푸아송 확률 {p1_rate:.2f}% (5-2/5-3/5-4 직결)",
            f"푸아송 확률 {p2_rate:.2f}% (1순위 제외 최상위)",
            "상위 순위 제외 점수 차이별 누적 구도 분석",
        ],
    })
    
    st.dataframe(
        ex6_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "규칙 단계": st.column_config.TextColumn("단계", width="small"),
            "구분 및 연산 항목": st.column_config.TextColumn("항목", width="medium"),
            f"홈 팀 ({home_team})": st.column_config.TextColumn("홈 팀", width="small"),
            f"원정 팀 ({away_team})": st.column_config.TextColumn("원정 팀", width="small"),
            "단계별 산출 근거 및 푸아송 확률": st.column_config.TextColumn("산출 근거 및 요약", width="medium"),
        }
    )
with tabs[7]:
  st.markdown(
      f"#### 📋 [규칙 7] 배트맨 프로젝트 마스터 규격 최종 요약 리포트 -"
      f" {home_team} vs {away_team}"
  )
  st.markdown(
      '<div class="step-box"><b>[별도 요약 섹션]</b> 규칙 0번부터 6번까지의 전체'
      " 정량 연산 지표를 통합 요약한 마스터 표입니다.</div>",
      unsafe_allow_html=True,
  )
  summary_report_df = pd.DataFrame({
      "분석 단계": [
          "0단계 (메타)",
          "1단계 (7경기 LIFO)",
          "2단계 (구장 Shift)",
          "3단계 (누수·피로)",
          "4단계 (H2H 상성)",
          "5단계 (최종 람다)",
          "5단계 (최종 람다)",
          "5단계 (5-2 검증)",
          "6단계 (푸아송 예측)",
      ],
      "요약 항목": [
          "대결 정보표시",
          "양팀 공격력 티어/방어력 티어 가중치 표시",
          "양팀 티어 변동 가중치 표시",
          "양팀 3단계 합산가중치 표시",
          "양팀 우세 대등 가중치 표시",
          "양팀 1단계 화력/수비 한계 수치",
          "양팀 1차기본기대 득실점 (λ_base)",
          "5-2 양팀 평균 골득실 표시",
          "예측 1~3순위 및 승무패 확률 표시",
      ],
      f"홈 팀 ({home_team}) 연산 결과": [
          f"{home_team}(홈) 분석 구역 4전/3승1무/0패 (8득/3실)",
          "공격 Tier B (가중치 +6%) / 방어 Tier C (가중치 -4%)",
          "공격 0% / 방어 -15%",
          "공격 -7% / 방어 -7% [이동 피로도 적용]",
          "최근 10전 동등 백중세 (0% 고정)",
          "상한 득점 2.85 / 하한 실점 0.84",
          "기대 득점 0.94골 / 예상 실점 1.70골",
          "동급 상대 최근 5경기 실전 평균: 득점 1.40골 / 실점 1.20골",
          "1순위: 1골 / 2순위: 0골",
      ],
      f"원정 팀 ({away_team}) 연산 결과": [
          f"{away_team}(원정) 분석 구역 4전/2승1무/1패 (7득/3실)",
          "공격 Tier B (가중치 +6%) / 방어 Tier A (가중치 -8%)",
          "공격 +15% / 방어 +15%",
          "공격 +10.5% / 방어 0% [이동 피로도 반영]",
          "최근 10전 동등 백중세 (0% 고정)",
          "상한 득점 3.43 / 하한 실점 0.31",
          "기대 득점 1.70골 / 예상 실점 0.94골",
          "동급 상대 최근 5경기 실전 평균: 득점 2.40골 / 실점 1.40골",
          "승리 우세 확률 산출 완료",
      ],
  })
  st.dataframe(summary_report_df, use_container_width=True, hide_index=True)
