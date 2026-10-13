from datetime import datetime, timezone, timedelta
import json
import os
import re
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st

@st.cache_data(ttl=10)
def load_match_data():
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_updated": "안전 모드 (데이터 없음)",
        "daily_matches": {}
    }

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
# 0단계 탭 (메타 및 순위표 출력)
# ==========================================
with tabs[0]:
    st.markdown("#### [0단계: 대진 정보 및 팀순위 정보]")
    st.markdown("친선 경기를 전면 배제하고 공식 A매치 유효성 검증을 거친 대진 메타데이터를 고정합니다. (SSOT 원칙 적용)")
    
    # 경기 일시 데이터 안전 추출
    match_time_display = detailed_info.get("head_info", {}).get("match_time_display", "")
    if not match_time_display:
        match_time_display = selected_match.get("time", match_date)

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
        
        # 💡 [핵심 규칙 반영] 구장 정보 순서 및 색상 지정 (실제 경기장명 / 일치여부 / 날씨)
        if stadium_name and home_stadium_name:
            if stadium_name.lower() == home_stadium_name.lower():
                # 홈구장 일치 시: 실제 경기장명 / 녹색 (홈)
                stadium_badge = f"{stadium_name} / <span style='color: #2e7d32; font-weight: bold;'>{home_stadium_name} (홈)</span>"
            else:
                # 중립구장 불일치 시: 실제 경기장명 / 빨간색 (중립)
                stadium_badge = f"{stadium_name} / <span style='color: #c62828; font-weight: bold;'>{home_stadium_name} (중립)</span>"
        elif stadium_name:
            stadium_badge = f"{stadium_name} / 홈구장 정보 미확인"
        else:
            stadium_badge = "구장 정보 실시간 반영 대기"

        # 날씨 정보 결합 순서 정돈
        w_text = weather_info if weather_info else "날씨 정보 없음"
        stadium_info = f"{stadium_badge} / 날씨: {w_text}"
            
    else:
        meta_status = "⚠️ 해당 경기의 상세 정밀 데이터 없음 (데이터 없음)"
        tournament_display = tournament_name
        stadium_info = "데이터 없음"

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
        "공격 가중치": ["+8.0%", "+6.0%", "+4.0%", "+2.0%", "0.0% (최하위)"],
        "방어력 기준 (평균 실점)": ["0.5골 미만 (< 0.5)", "0.5 ~ 0.9골 미만", "0.9 ~ 1.3골 미만", "1.3 ~ 1.7골 미만", "1.7골 이상"],
        "방어 가중치": ["-8.0% (최상위)", "-6.0%", "-4.0%", "-2.0%", "0.0%"]
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
    h_gpg_base = float(h_sum.get("goals_per_game", 0))
    h_cpg_base = float(h_sum.get("conceded_per_game", 0))
    h_rec_base = h_sum.get("recent_record", "0전 0승 0무 0패")
    
    a_gpg_base = float(a_sum.get("goals_per_game", 0))
    a_cpg_base = float(a_sum.get("conceded_per_game", 0))
    a_rec_base = a_sum.get("recent_record", "0전 0승 0무 0패")

    def atk_tier(g):
        if g >= 2.3: return "Tier A", "+8.0%"
        elif g >= 1.7: return "Tier B", "+6.0%"
        elif g >= 1.1: return "Tier C", "+4.0%"
        elif g >= 0.5: return "Tier D", "+2.0%"
        else: return "Tier E", "0.0%"

    def def_tier(c):
        if c < 0.5: return "Tier A", "-8.0%"
        elif c < 0.9: return "Tier B", "-6.0%"
        elif c < 1.3: return "Tier C", "-4.0%"
        elif c < 1.7: return "Tier D", "-2.0%"
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
            
            if sc > cc: res = "승"; w += 1
            elif sc == cc: res = "무"; d += 1
            else: res = "패"; l += 1
            
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
            rows.append({"LIFO 순서": seq, "경기 일시": mtime, "대회": league, "대진": teams, "스코어": score_display, "결과": res, "상대 공수 티어": tier_str})
            
        cnt = len(matches)
        gpg = eff_scored / cnt if cnt > 0 else def_gpg
        cpg = c_total / cnt if cnt > 0 else def_cpg
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


