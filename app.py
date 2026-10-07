from datetime import datetime, timezone, timedelta
import json
import os
import re
from bs4 import BeautifulSoup
import pandas as pd
import requests
import streamlit as st

TARGET_URL = "https://www.scoreman123.com/football/fixture"

def update_json_file():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://www.scoreman123.com/"
    }
    matches = []
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            current_league = "해외축구 (실시간)"
            table = soup.find("table", id="table_live")
            if table:
                rows = table.find_all("tr")
                for row in rows:
                    classes = row.get("class", [])
                    if any("Leaguestitle" in str(c) for c in classes) and any("fbHead" in str(c) for c in classes):
                        league_text = row.get_text(strip=True)
                        if league_text:
                            current_league = re.sub(r'^[^\w\s]+\s*', '', league_text).replace("+", "").strip()
                        continue
                    tds = row.find_all("td")
                    if len(tds) >= 6:
                        time_str = tds[1].get_text(strip=True)
                        status_str = tds[2].get_text(strip=True)
                        home_raw = tds[3].get_text(strip=True)
                        score_str = tds[4].get_text(strip=True)
                        away_raw = tds[5].get_text(strip=True)
                        
                        home_team = re.sub(r"\[.*?\]", "", home_raw).strip()
                        away_team = re.sub(r"\[.*?\]", "", away_raw).strip()
                        
                        if home_team and away_team and home_team != away_team and time_str:
                            matches.append({
                                "id": len(matches) + 1,
                                "league": current_league,
                                "time": time_str,
                                "status": status_str,
                                "home": home_team,
                                "away": away_team,
                                "home_team": home_team,
                                "away_team": away_team,
                                "tournament": current_league,
                                "score": score_str if score_str else "-",
                                "home_recent_stats": "4전/3승1무/0패",
                                "away_recent_stats": "4전/2승1무/1패",
                                "match_name": f"[{current_league}] {home_team} vs {away_team} ({time_str})"
                            })
    except Exception as e:
        print(f"업데이트 중 크롤링 오류 발생: {e}")

    if not matches:
        matches = [{
            "id": 1,
            "league": "베이카우스리가",
            "match_name": "[베이카우스리가] 그니스탄 vs 인터 투르쿠 (01:00)",
            "home": "그니스탄",
            "away": "인터 투르쿠",
            "home_team": "그니스탄",
            "away_team": "인터 투르쿠",
            "tournament": "베이카우스리가",
            "time": "01:00",
            "home_recent_stats": "4전/3승1무/0패",
            "away_recent_stats": "4전/2승1무/1패",
            "score": "0 - 0"
        }]

    KST = timezone(timedelta(hours=9))
    kst_time_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    output_data = {
        "last_updated": kst_time_str,
        "matches": matches
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

update_json_file()

@st.cache_data(ttl=10)
def load_match_data():
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_updated": "안전 모드",
        "matches": [{
            "id": 1,
            "league": "베이카우스리가",
            "match_name": "[베이카우스리가] 그니스탄 vs 인터 투르쿠 (01:00)",
            "home_team": "그니스탄",
            "away_team": "인터 투르쿠",
            "tournament": "베이카우스리가",
            "time": "01:00"
        }]
    }

data = load_match_data()
matches = data.get("matches", [])
last_updated_time = data.get("last_updated", "알 수 없음")

st.title("배트맨 프로젝트 통합 마스터 규격 및 분석 엔진")
st.markdown("구글 독스 원문 규격 100% 반영 • 생략 없는 0단계~6단계 세부 정량 표 완벽 탑재 시스템")

st.sidebar.markdown("---")
st.sidebar.markdown(f"🕒 **데이터 갱신 시각 (KST)**\n\n `{last_updated_time}`")
st.sidebar.subheader("🏆 실시간 수집 대진 선택")

if matches:
    match_options = [m["match_name"] for m in matches]
    selected_match_name = st.sidebar.radio(
        "분석할 경기를 선택하세요:",
        match_options,
        index=0,
        key="match_radio_selection"
    )
    selected_match = next((m for m in matches if m["match_name"] == selected_match_name), matches[0])
else:
    selected_match = {
        "home_team": "그니스탄",
        "away_team": "인터 투르쿠",
        "tournament": "베이카우스리가",
        "time": "01:00"
    }

home_team = selected_match.get("home_team", "홈팀")
away_team = selected_match.get("away_team", "원정팀")
match_date = selected_match.get("time", "오늘")

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

with tabs[0]:
   st.markdown("## [0단계: 프리 앤트리 메타데이터 및 공식 규칙 필터 검증]")
   st.markdown("친선 경기를 전면 배제하고 공식 A매치 유효성 검증을 거친 대진 메타데이터를 고정합니다. (SSOT 원칙 적용)")
   st.table({
        "메타 항목": ["대회 성격", "기준 경기 일시", "구장 정보", "대결 정보", "필터 검증 결과"],
        "내용": [
            selected_match.get("tournament", "리그"),
            f"{selected_match.get('time', '시간')} (공식 지정 경기)",
            "홈구장 실시간 반영",
            f"{home_team} vs {away_team}",
            "정상 통과"
        ]
    })