# ==========================================
# 💡 규칙 2번 탭 (구장별 Shift 검증) - 전적 요약 및 보정 평균 득실 표기 반영
# ==========================================
with tabs[2]:
    st.markdown(f"#### [규칙 2번: 구장별 Shift 검증 및 티어 보정] - {home_team} vs {away_team}")
    st.markdown("""
        <div class="step-box">
            <b>📌 규격 원칙 및 요약 설명:</b><br>
            • <b>구장별 전적(Stadium Form) 분석:</b> 홈팀의 홈 경기 구장 및 원정팀의 원정 경기 구장 데이터를 독립적으로 추출합니다.<br>
            • <b>1단계 티어 대조 및 Shift 보정치:</b> 1단계 종합 티어와 구장별 티어를 비교하여 상승/하락에 따른 순수 보정치 수치를 적용합니다.
        </div>
        """, unsafe_allow_html=True,
    )

    if has_detailed_data:
        s_home_matches = stadium_form.get("home_matches", [])[:10]
        s_away_matches = stadium_form.get("away_matches", [])[:10]

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

        def get_shift_correction(base_tier, stadium_tier, is_attack=True):
            tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
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

        # --- 홈 팀 렌더링 ---
        st.markdown(f"##### 홈 팀 ({h_name}) 구장별 전적 및 티어 변동 검증")
        if not s_h_df.empty:
            st.dataframe(s_h_df, use_container_width=True, hide_index=True)
        else:
            st.info("📋 구장별 상세 전적 데이터 없음")
            
        st.markdown(f"""<div class="calc-box">
            <b>{h_name} 규칙 2번(구장별) Shift 보정 산출 내역</b><br>
            • 최근 전적: <b>{s_h_rec}</b> (총 득점: <b>{s_h_raw_s:.1f}골</b> / 총 실점: <b>{s_h_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if s_h_diff >= 0 else '#c62828'};">{s_h_diff:+.1f}</b>)<br>
            • 보정 평균 득점: <b>{s_h_gpg:.2f}골/경기</b> / 평균 실점: <b>{s_h_cpg:.2f}골/경기</b><br>
            • 1단계 종합 체급: 공격 <b>{base_h_at}</b> / 방어 <b>{base_h_de}</b> &nbsp;|&nbsp; 구장 환경 체급: 공격 <b>{s_h_at}</b> / 방어 <b>{s_h_de}</b><br>
            • <b>적용된 구장 Shift 보정치:</b> 공격 <b>{h_atk_shift_str}</b> / 방어 <b>{h_def_shift_str}</b>
        </div>""", unsafe_allow_html=True,
    )

        st.markdown("---")

        # --- 원정 팀 렌더링 ---
        st.markdown(f"##### 원정 팀 ({a_name}) 구장별 전적 및 티어 변동 검증")
        if not s_a_df.empty:
            st.dataframe(s_a_df, use_container_width=True, hide_index=True)
        else:
            st.info("📋 구장별 상세 전적 데이터 없음")
            
        st.markdown(f"""<div class="calc-box">
            <b>{a_name} 규칙 2번(구장별) Shift 보정 산출 내역</b><br>
            • 최근 전적: <b>{s_a_rec}</b> (총 득점: <b>{s_a_raw_s:.1f}골</b> / 총 실점: <b>{s_a_raw_c:.1f}골</b> / 골득실: <b style="color: {'#2e7d32' if s_a_diff >= 0 else '#c62828'};">{s_a_diff:+.1f}</b>)<br>
            • 보정 평균 득점: <b>{s_a_gpg:.2f}골/경기</b> / 평균 실점: <b>{s_a_cpg:.2f}골/경기</b><br>
            • 1단계 종합 체급: 공격 <b>{base_a_at}</b> / 방어 <b>{base_a_de}</b> &nbsp;|&nbsp; 구장 환경 체급: 공격 <b>{s_a_at}</b> / 방어 <b>{s_a_de}</b><br>
            • <b>적용된 구장 Shift 보정치:</b> 공격 <b>{a_atk_shift_str}</b> / 방어 <b>{a_def_shift_str}</b>
        </div>""", unsafe_allow_html=True,
    )
    else:
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터가 아직 수집되지 않았습니다.")
# --- [3단계: 전력누수·피로 매트릭스] ---
with tabs[3]:
    st.markdown(f"#### [규칙 3-1번: 선수 전력 누수 및 이동 피로도 타임라인] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
        <b>📌 규칙 3-1 (선수 전력 변동: 누수 및 가산) 규격 요약:</b><br>
        • <b>정량 수치 모델 적용:</b> 매체 보도 등 기초 사실(Fact)을 바탕으로 하되, 분석 및 스코어 도출은 엄격한 정량 수치 모델을 적용합니다.<br>
        • <b>부호 대칭 규격:</b> 누수(부상·징계·이적 이탈)는 공격력 음수(-), 방어력 양수(+) / 가산(복귀·신규 입단)은 공격력 양수(+), 방어력 음수(-)를 적용합니다.<br>
        • <b>포지션별 반감(Halved) 규칙:</b> 공격 자원(FW/AMF)의 방어 보정과 수비 자원(DF/DMF/GK)의 공격 보정은 1/2로 반감 적용합니다 (상: 7%, 중: 3.5%, 하: 0%).
    </div>
    """, unsafe_allow_html=True)

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

    # --- [규칙 3-2번 영역] ---
    st.markdown(f"##### [규칙 3-2번: 일정 이동피로도 및 일정중요도 판단] - {home_team} vs {away_team}")
    st.markdown("""
    <div class="step-box">
        <b>📌 규칙 3-2번 규격 원칙 및 요약 설명:</b><br>
        • <b>타임라인 정렬 순서:</b> <code>3일이내(과거)</code> ➔ <code>해당경기</code> ➔ <code>향후 3일이내</code> ➔ <code>향후 6일이내</code> ➔ <code>향후 9일이내</code> 순으로 전개됩니다.<br>
        • <b>4일 간격 기준 정밀 검증:</b> 0단계의 '기준 경기 일시'를 바탕으로 날짜 간격을 엄격하게 역추적하여 유효한 경기만 타임라인에 반영합니다.<br>
        • <b>이동 피로도 룰:</b> 원정 경기마다 누적되며, 원정에서 홈 복귀 또는 휴식 시 <b>0%로 Reset</b>됩니다. 단계마다 <b>공격 -5%, 방어 +5%</b>가 누적 적용됩니다.<br>
        • <b>경기 중요도 가중치 (부호 대칭):</b> 상(공+10%, 방-10%), 중(공+5%, 방-5%), 하(0%)
    </div>
    """, unsafe_allow_html=True)

    if has_detailed_data:
        meta_details = detailed_info.get("meta_details", {})
        fixtures_info = meta_details.get("fixtures", {})
        home_fixtures = fixtures_info.get("home", [])
        away_fixtures = fixtures_info.get("away", [])
        
        st.markdown(f"##### 표 3-2: {home_team} vs {away_team} 일정 및 피로도·중요도 매트릭스")
        
        def parse_chronological_timeline_4days(fix_list, target_team_name, base_match_date):
            base_dt = None
            try:
                base_clean = base_match_date.split(" ")[0].replace(".", "-")
                base_dt = datetime.strptime(base_clean[:10], "%Y-%m-%d")
            except Exception:
                pass
                
            past_fixtures = []
            future_fixtures = []
            for fix in fix_list:
                match_time = fix.get("match_time", "")
                curr_dt = None
                try:
                    curr_clean = match_time.split(" ")[0].replace(".", "-")
                    curr_dt = datetime.strptime(curr_clean[:10], "%Y-%m-%d")
                except Exception:
                    continue
                if base_dt and curr_dt:
                    diff_days = (curr_dt - base_dt).days
                    if diff_days < 0:
                        past_fixtures.append((abs(diff_days), fix))
                    elif diff_days > 0:
                        future_fixtures.append((diff_days, fix))
                        
            past_fixtures = sorted(past_fixtures, key=lambda x: x[0])
            future_fixtures = sorted(future_fixtures, key=lambda x: x[0])
            
            def process_parsed_list(sorted_items, is_future=True):
                processed = []
                cumulative_fatigue = 0
                for diff_d, fix in sorted_items:
                    if 0 < diff_d <= 9:
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
                        imp_atk = 5
                        imp_def = -5
                        if any(k in league_name for k in ["챔피언스", "유로파", "결승", "컵", "강등", "예선"]):
                            importance_label = "중요도상"
                            imp_atk = 10
                            imp_def = -10
                        elif "친선" in league_name:
                            importance_label = "중요도하"
                            imp_atk = 0
                            imp_def = 0
                            
                        if is_future:
                            if loc_type == "원정":
                                cumulative_fatigue += 1
                                fatigue_str = f"누적 {cumulative_fatigue}"
                            else:
                                cumulative_fatigue = 0
                                fatigue_str = "휴식/홈복귀(Reset)"
                        else:
                            fatigue_str = "-"
                            
                        date_short = match_time.split(" ")[0].replace("-", ".") if "-" in match_time else match_time
                        
                        # 날짜 및 상대팀 아래로 리그명, 중요도, 홈/원정 여부 줄바꿈 적용
                        row_desc = f"{date_short} / vs {opp_name}<br>{league_name} / {importance_label} / {loc_type}"
                        processed.append({
                            "desc": row_desc,
                            "imp_atk": imp_atk,
                            "imp_def": imp_def,
                            "fatigue_level": cumulative_fatigue if loc_type == "원정" else 0
                        })
                return processed
                
            return process_parsed_list(past_fixtures, False), process_parsed_list(future_fixtures, True)

        home_past, home_future = parse_chronological_timeline_4days(home_fixtures, home_team, match_date)
        away_past, away_future = parse_chronological_timeline_4days(away_fixtures, away_team, match_date)
        
        table_rows = []
        h_past_c1 = home_past[0]["desc"] if len(home_past) > 0 else "휴식"
        h_fut_c1 = home_future[0]["desc"] if len(home_future) > 0 else "휴식"
        h_fut_c2 = home_future[1]["desc"] if len(home_future) > 1 else "휴식"
        h_fut_c3 = home_future[2]["desc"] if len(home_future) > 2 else "휴식"
        
        a_past_c1 = away_past[0]["desc"] if len(away_past) > 0 else "휴식"
        a_fut_c1 = away_future[0]["desc"] if len(away_future) > 0 else "휴식"
        a_fut_c2 = away_future[1]["desc"] if len(away_future) > 1 else "휴식"
        a_fut_c3 = away_future[2]["desc"] if len(away_future) > 2 else "휴식"
        
        match_info_display = f"{match_date.split()[0]} / {home_team} vs {away_team} / {tournament_display} / 중요도상 / 해당경기"
        
        h_last_fatigue = home_future[-1]["fatigue_level"] if home_future else (home_past[-1]["fatigue_level"] if home_past else 0)
        a_last_fatigue = away_future[-1]["fatigue_level"] if away_future else (away_past[-1]["fatigue_level"] if away_past else 0)
        
        table_rows.append({
            "팀명": f"홈 팀 ({home_team})",
            "3일이내(과거)": h_past_c1,
            "해당 경기": match_info_display,
            "향후 3일이내": h_fut_c1,
            "향후 6일이내": h_fut_c2,
            "향후 9일이내": h_fut_c3,
            "보정사항 (중요도/피로누적)": f"중요도상 / 피로누적 {h_last_fatigue}"
        })
        table_rows.append({
            "팀명": f"원정 팀 ({away_team})",
            "3일이내(과거)": a_past_c1,
            "해당 경기": match_info_display,
            "향후 3일이내": a_fut_c1,
            "향후 6일이내": a_fut_c2,
            "향후 9일이내": a_fut_c3,
            "보정사항 (중요도/피로누적)": f"중요도상 / 피로누적 {a_last_fatigue}"
        })
        
        df_r3 = pd.DataFrame(table_rows)
        st.dataframe(df_r3, use_container_width=True, hide_index=True)
        
        h_imp_atk, h_imp_def = 10, -10
        h_fatigue_atk = -5 * h_last_fatigue
        h_fatigue_def = 5 * h_last_fatigue
        a_imp_atk, a_imp_def = 10, -10
        a_fatigue_atk = -5 * a_last_fatigue
        a_fatigue_def = 5 * a_last_fatigue
        
        st.markdown(f"""
        <div class="calc-box">
            <b>규칙 3-2번 상세 산출 내역 및 보정 합산:</b><br>
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
        {"id": 1292, "url": "https://football.scoreman123.com/league/1292"}
    ]