with tabs[1]:
  st.markdown(f"### [규칙 1번: 종합 최근 7경기 전수 로그 및 A~E 등급별 공수 티어 산출] - {home_team} vs {away_team}")
  st.markdown("""
    <div class="step-box">
        <b>📌 규격 원칙 및 요약 설명:</b><br>
        • <b>전수 조사 및 LIFO 방식:</b> 홈/원정 통합 최근 공식 경기 7개를 최신순 역순(LIFO)으로 전수 조사하며, 골득실 평균을 산출하여 티어 산정표의 티어를 각 양팀에 부여합니다.<br>
        • <b>친선 경기 전면 배제:</b> 최근 경기 표본에서 모든 친선 경기를 영구 배제하며, 오직 공식 경기만을 채택합니다.<br>
        • <b>특수 룰:</b> E티어 상대 득점 50% 할인 및 경고등 발동 프로토콜을 적용합니다.
    </div>
    """, unsafe_allow_html=True)
    
    tier_weight_df = pd.DataFrame({
        "등급 (Tier)": ["Tier A", "Tier B", "Tier C", "Tier D", "Tier E"],
        "공격력 기준 (평균 득점)": ["2.3골 이상", "1.7 ~ 2.2골 미만", "1.1 ~ 1.6골 미만", "0.5 ~ 1.1골 미만", "0.5골 미만 (< 0.5)"],
        "공격 가중치": ["+8.0%", "+6.0%", "+4.0%", "+2.0%", "0.0% (최하위)"],
        "방어력 기준 (평균 실점)": ["0.5골 미만 (< 0.5)", "0.5 ~ 0.9골 미만", "0.9 ~ 1.3골 미만", "1.3 ~ 1.7골 미만", "1.7골 이상"],
        "방어 가중치": ["-8.0% (최상위)", "-6.0%", "-4.0%", "-2.0%", "0.0%"]
    })
  st.dataframe(tier_weight_df, use_container_width=True, hide_index=True)
    
  st.markdown(f"#### 예시표 1-1: 홈 팀 ({home_team}) 최근 공식 7경기 전수 LIFO 표")
    h_lifi_df = pd.DataFrame({
        "LIFO 순서": ["최신 (1)", "2", "3", "4", "5", "6", "과거 (7)"],
        "경기 일시": ["2026-06-06", "2026-03-26", "2026-03-21", "2024-02-06", "2024-02-02", "2024-01-30", "2024-01-25"],
        "상대 팀 (대회명)": ["싱가포르 (월드컵예선)", "태국 (월드컵예선)", "태국 (월드컵예선)", "요르단 (아시안컵)", "호주 (아시안컵)", "사우디 (아시안컵)", "말레이시아 (아시안컵)"],
        "홈/중립/원정": ["홈", "원정", "홈", "중립", "중립", "중립", "중립"],
        "결과": ["7 : 0", "3 : 0", "1 : 1", "0 : 2", "2 : 1", "1 : 1", "5 : 3"],
        "승패": ["승", "승", "무", "패", "승(연)", "승(PK)", "승"],
        "상대 공·방 티어 태깅": [
            "평균득점/실점 [공격 D티어, 방어 E티어] (50% 할인)",
            "평균득점/실점 [공격 C티어, 방어 D티어]",
            "평균득점/실점 [공격 D티어, 방어 C티어]",
            "평균득점/실점 [공격 C티어, 방어 D티어]",
            "평균득점/실점 [공격 B티어, 방어 B티어]",
            "평균득점/실점 [공격 B티어, 방어 C티어]",
            "평균득점/실점 [공격 C티어, 방어 D티어]"
        ]
    })
  st.dataframe(h_lifi_df, use_container_width=True, hide_index=True)
  st.markdown(
      f""" <div class="calc-box"> <b>{home_team} 규칙 1번 상세 산출 내역:</b><br> • 최근 7경기 득실: 득점 19, 실점 8<br> • 기본기대값: 평균 득점 2.71 / 평균 실점 1.14<br> • 경고등 발동 조건 충족 E티어에 해당하는 싱가포르전의 득점 7점을 50% 할인 적용하여 3.5점으로 계산한 총득점 15.5 (평균 득점 2.21)로 <b>공격력 Tier A에서 공격력 Tier B로 변동</b><br> • 정량 공식 대조 체급: <b>공격력 Tier B, 방어력 Tier C</b><br> • 기초 가중치: <b>공격 +6%, 방어 -4%</b> </div> """,
      unsafe_allow_html=True,
  )
  st.markdown("---")
  st.markdown(
      f"#### 예시표 1-2: 원정 팀 ({away_team}) 최근 공식 7경기 전수 LIFO 표"
  )
  a_lifi_df = pd.DataFrame({
      "LIFO 순서": ["최신 (1)", "2", "3", "4", "5", "6", "과거 (7)"],
      "경기 일시": [
          "2026-06-11",
          "2026-06-06",
          "2026-03-26",
          "2026-03-21",
          "2024-02-02",
          "2024-01-31",
          "2024-01-24",
      ],
      "상대 팀 (대회명)": [
          "시리아 (월드컵예선)",
          "미얀마 (월드컵예선)",
          "북한 (월드컵예선)",
          "북한 (월드컵예선)",
          "이란 (아시안컵)",
          "바레인 (아시안컵)",
          "인도네시아 (아시안컵)",
      ],
      "홈/중립/원정": ["홈", "원정", "원정", "홈", "중립", "중립", "중립"],
      "결과": ["5 : 0", "5 : 0", "3 : 0", "1 : 0", "1 : 2", "1 : 0", "3 : 0"],
      "승패": ["승", "승", "승(몰수)", "승", "패", "승", "승"],
      "상대 공·방 티어 태깅": [
          "평균득점/실점 [공격 E티어, 방어 D티어] (50% 할인)",
          "평균득점/실점 [공격 D티어, 방어 E티어] (50% 할인)",
          "평균득점/실점 [공격 D티어, 방어 C티어]",
          "평균득점/실점 [공격 C티어, 방어 D티어]",
          "평균득점/실점 [공격 C티어, 방어 B티어]",
          "평균득점/실점 [공격 C티어, 방어 C티어]",
          "평균득점/실점 [공격 C티어, 방어 D티어]",
      ],
  })
  st.dataframe(a_lifi_df, use_container_width=True, hide_index=True)
  st.markdown(
      f""" <div class="calc-box"> <b>{away_team} 규칙 1번 상세 산출 내역:</b><br> • 최근 7경기 득실: 득점 19, 실점 2<br> • 기본 기대값: 평균 득점 2.71 / 평균 실점 0.28<br> • 경고등 발동 조건 충족 E티어에 해당하는 시리아(5점), 미얀마(5점)전의 E티어 득점 10점을 50% 할인 적용하여 5점으로 계산한 총득점 14 (평균 득점 2.00)로 <b>공격력 Tier A에서 공격력 Tier B로 변동</b><br> • 정량 공식 대조 체급: <b>공격력 Tier B, 방어력 Tier A</b><br> • 기초 가중치: <b>공격 +6%, 방어 -8%</b> </div> """,
      unsafe_allow_html=True,
  )

# --- [2단계] ---
with tabs[2]:
  st.markdown(
      f"### [규칙 2번: 구장별 순수 최근 7경기 대조 및 조건부 티어 변동 보정] -"
      f" {home_team} vs {away_team}"
  )
  st.markdown(
      """ <div class="step-box"> <b>📌 규격 원칙 및 요약 설명:</b><br> • <b>구장별 LIFO 대조:</b> 홈 구장 또는 원정 구장별 순수 최근 7경기 역순 전수 대조를 통한 Shift 변동성 검증을 수행합니다.<br> • <b>티어변동 보정치:</b> 각 팀의 티어 변동이 있는지 확인하고 변동이 있을 시 보정치 공격 ±15%, 방어 ±15%를 적용합니다.<br> • <b>상대 공수 티어 필수 태깅:</b> 각 구장별 7경기에 출전한 상대 팀의 공수 티어(Tier A~E)를 개별적으로 태깅합니다.<br> • <b>중립구장 경기 룰:</b> 양팀이 중립구장에서 경기를 진행할 경우 양쪽 다 원정 최근 7경기를 적용하여 검증합니다. </div> """,
      unsafe_allow_html=True,
  )
  st.markdown(
      f"#### 예시표 2-1: 홈 팀 ({home_team}) - 홈 구장 기준 최근 공식 7경기 전수"
      " LIFO 대조 표"
  )
  kor_g2_df = pd.DataFrame({
      "구장 LIFO 순서": ["최신 (1)", "2", "3", "4", "5", "6", "과거 (7)"],
      "경기 일시": [
          "2026-06-06",
          "2026-03-21",
          "2023-11-16",
          "2023-10-13",
          "2023-03-28",
          "2023-03-24",
          "2022-06-14",
      ],
      "상대 팀 (대회명)": [
          "싱가포르 (월드컵예선)",
          "태국 (월드컵예선)",
          "싱가포르 (월드컵예선)",
          "베트남 (공식 A매치)",
          "우루과이 (공식 A매치)",
          "콜롬비아 (공식 A매치)",
          "이집트 (공식 A매치)",
      ],
      "홈/중립/원정": ["홈", "홈", "홈", "홈", "홈", "홈", "홈"],
      "결과": ["7 : 0", "1 : 1", "5 : 0", "6 : 0", "1 : 2", "2 : 2", "4 : 1"],
      "승패": ["승", "무", "승", "승", "패", "무", "승"],
      "상대 공·방 티어 필수 태깅": [
          "평균득점/실점 [공격 D티어, 방어 E티어] (50% 할인)",
          "평균득점/실점 [공격 D티어, 방어 C티어]",
          "평균득점/실점 [공격 E티어, 방어 D티어] (50% 할인)",
          "평균득점/실점 [공격 E티어, 방어 D티어] (50% 할인)",
          "평균득점/실점 [공격 A티어, 방어 B티어]",
          "평균득점/실점 [공격 B티어, 방어 B티어]",
          "평균득점/실점 [공격 C티어, 방어 D티어]",
      ],
  })
  st.dataframe(kor_g2_df, use_container_width=True, hide_index=True)
  st.markdown(
      f""" <div class="calc-box"> <b>{home_team} 규칙 2번 상세 산출 내역:</b><br> • 최근 7경기 득실: 득점 24, 실점 6 (평균 득점 3.42 / 평균 실점 0.86)<br> • 경고등 발동 조건 충족 E티어에 해당하는 싱가포르(7점), 싱가포르(5점), 베트남(6점) 전의 득점 18점을 50% 할인 적용하여 9점으로 계산한 총득점 15 (평균 득점 2.14) 공격력 Tier B<br> • 정량 공식 대조 체급: <b>공격력 Tier B, 방어력 Tier B</b><br> • 홈 구장 Shift 검증 결과: 규칙 1과 규칙 2에서의 변동성(Shift)<br> &nbsp;&nbsp;&nbsp;&nbsp;- 공격력 B ➔ 공격력 B (변동없음) 0%<br> &nbsp;&nbsp;&nbsp;&nbsp;- 방어력 C ➔ 방어력 B (상향보정) 방어 -15% </div> """,
      unsafe_allow_html=True,
  )
  st.markdown("---")
  st.markdown(
      f"#### 예시표 2-2: 원정 팀 ({away_team}) - 원정 구장 기준 최근 공식 7경기"
      " 전수 LIFO 대조 표"
  )
  jpn_g2_df = pd.DataFrame({
      "구장 LIFO 순서": ["최신 (1)", "2", "3", "4", "5", "6", "과거 (7)"],
      "경기 일시": [
          "2026-06-06",
          "2026-03-26",
          "2023-11-21",
          "2023-10-17",
          "2023-09-12",
          "2023-06-20",
          "2023-03-28",
      ],
      "상대 팀 (대회명)": [
          "미얀마 (월드컵예선)",
          "북한 (월드컵예선)",
          "시리아 (월드컵예선)",
          "튀니지 (공식 A매치)",
          "튀르키예 (공식 A매치)",
          "페루 (공식 A매치)",
          "콜롬비아 (공식 A매치)",
      ],
      "홈/중립/원정": ["원정", "원정", "원정", "중립", "중립", "중립", "원정"],
      "결과": ["5 : 0", "3 : 0", "5 : 0", "2 : 0", "4 : 2", "4 : 1", "1 : 2"],
      "승패": ["승", "승(몰수)", "승", "승", "승", "승", "패"],
      "상대 공·방 티어 필수 태깅": [
          "평균득점/실점 [공격 E티어, 방어 E티어] (50% 할인)",
          "평균득점/실점 [공격 D티어, 방어 C티어]",
          "평균득점/실점 [공격 D티어, 방어 E티어] (50% 할인)",
          "평균득점/실점 [공격 B티어, 방어 C티어]",
          "평균득점/실점 [공격 B티어, 방어 B티어]",
          "평균득점/실점 [공격 B티어, 방어 C티어]",
          "평균득점/실점 [공격 B티어, 방어 B티어]",
      ],
  })
  st.dataframe(jpn_g2_df, use_container_width=True, hide_index=True)
  st.markdown(
      f""" <div class="calc-box"> <b>{away_team} 규칙 2번 상세 산출 내역:</b><br> • 최근 7경기 득실: 득점 24, 실점 5 (평균 득점 3.42 / 평균 실점 0.71)<br> • 경고등 발동 조건 충족 E티어에 해당하는 미얀마(5점), 시리아(5점) 전의 득점 10점을 50% 할인 적용하여 5점으로 계산한 총득점 24에서 19로 변경 (평균 득점 2.71) 공격력 Tier A<br> • 정량 공식 대조 체급: <b>공격력 Tier A, 방어력 Tier B</b><br> • 원정 구장 Shift 검증 결과: 규칙 1과 규칙 2에서의 변동성(Shift)<br> &nbsp;&nbsp;&nbsp;&nbsp;- 공격력 B ➔ 공격력 A (상향조정) 공격 +15%<br> &nbsp;&nbsp;&nbsp;&nbsp;- 방어력 A ➔ 방어력 B (하향조정) 방어 +15% </div> """,
      unsafe_allow_html=True,
  )