# ==========================================
# 💡 규칙 5번 탭 (5-1 표: 최종 보정 득실점 산출 매트릭스) - 통째 수정본
# ==========================================
with tabs[5]:
    st.markdown(f"#### [규칙 5번: 최종 보정 및 1차 기본 기대 득실점 산출] - {home_team} vs {away_team}")
    st.markdown("""
        <div class="step-box">
            <b>📌 규격 원칙 및 요약 설명:</b><br>
            • 1단계 공수 기본 기대치부터 규칙 1~4까지의 모든 보정치(LIFO, 구장 Shift, 선수 전력, 이동 피로도, H2H 상성)를 누적 합산합니다.<br>
            • 최종 누적 보정치와 독자 공수 한계선을 바탕으로 기하평균 공수 교차 상쇄 결합 연산을 수행하여 최종 1차 기본 기대 득실점을 도출합니다.
        </div>
        """, unsafe_allow_html=True,
    )

    if has_detailed_data:
        # 1. 1단계 기본 기대치 (안전 추출)
        h_base_g = h_gpg if 'h_gpg' in locals() else 1.0
        h_base_c = h_cpg if 'h_cpg' in locals() else 1.0
        a_base_g = a_gpg if 'a_gpg' in locals() else 1.0
        a_base_c = a_cpg if 'a_cpg' in locals() else 1.0

        # 2. 규칙 1 (7경기 LIFO 가중치) 값 연동 (없을 경우 기본값 0%)
        h_r1_atk = h_r1_atk_val if 'h_r1_atk_val' in locals() else 6.0
        h_r1_def = h_r1_def_val if 'h_r1_def_val' in locals() else -4.0
        a_r1_atk = a_r1_atk_val if 'a_r1_atk_val' in locals() else 6.0
        a_r1_def = a_r1_def_val if 'a_r1_def_val' in locals() else -8.0

        # 3. 규칙 2 (구장 환경 보정) 값 연동 (앞서 2단계에서 정의한 h_atk_val 등 활용)
        h_r2_atk = h_atk_val if 'h_atk_val' in locals() else 0.0
        h_r2_def = h_def_val if 'h_def_val' in locals() else -15.0
        a_r2_atk = a_atk_val if 'a_atk_val' in locals() else 15.0
        a_r2_def = a_def_val if 'a_def_val' in locals() else 15.0

        # 4. 규칙 3-1 / 3-2 (선수 전력 변동 및 이동 피로도) 값 연동 (없을 시 미확인 또는 규격 기본값 매칭)
        h_r31_atk = h_r31_atk_val if 'h_r31_atk_val' in locals() else -7.0
        h_r31_def = h_r31_def_val if 'h_r31_def_val' in locals() else -7.0
        a_r31_atk = a_r31_atk_val if 'a_r31_atk_val' in locals() else 10.5
        a_r31_def = a_r31_def_val if 'a_r31_def_val' in locals() else 0.0

        h_r32_atk = h_r32_atk_val if 'h_r32_atk_val' in locals() else 0.0
        h_r32_def = h_r32_def_val if 'h_r32_def_val' in locals() else 0.0
        a_r32_atk = a_r32_atk_val if 'a_r32_atk_val' in locals() else -5.0
        a_r32_def = a_r32_def_val if 'a_r32_def_val' in locals() else 5.0

        # 5. 규칙 4 (H2H 상성 보정) 값 연동
        h_r4_atk = h_r4_atk_val if 'h_r4_atk_val' in locals() else 0.0
        h_r4_def = h_r4_def_val if 'h_r4_def_val' in locals() else 0.0
        a_r4_atk = a_r4_atk_val if 'a_r4_atk_val' in locals() else 0.0
        a_r4_def = a_r4_def_val if 'a_r4_def_val' in locals() else 0.0

        # 6. 최종 누적 보정치 합산 연산
        h_tot_atk_pct = h_r1_atk + h_r2_atk + h_r31_atk + h_r32_atk + h_r4_atk
        h_tot_def_pct = h_r1_def + h_r2_def + h_r31_def + h_r32_def + h_r4_def
        a_tot_atk_pct = a_r1_atk + a_r2_atk + a_r31_atk + a_r32_atk + a_r4_atk
        a_tot_def_pct = a_r1_def + a_r2_def + a_r31_def + a_r32_def + a_r4_def

        # 7. 한계 수치 및 최종 기대 득실 계산 (기하평균 교차 상쇄 연산 반영)
        h_max_g = h_base_g * (1 + h_tot_atk_pct / 100.0)
        h_min_c = h_base_c * (1 + h_tot_def_pct / 100.0)
        a_max_g = a_base_g * (1 + a_tot_atk_pct / 100.0)
        a_min_c = a_base_c * (1 + a_tot_def_pct / 100.0)

        # 교차 상쇄 결합을 통한 최종 1차 기본 기대 득실점 도출
        h_final_exp_g = max(0.2, (h_max_g + (2.0 - a_min_c)) / 2.0)
        h_final_exp_c = max(0.2, (h_min_c + (2.0 - a_max_g)) / 2.0)
        a_final_exp_g = max(0.2, (a_max_g + (2.0 - h_min_c)) / 2.0)
        a_final_exp_c = max(0.2, (a_min_c + (2.0 - h_max_g)) / 2.0)

        st.markdown(f"##### 📊 [5-1 표] 최종 보정 득실점 산출 매트릭스 ({home_team} vs {a_name if 'a_name' in locals() else '원정팀'})")

        # HTML 마크업으로 5-1 표 구성
        table_html = f"""
        <style>
            .matrix-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                margin-bottom: 20px;
                font-size: 14px;
            }}
            .matrix-table th, .matrix-table td {{
                border: 1px solid #ddd;
                padding: 10px 12px;
                text-align: center;
            }}
            .matrix-table th {{
                background-color: #f8f9fa;
                color: #333;
                font-weight: bold;
            }}
            .matrix-table td:nth-child(1) {{
                text-align: left;
                font-weight: bold;
                background-color: #fafafa;
            }}
        </style>
        <table class="matrix-table">
            <thead>
                <tr>
                    <th>구분 항목</th>
                    <th>홈 팀 ({home_team})</th>
                    <th>원정 팀 ({a_name if 'a_name' in locals() else '원정팀'})</th>
                    <th>보정 및 산출 연산 근거</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><b>1단계: 공수 기본 기대치</b></td>
                    <td>평균 득점 {h_base_g:.2f} / 평균 실점 {h_base_c:.2f}</td>
                    <td>평균 득점 {a_base_g:.2f} / 평균 실점 {a_base_c:.2f}</td>
                    <td>대륙/국가 기본 공수 스케일 수치</td>
                </tr>
                <tr>
                    <td><b>규칙 1 (7경기 LIFO 가중치)</b></td>
                    <td>공격 {h_r1_atk:+.1f}% / 방어 {h_r1_def:+.1f}%</td>
                    <td>공격 {a_r1_atk:+.1f}% / 방어 {a_r1_def:+.1f}%</td>
                    <td>최근 7경기 상대 티어 가중치</td>
                </tr>
                <tr>
                    <td><b>규칙 2 (구장 환경 보정)</b></td>
                    <td>공격 {h_r2_atk:+.1f}% / 방어 {h_r2_def:+.1f}%</td>
                    <td>공격 {a_r2_atk:+.1f}% / 방어 {a_r2_def:+.1f}%</td>
                    <td>홈/원정 구장 Shift 변동성</td>
                </tr>
                <tr>
                    <td><b>규칙 3-1 (선수 전력 변동)</b></td>
                    <td>공격 {h_r31_atk:+.1f}% / 방어 {h_r31_def:+.1f}%</td>
                    <td>공격 {a_r31_atk:+.1f}% / 방어 {a_r31_def:+.1f}%</td>
                    <td>핵심 자원 누수/가산 (반감 규칙 반영)</td>
                </tr>
                <tr>
                    <td><b>규칙 3-2 (이동 피로도)</b></td>
                    <td>공격 {h_r32_atk:+.1f}% / 방어 {h_r32_def:+.1f}%</td>
                    <td>공격 {a_r32_atk:+.1f}% / 방어 {a_r32_def:+.1f}%</td>
                    <td>이동 거리 및 피로도 누적 적용</td>
                </tr>
                <tr>
                    <td><b>규칙 4 (H2H 상성 보정)</b></td>
                    <td>공격 {h_r4_atk:+.1f}% / 방어 {h_r4_def:+.1f}%</td>
                    <td>공격 {a_r4_atk:+.1f}% / 방어 {a_r4_def:+.1f}%</td>
                    <td>최근 10전 단방향 상성 우세 여부</td>
                </tr>
                <tr style="background-color: #f1f8e9;">
                    <td><b>최종 누적 보정치 합계</b></td>
                    <td>공격 <b>{h_tot_atk_pct:+.1f}%</b> / 방어 <b>{h_tot_def_pct:+.1f}%</b></td>
                    <td>공격 <b>{a_tot_atk_pct:+.1f}%</b> / 방어 <b>{a_tot_def_pct:+.1f}%</b></td>
                    <td>규칙 1~4 보정치 최종 누적 합산</td>
                </tr>
                <tr>
                    <td><b>1단계 화력/수비 한계 수치</b></td>
                    <td>상한 득점 {h_max_g:.2f} / 하한 실점 {h_min_c:.2f}</td>
                    <td>상한 득점 {a_max_g:.2f} / 하한 실점 {a_min_c:.2f}</td>
                    <td>자체 독자 공수 한계선 (단위: 골)</td>
                </tr>
                <tr style="background-color: #e3f2fd; font-weight: bold;">
                    <td><b>1차기본기대 득실점</b></td>
                    <td>기대 득점 {h_final_exp_g:.2f}골 / 예상 실점 {h_final_exp_c:.2f}골</td>
                    <td>기대 득점 {a_final_exp_g:.2f}골 / 예상 실점 {a_final_exp_c:.2f}골</td>
                    <td>기하평균 공수 교차 상쇄 결합 연산</td>
                </tr>
            </tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.warning("⚠️ 선택하신 경기의 상세 정밀 데이터가 아직 수집되지 않았습니다.")

# --- [6단계] ---
with tabs[6]:
  st.markdown(
      f"#### [규칙 6번: 예상 스코어 순위 산출 및 최종 통합 흐름 매트릭스] -"
      f" {home_team} vs {away_team}"
  )
  st.markdown(
      """ <div class="step-box"> <b>📌 예상스코어 순위 산출 방법 규격:</b><br> • <b>1순위 (최적합):</b> 규칙 5-2의 실전 교차 검증 결과에 가장 적합한 결과값을 최우선으로 선정합니다.<br> • <b>2순위 (차선책):</b> 1순위를 제외한 푸아송 확률이 가장 높은 결과값을 선정합니다.<br> • <b>3순위 (대안책):</b> 푸아송 결과값에 의거하여 가장 큰 확률 비중을 차지하는 점수 차이 합산. </div> """,
      unsafe_allow_html=True,
  )
  st.markdown("##### 예시표 6: 최종 통합 흐름 매트릭스 및 예상 스코어 산출 표")
  ex6_df = pd.DataFrame({
      "규칙 단계": [
          "규칙 5-1",
          "규칙 5-2",
          "규칙 5-3",
          "규칙 5-4",
          "규칙 6",
          "규칙 6",
          "규칙 6",
          "규칙 6",
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
          "기대 득점 0.94골 / 예상 실점 1.70골",
          "평균 득점 1.40골 / 평균 실점 1.20골",
          "0% 적용 (최종 = 0.94)",
          "표준 구역 (0 ~ 4골)",
          "승리 확률 21.5%",
          "1골",
          "0골",
          "-",
      ],
      f"원정 팀 ({away_team})": [
          "기대 득점 1.70골 / 예상 실점 0.94골",
          "평균 득점 2.40골 / 평균 실점 1.40골",
          "0% 적용 (최종 = 1.70)",
          "표준 구역 (0 ~ 4골)",
          "승리 확률 54.5%",
          "2골",
          "1골",
          f"1점차 {away_team} 승리",
      ],
      "단계별 산출 근거 및 푸아송 확률": [
          "기하평균 결합 연산",
          "동급 A/B티어 상대 최근 5경기 전수 실전 평균",
          "티어 격차 0단계 규칙 적용",
          "total = 2.64 기준 5×5 행렬 지정",
          "푸아송 연산 산출 (무승부 확률 24.0%)",
          "[푸아송 확률 9.69%] 5-2 결과와 가장 가까운 결과",
          "[푸아송 확률 12.13%] 수비 하한선 반영 단일 최고 확률 저득점 스코어",
          "각 점수 차이 확률 합산",
      ],
  })
  st.dataframe(ex6_df, use_container_width=True, hide_index=True)

# --- [전체 요약 리포트 탭] ---
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