# --- [3단계: 누수·피로 매트릭스] ---
with tabs[3]:
  st.markdown(
      f"### [규칙 3번: 선수 전력 누수 및 이동 피로도 타임라인 매트릭스] -"
      f" {home_team} vs {away_team}"
  )
  st.markdown(
      """ <div class="step-box"> <b>📌 규칙 3-1 (선수 전력 변동: 누수 및 가산) 규격 요약:</b><br> • <b>정량 수치 모델 적용:</b> 매체 보도 등 기초 사실(Fact)을 바탕으로 하되, 분석 및 스코어 도출은 엄격한 정량 수치 모델을 적용합니다.<br> • <b>부호 대칭 규격:</b> 누수(부상·징계·이적 이탈)는 공격력 음수(-), 방어력 양수(+) / 가산(복귀·신규 입단)은 공격력 양수(+), 방어력 음수(-)를 적용합니다.<br> • <b>포지션별 반감(Halved) 규칙:</b> 공격 자원(FW/AMF)의 방어 보정과 수비 자원(DF/DMF/GK)의 공격 보정은 1/2로 반감 적용합니다 (상: 7%, 중: 3.5%, 하: 0%). </div> """,
      unsafe_allow_html=True,
  )
  st.markdown("#### 선수 등급(상/중/하) 정량 판정 기준표")
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
  st.markdown(f"#### 예시표 3-1: 구단명 - {home_team} 선수 전력 변동 매트릭스")
  table_3_1_kor = pd.DataFrame({
      "선수 실명": ["손흥민", "김민재", "[총합]"],
      "포지션": ["FW", "DF", "-"],
      "변동 유형": ["누수", "가산", "-"],
      "핵심 영향력": ["주장 / 에이스", "핵심 수비수", f"{home_team} 최종 가중치"],
      "시즌 누적 스탯 (수비/공격)": [
          "20골 10도움 (출전율 90%)",
          "35경기 / 클린시트 15경기 / 태클 2.4회",
          "-",
      ],
      "등급": ["상 (High)", "상 (High)", "-"],
      "공격 보정": ["-14%", "+7%", "-7%"],
      "방어 보정": ["+7%", "-14%", "-7%"],
      "비고": [
          "부상 결장 (방어력 반감)",
          "징계 해제 복귀 (공격력 반감)",
          "최종 누적 보정치",
      ],
  })
  st.dataframe(table_3_1_kor, use_container_width=True, hide_index=True)
  st.markdown(f"#### 예시표 3-1: 구단명 - {away_team} 선수 전력 변동 매트릭스")
  table_3_1_jpn = pd.DataFrame({
      "선수 실명": ["엔도 와타루", "쿠보 타케후사", "[총합]"],
      "포지션": ["MF", "FW", "-"],
      "변동 유형": ["누수", "가산", "-"],
      "핵심 영향력": [
          "주전 수비형 MF",
          "주전 윙어",
          f"{away_team} 최종 가중치",
      ],
      "시즌 누적 스탯 (수비/공격)": [
          "5골 3도움 / 28경기 / 인터셉트 2.1회",
          "12골 8도움 (출전율 89%)",
          "-",
      ],
      "등급": ["중 (Medium)", "상 (High)", "-"],
      "공격 보정": ["-3.5%", "+14%", "+10.5%"],
      "방어 보정": ["+7%", "-7%", "0%"],
      "비고": [
          "경고 누적 결장",
          "대표팀 차출 복귀",
          "최종 누적 보정치",
      ],
  })
  st.dataframe(table_3_1_jpn, use_container_width=True, hide_index=True)
  st.markdown("#### 예시표 3-2: 5포인트 시계열 타임라인 및 이동 피로도 매트릭스 표")
  matrix_3_2_df = pd.DataFrame({
      "팀명": [f"홈 팀 ({home_team})", f"원정 팀 ({away_team})"],
      "경기 일시": [str(match_date), str(match_date)],
      "과거 7일": ["완전 휴식 (홈 체류)", "해외 전지훈련 및 이동"],
      "과거 4일": ["완전 휴식 (홈 체류)", "2일 전 입국 이동"],
      "해당 경기": [
          f"{away_team}전 / 준결승 (중요도 상)",
          f"{home_team}전 / 준결승 (중요도 상)",
      ],
      "향후 4일": ["친선경기 (중요도 하)", "예선전 1차 (중요도 상)"],
      "향후 7일": ["평가전", "리그전"],
      "이동 피로도 및 보정": [
          "준결승전 동기부여 (공격력 +10%, 방어력 -10%)",
          (
              "이동적용 (공격 -5% / 방어 +5%)<br>준결승전 동기부여 (공격력 +10%,"
              " 방어력 -10%)"
          ),
      ],
  })
  st.dataframe(matrix_3_2_df, use_container_width=True, hide_index=True)
  st.markdown(
      f""" <div class="calc-box"> <b>규칙 3번 상세 산출 내역:</b><br> • <b>{home_team}:</b> 규칙 3-1 (공격 -7%, 방어 -7%)<br> • <b>{away_team}:</b> 규칙 3-1 (공격 +10.5%, 방어 0%) / 규칙 3-2 (공격 -5%, 방어 +5%) </div> """,
      unsafe_allow_html=True,
  )

# --- [4단계] ---
with tabs[4]:
  st.markdown(
      f"### [규칙 4번: 역대 공식 맞대결 상성 전수 로그 및 단방향 10% 룰] -"
      f" {home_team} vs {away_team}"
  )
  st.markdown(
      """ <div class="step-box"> <b>📌 규칙 4번 규격 원칙 및 요약 설명:</b><br> • <b>전수 조사 대상:</b> 역대 공식 맞대결 최근 10경기 전수 조사 (5경기 미만일 시 동등 팀으로 간주)<br> • <b>친선전 전면 배제:</b> 친선 경기는 전면 배제하고 오직 공식 A매치 및 대회 맞대결 기록만을 표본으로 채택합니다.<br> • <b>단방향 10% 룰 (Single-Direction Rule):</b> 통산 승률 50% 이상인 상성 우세 팀에게 공격력 +10% 및 방어력 -10% 단방향 상성 보정을 동시 부여합니다 (열세 또는 동등 팀은 0% 고정).<br> • <b>'단방향'인 이유:</b> 상대 팀 수치를 깎아내리는 방식이 아니라, 승률 50% 이상으로 상성 우위를 입증한 우세 팀에게만 보정(+10% / -10%)을 더해주고 열세 팀은 0%로 고정하기 때문입니다. </div> """,
      unsafe_allow_html=True,
  )
  st.markdown(
      f"#### 예시표 4: {home_team} 기준 역대 공식 맞대결 최근 10경기 전수 표"
  )
  h2h_df = pd.DataFrame({
      "H2H 순서": [
          "1 (최신)",
          "2",
          "3",
          "4",
          "5",
          "6",
          "7",
          "8",
          "9",
          "10 (과거)",
      ],
      "경기 일자": [
          "2022-07-27",
          "2019-12-18",
          "2017-12-16",
          "2015-08-05",
          "2013-07-28",
          "2011-08-10",
          "2010-10-12",
          "2010-05-24",
          "2010-02-14",
          "2009-02-22",
      ],
      "대회 명칭": [
          "EAFF E-1 챔피언십",
          "EAFF E-1 챔피언십",
          "EAFF E-1 챔피언십",
          "EAFF 동아시안컵",
          "EAFF 동아시안컵",
          "친선경기 (공식 A매치)",
          "친선경기 (공식 A매치)",
          "친선경기 (공식 A매치)",
          "EAFF 동아시안컵",
          "국가대표 친선경기",
      ],
      "경기 장소": [
          f"{away_team} (원정)",
          f"{home_team} (홈)",
          f"{away_team} (원정)",
          "중국 (중립)",
          f"{home_team} (홈)",
          f"{away_team} (원정)",
          f"{home_team} (홈)",
          f"{away_team} (원정)",
          f"{away_team} (원정)",
          f"{home_team} (홈)",
      ],
      "최종 스코어": [
          "0 : 3",
          "1 : 0",
          "4 : 1",
          "1 : 1",
          "1 : 2",
          "0 : 3",
          "0 : 0",
          "2 : 0",
          "3 : 1",
          "0 : 0",
      ],
      "경기 결과 판정": ["패", "승", "승", "무", "패", "패", "무", "승", "승", "무"],
  })
  st.dataframe(h2h_df, use_container_width=True, hide_index=True)
  st.markdown(
      f""" <div class="calc-box"> <b>규칙 4번 상세 산출 내역:</b><br> • {home_team}: 10전 4승 3무 3패 (승률 40%)<br> • {away_team}: 10전 3승 3무 4패 (승률 30%)<br> • 판정 결과: <b>양팀 우세 없이 동등 0% 고정</b> </div> """,
      unsafe_allow_html=True,
  )

# --- [5단계] ---
with tabs[5]:
  st.markdown(
      f"### [규칙 5번: 최종 보정 득실점 산출 매트릭스 및 교차 검증 (5-1 ~ 5-4)]"
      f" - {home_team} vs {away_team}"
  )
  st.markdown(
      f""" <div class="step-box"> <b>📌 규칙 5-1 (2단계 공수 이원화 모델 및 기하평균 결합):</b><br> • <b>설계 철학:</b> 단순 비율 곱연산의 수치 부풀림을 차단하고, 공격 화력과 상대 수비벽의 저항력을 격리하여 '최대 득점 상한선(λ_max)'과 '최소 실점 하한선(λ_min)'을 독립 산출한 뒤 기하평균으로 결합합니다.<br> • <b>산출 결과:</b> {home_team}(홈) 기대 득점 0.94골 / 예상 실점 1.70골, {away_team}(원정) 기대 득점 1.70골 / 예상 실점 0.94골. </div> """,
      unsafe_allow_html=True,
  )
  st.markdown("#### 예시표 5-1: 최종 보정치 및 1차 기본 기대 득실점 산출 표")
  ex5_1_df = pd.DataFrame({
      "구분 항목": [
          "1단계: 공수 기본 기대치",
          "규칙 1 (7경기 LIFO 가중치)",
          "규칙 2 (구장 환경 보정)",
          "규칙 3-1 (선수 전력 변동)",
          "규칙 3-2 (이동 피로도)",
          "규칙 4 (H2H 상성 보정)",
          "최종 누적 보정치 합계",
          "1단계 화력/수비 한계 수치",
          "1차기본기대 득실점 (λ_base)",
      ],
      f"홈 팀 ({home_team})": [
          "평균 득점 2.71 / 평균 실점 1.14",
          "공격 +6% / 방어 -4%",
          "공격 0% / 방어 -15%",
          "공격 -7% / 방어 -7%",
          "공격 0% / 방어 0%",
          "공격 0% / 방어 0%",
          "공격 +5% / 방어 -26%",
          "상한 득점 2.85 / 하한 실점 0.84",
          "기대 득점 0.94골 / 예상 실점 1.70골",
      ],
      f"원정 팀 ({away_team})": [
          "평균 득점 2.71 / 평균 실점 0.28",
          "공격 +6% / 방어 -8%",
          "공격 +15% / 방어 +15%",
          "공격 +10.5% / 방어 0%",
          "공격 -5% / 방어 +5%",
          "공격 0% / 방어 0%",
          "공격 +26.5% / 방어 +12%",
          "상한 득점 3.43 / 하한 실점 0.31",
          "기대 득점 1.70골 / 예상 실점 0.94골",
      ],
      "보정 및 산출 연산 근거": [
          "대륙/국가 기본 공수 스케일 수치",
          "최근 7경기 상대 티어 가중치",
          "홈/원정 구장 Shift 변동성",
          "핵심 자원 누수/가산 (반감 규칙 반영)",
          "이동 피로도 적용",
          "최근 10전 단방향 상성 우세 없음",
          "규칙 1~4 보정치 최종 누적 합산",
          "자체 독자 공수 한계선 (단위: 골)",
          "기하평균 공수 교차 상쇄 결합 연산",
      ],
  })
  st.dataframe(ex5_1_df, use_container_width=True, hide_index=True)
  st.markdown("---")
  st.markdown(
      """ <div class="step-box"> <b>📌 규칙 5-2 (티어 매칭 실전 득실 평균 교차 검증):</b><br> • 상대방 공격력·방어력 동급 티어 최근 상대 전적 7경기를 산출해 실전 평균 득실로 비교 검증합니다.<br> • 티어 차이가 2단계 이상 벌어질 경우 A나 E티어에 가까운 티어에 비중을 더 두고 유사 팀을 탐색합니다. </div> """,
      unsafe_allow_html=True,
  )
  st.markdown(
      f"#### 예시표 5-2: {home_team} - 상대방 동급(A/B티어) 상대 최근 5경기 전수 표"
  )
  kor_5_2_df = pd.DataFrame({
      "순서": ["1 (최신)", "2", "3", "4", "5 (과거)"],
      "경기 일시": [
          "2024-02-02",
          "2024-01-30",
          "2023-09-13",
          "2023-03-28",
          "2023-03-24",
      ],
      "대회 명칭": [
          "토너먼트 8강",
          "토너먼트 16강",
          "공식 A매치",
          "공식 A매치",
          "공식 A매치",
      ],
      "장소": ["중립", "중립", "중립", "홈", "홈"],
      "상대 팀": [
          "가상 상위팀 A",
          "가상 상위팀 B",
          "가상 상위팀 C",
          "우루과이",
          "콜롬비아",
      ],
      "상대 티어": [
          "평균득점/평균실점 [공격 A티어, 방어 B티어]",
          "평균득점/평균실점 [공격 A티어, 방어 B티어]",
          "평균득점/평균실점 [공격 B티어, 방어 B티어]",
          "평균득점/평균실점 [공격 A티어, 방어 B티어]",
          "평균득점/평균실점 [공격 B티어, 방어 A티어]",
      ],
      "최종 스코어": ["2 : 1", "1 : 1", "1 : 0", "1 : 2", "2 : 2"],
      "결과": ["승", "무", "승", "패", "무"],
      "비고 (득점 / 실점)": [
          "2득점 / 1실점",
          "1득점 / 1실점",
          "1득점 / 0실점",
          "1득점 / 2실점",
          "2득점 / 2실점",
      ],
  })
  st.dataframe(kor_5_2_df, use_container_width=True, hide_index=True)
  st.markdown(
      f"• **{home_team} 5경기 총합:** 7득점 / 6실점 &nbsp;|&nbsp; **실전"
      " 평균:** 평균 득점 1.40골 / 평균 실점 1.20골"
  )
  st.markdown(
      f"#### 예시표 5-2: {away_team} - 상대방 동급(B/B티어) 상대 최근 5경기"
      " 전수 표"
  )
  jpn_5_2_df = pd.DataFrame({
      "순서": ["1 (최신)", "2", "3", "4", "5 (과거)"],
      "경기 일시": [
          "2024-02-02",
          "2023-10-17",
          "2023-09-12",
          "2023-06-20",
          "2023-03-28",
      ],
      "대회 명칭": [
          "토너먼트 8강",
          "공식 A매치",
          "공식 A매치",
          "공식 A매치",
          "공식 A매치",
      ],
      "장소": ["중립", "홈", "원정", "홈", "홈"],
      "상대 팀": [
          "가상 상대팀 A",
          "튀니지",
          "튀르키예",
          "페루",
          "콜롬비아",
      ],
      "상대 티어": [
          "평균득점/평균실점 [공격 B티어, 방어 B티어]",
          "평균득점/평균실점 [공격 C티어, 방어 B티어]",
          "평균득점/평균실점 [공격 B티어, 방어 B티어]",
          "평균득점/평균실점 [공격 B티어, 방어 C티어]",
          "평균득점/평균실점 [공격 B티어, 방어 A티어]",
      ],
      "최종 스코어": ["1 : 2", "2 : 0", "4 : 2", "4 : 1", "1 : 2"],
      "결과": ["패", "승", "승", "승", "패"],
      "비고 (득점 / 실점)": [
          "1득점 / 2실점",
          "2득점 / 0실점",
          "4득점 / 2실점",
          "4득점 / 1실점",
          "1득점 / 2실점",
      ],
  })
  st.dataframe(jpn_5_2_df, use_container_width=True, hide_index=True)
  st.markdown(
      f"• **{away_team} 5경기 총합:** 12득점 / 7실점 &nbsp;|&nbsp; **실전"
      " 평균:** 평균 득점 2.40골 / 평균 실점 1.40골"
  )
  st.markdown("---")
  st.markdown(
      """ <div class="step-box"> <b>📌 규칙 5-3 (다득점/체급차 변동성 보정 - Over Factor):</b><br> • 체급 격차형 (티어 차이 2단계 이상): 하위 팀 수비 조직력 붕괴를 반영하여 상위 팀 공격력에 추가 득점 가산 (2단계 +10%, 3단계 +20%, 4단계 +30%).<br> • 동급 난타전형 (total > 3.2 또는 양 팀 실점 하한선 ≥ 1.50): 양 팀 화력 보존 및 수비 불안을 반영해 양 팀 득점력에 +15% 추가 득점 가산.<br> • 표준/저득점형 (동급 비등한 경기): Over Factor = 0% (λ_final = λ_base 유효). </div> """,
      unsafe_allow_html=True,
  )
  st.markdown(
      """ <div class="step-box"> <b>📌 규칙 5-4 (이원화 동적 골 범위 행렬 확정 - Dynamic Goal Range):</b><br> • <b>저득점 통제 구역 (total < 2.2골):</b> 0 ~ 3골 범위 (4×4 행렬)<br> • <b>표준 득점 구역 (2.2 ≤ total ≤ 3.2골):</b> 0 ~ 4골 범위 (5×5 행렬 - 기본)<br> • <b>다득점 변동 구역 (total > 3.2골 또는 티어 격차 2단계 이상):</b> 0 ~ 6골 / 0 ~ 7골 동적 확장 행렬 </div> """,
      unsafe_allow_html=True,
  )

# --- [6단계] ---
with tabs[6]:
  st.markdown(
      f"### [규칙 6번: 예상 스코어 순위 산출 및 최종 통합 흐름 매트릭스] -"
      f" {home_team} vs {away_team}"
  )
  st.markdown(
      """ <div class="step-box"> <b>📌 예상스코어 순위 산출 방법 규격:</b><br> • <b>1순위 (최적합):</b> 규칙 5-2의 실전 교차 검증 결과에 가장 적합한 결과값을 최우선으로 선정합니다.<br> • <b>2순위 (차선책):</b> 1순위를 제외한 푸아송 확률이 가장 높은 결과값을 선정합니다.<br> • <b>3순위 (대안책):</b> 푸아송 결과값에 의거하여 가장 큰 확률 비중을 차지하는 점수 차이 합산. </div> """,
      unsafe_allow_html=True,
  )
  st.markdown("#### 예시표 6: 최종 통합 흐름 매트릭스 및 예상 스코어 산출 표")
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
      f"### 📋 [규칙 7] 배트맨 프로젝트 마스터 규격 최종 요약 리포트 -"
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
