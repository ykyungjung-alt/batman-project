import math
import os
import json
import re
import pandas as pd

# ==============================================================================
# 📦 [공통] 데이터 로딩 함수 5종 (app.py 호환)
# ==============================================================================
def load_match_data_for_engine():
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_updated": "안전 모드 (데이터 없음)", "daily_matches": {}}

def load_all_match_details_for_engine():
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

def load_v3_match_details_for_engine():
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

def load_v4_match_details_for_engine():
    v4_file = "match_details_v4.json"
    if os.path.exists(v4_file):
        try:
            with open(v4_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                return file_data.get("leagues", {})
        except Exception:
            pass
    return {}

def load_v5_match_details_for_engine():
    v5_file = "match_details_v5.json"
    if os.path.exists(v5_file):
        try:
            with open(v5_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                return file_data.get("lineup_details", {})
        except Exception:
            pass
    return {}

def load_v5_1_match_details_for_engine():
    v5_1_file = "match_details_v5-1.json"
    if os.path.exists(v5_1_file):
        try:
            with open(v5_1_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                return file_data.get("squad_details", {})
        except Exception:
            pass
    return {}


# 전역 딕셔너리 초기화 셋
engine_data = load_match_data_for_engine()
engine_daily_matches = engine_data.get("daily_matches", {})
all_details_dict = load_all_match_details_for_engine()
v3_details_dict = load_v3_match_details_for_engine()
v4_leagues_dict = load_v4_match_details_for_engine()
v5_details_dict = load_v5_match_details_for_engine()
v5_1_details_dict = load_v5_1_match_details_for_engine()


# ==============================================================================
# 🛠️ [공통 유틸리티] 퍼센트 파싱 및 country.json 로드
# ==============================================================================
def parse_pct(val_str):
    if isinstance(val_str, (int, float)):
        return float(val_str)
    if isinstance(val_str, str):
        cleaned = val_str.replace('%', '').replace('+', '').strip()
        try:
            return float(cleaned)
        except Exception:
            return 0.0
    return 0.0

def load_country_data_for_engine():
    if os.path.exists("country.json"):
        try:
            with open("country.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# ==============================================================================
# 🚀 [마스터 계산 엔진] 단계별 규칙 블록이 밀착 내장된 메인 함수
# ==============================================================================
def compute_match_prediction_master(target_detail, home_name, away_name, league_name=""):
    if not target_detail or not isinstance(target_detail, dict):
        return {"status": False, "msg": "상세 정량 데이터 없음"}

    try:
        meta_details = target_detail.get("meta_details", {})
        rankings_raw = meta_details.get("rankings", [])
        
        # ----------------------------------------------------------------------
        # [0단계 영역] 메타 및 국가 등급 정밀 판정 (안전장치 완비)
        # ----------------------------------------------------------------------
        def resolve_country_and_grade(rank_val, team_val, current_league_name="", country_data=None):
            try:
                if not country_data:
                    country_data = load_country_data_for_engine()
                grades = country_data.get("grades", {})
                rank_str = str(rank_val).strip()
                team_str = str(team_val).strip().lower()
                clean_league = str(current_league_name).strip().replace(" ", "").lower()

                if "k리그" in clean_league or "kor" in rank_str.upper():
                    for c in grades.get("C", []):
                        if c.get("code") == "KOR" or c.get("country_code") == "KOR":
                            return c.get("grade", "C"), parse_pct(c.get("attack_bonus", "+9%")), parse_pct(c.get("defense_bonus", "-9%"))
                    return "C", 9.0, -9.0

                extracted_code = ""
                if rank_str and rank_str != "-":
                    token = re.split(r'[\s\-]+', rank_str)[0].strip().upper()
                    if token and not token.isdigit():
                        extracted_code = token

                if extracted_code:
                    for grade_key, countries in grades.items():
                        if grade_key == "F": continue
                        if isinstance(countries, list):
                            for c in countries:
                                c_code = str(c.get("code", "")).strip().upper()
                                c_ccode = str(c.get("country_code", "")).strip().upper()
                                leagues_list = [str(l).strip().upper() for l in c.get("leagues", [])]
                                if (c_code and c_code == extracted_code) or (c_ccode and c_ccode == extracted_code) or any(extracted_code == l.split()[0] for l in leagues_list if l):
                                    return c.get("grade", "E"), parse_pct(c.get("attack_bonus", "+3%")), parse_pct(c.get("defense_bonus", "-3%"))

                for grade_key, countries in grades.items():
                    if grade_key == "F": continue
                    if isinstance(countries, list):
                        for c in countries:
                            kor_league = str(c.get("league_kor_name", "")).strip().replace(" ", "").lower()
                            c_name = str(c.get("name", "")).strip().lower()
                            if (kor_league and (kor_league == clean_league or f" {kor_league} " in f" {clean_league} ")) or (c_name and (c_name in clean_league or c_name in team_str)):
                                return c.get("grade", "E"), parse_pct(c.get("attack_bonus", "+3%")), parse_pct(c.get("defense_bonus", "-3%"))

                return "F", 0.0, 0.0
            except Exception:
                return "F", 0.0, 0.0

        h_step0_atk, h_step0_def = 0.0, 0.0
        a_step0_atk, a_step0_def = 0.0, 0.0
        clean_home_target = str(home_name).strip().replace(" ", "").lower()
        clean_away_target = str(away_name).strip().replace(" ", "").lower()
        found_home = found_away = False

        if rankings_raw and isinstance(rankings_raw, list):
            for r in rankings_raw:
                if not isinstance(r, dict): continue
                r_team = str(r.get("team", "-"))
                r_code = str(r.get("rank", ""))
                grade, atk_val, def_val = resolve_country_and_grade(r_code, r_team, league_name)
                clean_row_team = r_team.strip().replace(" ", "").lower()
                
                if not found_home and (clean_home_target == clean_row_team or clean_home_target in clean_row_team or clean_row_team in clean_home_target):
                    h_step0_atk, h_step0_def = atk_val, def_val
                    found_home = True
                elif not found_away and (clean_away_target == clean_row_team or clean_away_target in clean_row_team or clean_row_team in clean_home_target):
                    a_step0_atk, a_step0_def = atk_val, def_val
                    found_away = True


# ----------------------------------------------------------------------
        # [규칙 1번 영역] LIFO 10경기, 친선전 보완 및 공수 교차 대칭 특수 룰 완벽 연동
        # ----------------------------------------------------------------------
        recent_form = meta_details.get("recent_form", {})
        raw_h_matches = recent_form.get("home_matches", [])
        raw_a_matches = recent_form.get("away_matches", [])

        # 1. 공식 경기 우선 필터링 및 10경기 확보 함수
        def filter_and_supplement_matches(match_list, max_count=10):
            if not match_list or not isinstance(match_list, list): return []
            official = [m for m in match_list if isinstance(m, dict) and not any(k in str(m.get("league", "")).upper() for k in ["CF", "친선", "FRIENDLY"])]
            friendly = [m for m in match_list if isinstance(m, dict) and m not in official]
            combined = list(official)
            if len(combined) < max_count:
                combined.extend(friendly[:max_count - len(combined)])
            return combined[:max_count]

        h_matches = filter_and_supplement_matches(raw_h_matches, 10)
        a_matches = filter_and_supplement_matches(raw_a_matches, 10)

        h_sum = recent_form.get("home_summary", {})
        a_sum = recent_form.get("away_summary", {})
        
        h_gpg_base = float(target_detail.get("h_gpg", h_sum.get("goals_per_game", 1.2)))
        h_cpg_base = float(target_detail.get("cpg", h_sum.get("conceded_per_game", 1.1)))
        a_gpg_base = float(target_detail.get("a_gpg", a_sum.get("goals_per_game", 1.1)))
        a_cpg_base = float(target_detail.get("a_cpg", a_sum.get("conceded_per_game", 1.2)))

        def get_atk_tier(g):
            if g >= 2.3: return "Tier A", 12.0
            elif g >= 1.7: return "Tier B", 9.0
            elif g >= 1.1: return "Tier C", 6.0
            elif g >= 0.5: return "Tier D", 3.0
            else: return "Tier E", 0.0

        def get_def_tier(c):
            if c < 0.5: return "Tier A", -12.0
            elif c < 0.9: return "Tier B", -9.0
            elif c < 1.3: return "Tier C", -6.0
            elif c < 1.7: return "Tier D", -3.0
            else: return "Tier E", 0.0

        # 2. 공수 교차 대칭 특수 룰 및 E티어 할인 룰을 포함한 정밀 산출 함수
        def compute_rule1_stats_with_cross_tier(matches, tname, base_gpg, base_cpg):
            if not matches or not isinstance(matches, list):
                return base_gpg, base_cpg, "Tier C", "Tier C", 6.0, -6.0

            # Step 1: 1차 예비 산출 (기본 평균으로 초기 체급 판정)
            pre_at, _ = get_atk_tier(base_gpg)
            pre_de, _ = get_def_tier(base_cpg)

            eff_scored = 0.0
            eff_conceded = 0.0

            # Step 2: 확정된 체급 기반 공수 교차 보정치 대칭 적용
            for m in matches:
                if not isinstance(m, dict): continue
                teams = m.get("teams", "-")
                scores = m.get("ft_scores", ["0", "0"])
                try:
                    s1, s2 = int(scores[0]), int(scores[1])
                except Exception:
                    s1 = s2 = 0
                
                sc, cc = s1, s2
                if " vs " in teams:
                    pair = teams.split(" vs ")
                    if len(pair) == 2:
                        if tname in pair[0]: sc, cc = s1, s2
                        elif tname in pair[1]: sc, cc = s2, s1

                mult_gf = 1.0
                mult_ga = 1.0
                tier_info = m.get("opponent_tier_info", "")
                
                if tier_info and "/" in tier_info:
                    try:
                        oa, od = map(float, tier_info.split("/"))
                        at_name, _ = get_atk_tier(oa)  # 상대 공격 티어
                        df_name, _ = get_def_tier(od)  # 상대 방어 티어

                        # 공격 대칭 교차 룰
                        if pre_at == "Tier A" and (df_name == "Tier E" or od >= 2.0):
                            mult_gf = 0.5
                        elif pre_at == "Tier E" and (df_name == "Tier A" or od < 0.5):
                            mult_gf = 1.5

                        # 방어 대칭 교차 룰
                        if pre_de == "Tier A" and (at_name == "Tier E" or oa < 0.5):
                            mult_ga = 1.5
                        elif pre_de == "Tier E" and (at_name == "Tier A" or oa >= 2.3):
                            mult_ga = 0.5
                    except Exception:
                        pass

                eff_scored += (sc * mult_gf)
                eff_conceded += (cc * mult_ga)

            cnt = len(matches)
            gpg = round(eff_scored / cnt, 2) if cnt > 0 else base_gpg
            cpg = round(eff_conceded / cnt, 2) if cnt > 0 else base_cpg

            final_at, at_val = get_atk_tier(gpg)
            final_de, def_val = get_def_tier(cpg)
            return gpg, cpg, final_at, final_de, at_val, def_val

        h_base_g, h_base_c, base_h_at, base_h_de, h_r1_atk, h_r1_def = compute_rule1_stats_with_cross_tier(h_matches, home_name, h_gpg_base, h_cpg_base)
        a_base_g, a_base_c, base_a_at, base_a_de, a_r1_atk, a_r1_def = compute_rule1_stats_with_cross_tier(a_matches, away_name, a_gpg_base, a_cpg_base)
        
        # 구장 Shift 룰에서 참조할 수 있도록 하위 변수 동기화
        h_is_triggered = (base_h_at == "Tier A" or base_h_de == "Tier E")
        a_is_triggered = (base_a_at == "Tier A" or base_a_de == "Tier E")
        
        
# ----------------------------------------------------------------------
        # [규칙 2번 영역] 구장별(Stadium Form) Shift 보정 연산 (시계열 정렬 및 2차 교차 보정 완벽 연동)
        # ----------------------------------------------------------------------
        head_info = target_detail.get("head_info", {})
        venue_val = str(head_info.get("stadium", "")) or str(head_info.get("venue", ""))
        home_stadium_val = str(head_info.get("home_stadium", ""))
        
        is_neutral_venue = False
        if venue_val and home_stadium_val and home_stadium_val != "-":
            if venue_val.strip().lower() != home_stadium_val.strip().lower():
                is_neutral_venue = True

        stadium_form = target_detail.get("meta_details", {}).get("stadium_form", {"home_matches": [], "away_matches": []})

        # 1. 시계열 최신순 정렬 기능이 포함된 공식 경기 우선 필터링 함수
        def filter_and_supplement_matches_with_sort(match_list, max_count=10):
            if not match_list or not isinstance(match_list, list):
                return []
            official_matches = []
            friendly_matches = []
            for m in match_list:
                if not isinstance(m, dict): continue
                league_str = str(m.get("league", "")).upper()
                if "CF" in league_str or "친선" in league_str or "FRIENDLY" in league_str:
                    friendly_matches.append(m)
                else:
                    official_matches.append(m)
            
            combined = list(official_matches)
            if len(combined) < max_count:
                needed = max_count - len(combined)
                combined.extend(friendly_matches[:needed])
            
            selected = combined[:max_count]
            # 💡 [시계열 정렬 보장] 경기 일시 기준 최신순 정렬
            try:
                selected.sort(key=lambda x: str(x.get("match_time", "")), reverse=True)
            except Exception:
                pass
            return selected

        # 2. 홈팀 전적 추출 (중립 경기일 경우 원정/중립 성격 경기 정밀 분기)
        s_home_matches = []
        if is_neutral_venue:
            recent_all_pool = []
            if 'h_matches' in locals() and h_matches:
                recent_all_pool = h_matches
            elif stadium_form and "recent_matches" in stadium_form:
                recent_all_pool = stadium_form.get("recent_matches", [])

            neutral_home_away_matches = []
            for m in recent_all_pool:
                if not isinstance(m, dict): continue
                teams_str = str(m.get("teams", ""))
                if " vs " in teams_str:
                    t_parts = [p.strip() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2 and home_name not in t_parts[0]:
                        neutral_home_away_matches.append(m)
                elif m.get("location") == "원정" or m.get("venue_type") == "away":
                    neutral_home_away_matches.append(m)
            
            if not neutral_home_away_matches:
                neutral_home_away_matches = stadium_form.get("away_matches", [])

            s_home_matches = filter_and_supplement_matches_with_sort(neutral_home_away_matches, 10)
        else:
            raw_sh = stadium_form.get("home_matches", [])
            if not raw_sh and 'h_matches' in locals():
                raw_sh = h_matches
            s_home_matches = filter_and_supplement_matches_with_sort(raw_sh, 10)

        # 3. 원정팀 전적 추출 (공식전 우선 10경기 확보 및 최신순 정렬)
        raw_sa = stadium_form.get("away_matches", [])
        if not raw_sa and 'a_matches' in locals():
            raw_sa = a_matches
        s_away_matches = filter_and_supplement_matches_with_sort(raw_sa, 10)

        if not s_home_matches and 'h_matches' in locals(): 
            s_home_matches = filter_and_supplement_matches_with_sort(h_matches, 10)
        if not s_away_matches and 'a_matches' in locals(): 
            s_away_matches = filter_and_supplement_matches_with_sort(a_matches, 10)

        # 4. 구장별 전적 기본 베이스 득실 산출 헬퍼
        def get_base_gpg_cpg(matches, tname):
            if not matches: return 0.0, 0.0
            s_sum, c_sum = 0.0, 0.0
            for m in matches:
                if not isinstance(m, dict): continue
                scores = m.get("ft_scores", ["0", "0"])
                try: s1, s2 = int(scores[0]), int(scores[1])
                except Exception: s1 = s2 = 0
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

        s_h_gpg_base = float(target_detail.get("s_h_gpg", get_base_gpg_cpg(s_home_matches, home_name)[0]))
        s_h_cpg_base = float(target_detail.get("s_h_cpg", get_base_gpg_cpg(s_home_matches, home_name)[1]))
        s_a_gpg_base = float(target_detail.get("s_a_gpg", get_base_gpg_cpg(s_away_matches, away_name)[0]))
        s_a_cpg_base = float(target_detail.get("s_a_cpg", get_base_gpg_cpg(s_away_matches, away_name)[1]))

        # 5. 구장별 1차 예비 체급 산출 및 2차 교차 보정 체계 적용
        def compute_stadium_stats_with_cross_tier(matches, tname, base_gpg, base_cpg):
            if not matches or not isinstance(matches, list):
                return base_gpg, base_cpg, "Tier C", "Tier C"
            
            pre_at, _ = get_atk_tier(base_gpg)
            pre_de, _ = get_def_tier(base_cpg)

            eff_scored = 0.0
            eff_conceded = 0.0

            for m in matches:
                if not isinstance(m, dict): continue
                teams = m.get("teams", "-")
                scores = m.get("ft_scores", ["0", "0"])
                try: s1, s2 = int(scores[0]), int(scores[1])
                except Exception: s1 = s2 = 0
                
                sc, cc = s1, s2
                if " vs " in teams:
                    pair = teams.split(" vs ")
                    if len(pair) == 2:
                        if tname in pair[0]: sc, cc = s1, s2
                        elif tname in pair[1]: sc, cc = s2, s1

                mult_gf = 1.0
                mult_ga = 1.0
                tier_info = m.get("opponent_tier_info", "")
                
                if tier_info and "/" in tier_info:
                    try:
                        oa, od = map(float, tier_info.split("/"))
                        at_name, _ = get_atk_tier(oa)
                        df_name, _ = get_def_tier(od)

                        if pre_at == "Tier A" and (df_name == "Tier E" or od >= 2.0): mult_gf = 0.5
                        elif pre_at == "Tier E" and (df_name == "Tier A" or od < 0.5): mult_gf = 1.5

                        if pre_de == "Tier A" and (at_name == "Tier E" or oa < 0.5): mult_ga = 1.5
                        elif pre_de == "Tier E" and (at_name == "Tier A" or oa >= 2.3): mult_ga = 0.5
                    except Exception:
                        pass

                eff_scored += (sc * mult_gf)
                eff_conceded += (cc * mult_ga)

            cnt = len(matches)
            gpg = round(eff_scored / cnt, 2) if cnt > 0 else base_gpg
            cpg = round(eff_conceded / cnt, 2) if cnt > 0 else base_cpg
            final_at, _ = get_atk_tier(gpg)
            final_de, _ = get_def_tier(cpg)
            return gpg, cpg, final_at, final_de

        s_h_g, s_h_c, s_h_at, s_h_de = compute_stadium_stats_with_cross_tier(s_home_matches, home_name, s_h_gpg_base, s_h_cpg_base)
        s_a_g, s_a_c, s_a_at, s_a_de = compute_stadium_stats_with_cross_tier(s_away_matches, away_name, s_a_gpg_base, s_a_cpg_base)

        tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
        def calc_shift(base_t, stadium_t, is_atk=True):
            b_v = tier_ranks.get(base_t, 3)
            s_v = tier_ranks.get(stadium_t, 3)
            if is_atk:
                if s_v > b_v: return 15.0
                elif s_v < b_v: return -15.0
                return 0.0
            else:
                if s_v < b_v: return 15.0
                elif s_v > b_v: return -15.0
                return 0.0

        h_r2_atk = calc_shift(base_h_at, s_h_at, True)
        h_r2_def = calc_shift(base_h_de, s_h_de, False)
        a_r2_atk = calc_shift(base_a_at, s_a_at, True)
        a_r2_def = calc_shift(base_a_de, s_a_de, False)
   
        
        # [규칙 3번] 선수 전력 누수(3-1) 및 일정 중요도 및 피로 
        
# ----------------------------------------------------------------------
        # [규칙 3-1 영역] 선수 전력 누수 및 결장자 보정 연산 (app.py 3-1 규격 100% 동기화)
        # ----------------------------------------------------------------------
        target_code = str(target_detail.get("match_code", "")).strip()

        def compute_squad_changes_engine(match_code_str, home_name_str, away_name_str):
            h_tot_atk, h_tot_def = 0.0, 0.0
            a_tot_atk, a_tot_def = 0.0, 0.0
            
            try:
                v5_lineup_dict = v5_details_dict.get("lineup_details", v5_details_dict) if 'v5_details_dict' in globals() else {}
                v5_1_squad_dict = v5_1_details_dict.get("squad_details", v5_1_details_dict) if 'v5_1_details_dict' in globals() else {}
                
                clean_home = str(home_name_str).strip().replace(" ", "").lower()
                clean_away = str(away_name_str).strip().replace(" ", "").lower()
                
                # 1. V5 결장자 데이터 매칭
                v5_match_data = {}
                for k, v in v5_lineup_dict.items():
                    if not isinstance(v, dict): continue
                    v_code = str(v.get("match_code", k)).strip()
                    v_h = str(v.get("home", "")).strip().replace(" ", "").lower()
                    v_a = str(v.get("away", "")).strip().replace(" ", "").lower()
                    if v_code == match_code_str or (clean_home in v_h and clean_away in v_a):
                        v5_match_data = v
                        break
                
                raw_home_absentees = []
                raw_away_absentees = []
                if v5_match_data:
                    data_home_name = str(v5_match_data.get("home", "")).strip().replace(" ", "").lower()
                    if clean_home in data_home_name or data_home_name in clean_home:
                        h_raw_list = v5_match_data.get("home_absentees", [])
                        a_raw_list = v5_match_data.get("away_absentees", [])
                    else:
                        h_raw_list = v5_match_data.get("away_absentees", [])
                        a_raw_list = v5_match_data.get("home_absentees", [])
                    
                    raw_home_absentees = [p for p in h_raw_list if isinstance(p, dict) and str(p.get("status", "")).strip() in ["결장", "부상", "징계", "누수", "출전의심/기타"] and str(p.get("name", "")).strip()]
                    raw_away_absentees = [p for p in a_raw_list if isinstance(p, dict) and str(p.get("status", "")).strip() in ["결장", "부상", "징계", "누수", "출전의심/기타"] and str(p.get("name", "")).strip()]

                # 2. V5-1 스쿼드 풀 매칭
                v5_1_match_data = {}
                for k, v in v5_1_squad_dict.items():
                    if not isinstance(v, dict): continue
                    v_code = str(v.get("match_code", k)).strip()
                    v_h = str(v.get("home", "")).strip().replace(" ", "").lower()
                    v_a = str(v.get("away", "")).strip().replace(" ", "").lower()
                    if v_code == match_code_str or (clean_home in v_h and clean_away in v_a):
                        v5_1_match_data = v
                        break
                
                home_squad_pool = []
                away_squad_pool = []
                if v5_1_match_data:
                    data_squad_home = str(v5_1_match_data.get("home", "")).strip().replace(" ", "").lower()
                    if clean_home in data_squad_home or data_squad_home in clean_home:
                        home_squad_pool = v5_1_match_data.get("home_squad", [])
                        away_squad_pool = v5_1_match_data.get("away_squad", [])
                    else:
                        home_squad_pool = v5_1_match_data.get("away_squad", [])
                        away_squad_pool = v5_1_match_data.get("home_squad", [])

                # 3. 개별 팀 보정치 산출 내부 헬퍼 함수 (app.py 3-1 규격 동일 적용)
                def calc_team_absentee_weights(abs_list, squad_list):
                    if not abs_list:
                        return 0.0, 0.0
                    
                    squad_pos_map = {}
                    if squad_list and isinstance(squad_list, list):
                        for p in squad_list:
                            if not isinstance(p, dict): continue
                            p_name = str(p.get("name", "")).strip()
                            p_pos = str(p.get("position", "")).strip()
                            if p_name and p_pos:
                                squad_pos_map[p_name] = p_pos
                                squad_pos_map[p_name.replace(" ", "")] = p_pos
                    
                    t_atk, t_def = 0.0, 0.0
                    for item in abs_list:
                        if not isinstance(item, dict): continue
                        p_name = str(item.get("name", "-")).strip()
                        p_pos = squad_pos_map.get(p_name, squad_pos_map.get(p_name.replace(" ", ""), ""))
                        if not p_pos or p_pos == "-":
                            p_pos = "미드필더"
                        
                        p_type = str(item.get("status", "결장")).strip()
                        stats_dict = item.get("stats", {})
                        raw_grade = str(stats_dict.get("grade", item.get("grade", "C"))).strip().upper()
                        
                        if "A" in raw_grade: rate = 12.0
                        elif "B" in raw_grade: rate = 8.0
                        elif "C" in raw_grade: rate = 4.0
                        else: rate = 0.0
                        
                        is_attacker = any(k in p_pos for k in ["공격수", "FW", "MF"])
                        is_defender = any(k in p_pos for k in ["수비수", "골키퍼", "DF", "GK"])
                        
                        if p_type in ["결장", "부상", "징계", "누수", "출전의심/기타"]:
                            if is_attacker:
                                atk_v, def_v = -rate, rate / 2.0
                            elif is_defender:
                                atk_v, def_v = -rate / 2.0, rate
                            else:
                                atk_v, def_v = -rate, rate / 2.0
                        else:
                            if is_attacker:
                                atk_v, def_v = rate, -rate / 2.0
                            elif is_defender:
                                atk_v, def_v = rate / 2.0, -rate
                            else:
                                atk_v, def_v = rate, -rate / 2.0
                        
                        t_atk += atk_v
                        t_def += def_v
                    return t_atk, t_def

                h_tot_atk, h_tot_def = calc_team_absentee_weights(raw_home_absentees, home_squad_pool)
                a_tot_atk, a_tot_def = calc_team_absentee_weights(raw_away_absentees, away_squad_pool)

            except Exception as e:
                print(f"[Engine 3-1 Error Warning]: {e}")
                
            return h_tot_atk, h_tot_def, a_tot_atk, a_tot_def

        # 엔진 메인 흐름에 3-1 결과 주입
        h_r31_atk, h_r31_def, a_r31_atk, a_r31_def = compute_squad_changes_engine(target_code, home_name, away_name)
        
        
        
        
# ----------------------------------------------------------------------
        # [규칙 3-2 영역] v4 리그 순위표 연동 중요도 판정 및 타임라인 이동 피로도 정밀 산출
        # ----------------------------------------------------------------------
        def get_team_standing_info_engine(target_team_name):
            target_clean = str(target_team_name).strip().replace(" ", "")
            matched_standings = []
            v4_dict = v4_leagues_dict.get("leagues", v4_leagues_dict) if 'v4_leagues_dict' in globals() else {}
            for l_id, l_data in v4_dict.items():
                if not isinstance(l_data, dict): continue
                standings = l_data.get("standings", [])
                league_name = l_data.get("league_name", "해외 리그")
                for row in standings:
                    if not isinstance(row, dict): continue
                    row_team = str(row.get("team", "")).strip().replace(" ", "")
                    if target_clean in row_team or row_team in target_clean:
                        raw_label = str(row.get("tag_label", "일반"))
                        matched_standings.append({
                            "league_name": league_name,
                            "rank": str(row.get("rank", "-")),
                            "team": row.get("team", target_team_name),
                            "tag_label": raw_label
                        })
            return matched_standings

        def determine_match_importance_engine(standing_info_list, league_raw_name):
            league_str = str(league_raw_name)
            if any(k in league_str for k in ["친선", "CF", "탈락", "탈락확정", "강등확정"]):
                return -10.0, 10.0
            if not standing_info_list:
                return 5.0, -5.0
            
            for standing_info in standing_info_list:
                l_name = str(standing_info.get("league_name", ""))
                if l_name in league_str or league_str in l_name or any(k in league_str and k in l_name for k in ["챔피언스", "유로파", "컨퍼런스", "분데스리가", "프리미어", "라리가", "세리에", "리그"]):
                    label = str(standing_info.get("tag_label", ""))
                    if any(k in label for k in ["탈락", "탈락확정", "강등확정"]):
                        return -10.0, 10.0
                    if any(k in label for k in ["진출권", "플레이오프", "승격", "우승", "qualifying", "play-offs", "Playoff"]) or any(k in league_str for k in ["챔피언스", "유로파", "결승", "컵", "ACL", "CL"]):
                        return 15.0, -15.0

            return 5.0, -5.0

        home_standings_list = get_team_standing_info_engine(home_name)
        away_standings_list = get_team_standing_info_engine(away_name)
        tournament_display = str(target_detail.get("tournament", "리그 경기"))

        h_imp_atk, h_imp_def = determine_match_importance_engine(home_standings_list, tournament_display)
        a_imp_atk, a_imp_def = determine_match_importance_engine(away_standings_list, tournament_display)

        # 타임라인 기반 피로도 단계 정밀 산출 (fixtures 데이터 연동)
        fixtures_info = meta_details.get("fixtures", {})
        raw_home_fixes = list(fixtures_info.get("home", []))
        raw_away_fixes = list(fixtures_info.get("away", []))
        match_date_str = str(target_detail.get("match_time", "2026-06-01"))

        def parse_fatigue_stage_strictly(fix_list, recent_list, is_home_team):
            base_dt = datetime.now()
            try:
                base_dt = datetime.strptime(match_date_str.split(" ")[0].replace(".", "-").replace("/", "-")[:10], "%Y-%m-%d")
            except Exception:
                pass

            combined_pool = []
            seen = set()
            for f in list(fix_list) + list(recent_list):
                if not isinstance(f, dict): continue
                uid = f"{f.get('match_time', '')}_{f.get('teams', '')}"
                if uid not in seen:
                    combined_pool.append(f)
                    seen.add(uid)

            past_arr = []
            for f in combined_pool:
                m_time_str = str(f.get("match_time", ""))
                try:
                    c_dt = datetime.strptime(m_time_str.split(" ")[0].replace(".", "-").replace("/", "-")[:10], "%Y-%m-%d")
                    d_diff = (c_dt - base_dt).days
                    if d_diff < 0:
                        past_arr.append((d_diff, f))
                except Exception:
                    continue

            chrono_past = sorted(past_arr, key=lambda x: x[0])
            has_4d_away = False
            has_7d_away = False

            for d_d, f_item in chrono_past:
                abs_d = abs(d_d)
                teams_raw = str(f_item.get("teams", ""))
                # 원정 여부 판정 (팀명이 원정에 위치하거나 로케이션이 원정인 경우)
                is_away_match = ("원정" in str(f_item.get("location", "")) or "away" in str(f_item.get("venue_type", "")))
                
                if 1 <= abs_d <= 4 and is_away_match:
                    has_4d_away = True
                elif 4 < abs_d <= 7 and is_away_match:
                    has_7d_away = True

            acc = 0
            if has_4d_away: acc += 1
            if has_7d_away: acc += 1

            my_loc = "홈" if is_home_team else "원정"
            if acc > 0 and my_loc == "원정":
                return acc + 1
            elif acc > 0:
                return acc
            else:
                return 1 if my_loc == "원정" else 0

        h_fatigue_stage = parse_fatigue_stage_strictly(raw_home_fixes, h_matches, True)
        a_fatigue_stage = parse_fatigue_stage_strictly(raw_away_fixes, a_matches, False)

        h_r32_atk = (-5.0 * h_fatigue_stage)
        h_r32_def = (5.0 * h_fatigue_stage)
        a_r32_atk = (-5.0 * a_fatigue_stage)
        a_r32_def = (5.0 * a_fatigue_stage)

        # 규칙 3번 최종 통합 합산 (3-1 누수 + 3-2 중요도 + 피로도)
        h_r3_tot_atk = h_r31_atk + h_imp_atk + h_r32_atk
        h_r3_tot_def = h_r31_def + h_imp_def + h_r32_def
        a_r3_tot_atk = a_r31_atk + a_imp_atk + a_r32_atk
        a_r3_tot_def = a_r31_def + a_imp_def + a_r32_def

# ----------------------------------------------------------------------
        # [규칙 4번 영역] 맞대결 H2H 상성 및 단방향 10% 룰 (app.py 4단계 100% 동기화)
        # ----------------------------------------------------------------------
        h2h_info = meta_details.get("h2h", {})
        h2h_matches = h2h_info.get("matches", [])
        
        home_wins = 0
        away_wins = 0
        total_games = len(h2h_matches) if isinstance(h2h_matches, list) else 0

        if total_games > 0 and isinstance(h2h_matches, list):
            for m in h2h_matches:
                if not isinstance(m, dict): continue
                row_cols = m.get("row_data", [])
                if len(row_cols) >= 4:
                    h_team_name = str(row_cols[1]).strip()
                    score_str = str(row_cols[2]).strip()
                    try:
                        scores = score_str.replace("：", "-").split("-")
                        h_score = int(scores[0].strip())
                        a_score = int(scores[1].strip())
                        
                        # 홈팀 기준으로 승패 판정
                        if h_team_name == home_name:
                            if h_score > a_score:
                                home_wins += 1
                            elif h_score < a_score:
                                away_wins += 1
                        else:
                            if h_score > a_score:
                                away_wins += 1
                            elif h_score < a_score:
                                home_wins += 1
                    except Exception:
                        pass

        home_win_rate = (home_wins / total_games * 100) if total_games > 0 else 0.0
        away_win_rate = (away_wins / total_games * 100) if total_games > 0 else 0.0

        h_r4_atk, h_r4_def = 0.0, 0.0
        a_r4_atk, a_r4_def = 0.0, 0.0

        # 표본 5경기 이상 및 승률 50% 이상 우세 팀에만 단방향 보정(+10% / -10%) 부여
        if total_games >= 5:
            if home_win_rate >= 50.0:
                h_r4_atk, h_r4_def = 10.0, -10.0
            elif away_win_rate >= 50.0:
                a_r4_atk, a_r4_def = 10.0, -10.0

        # ==============================================================================
        # 🎯 [0~5단계 통합 누적 합산 규격] 공격력 및 방어력 보정치 전 단계 완벽 결속 (5-1 표 연동)
        # ==============================================================================
        h_tot_atk_pct = h_step0_atk + h_r1_atk + h_r2_atk + h_r3_tot_atk + h_r4_atk
        h_tot_def_pct = h_step0_def + h_r1_def + h_r2_def + h_r3_tot_def + h_r4_def  # 방어력 누락분 완전 결속

        a_tot_atk_pct = a_step0_atk + a_r1_atk + a_r2_atk + a_r3_tot_atk + a_r4_atk
        a_tot_def_pct = a_step0_def + a_r1_def + a_r2_def + a_r3_tot_def + a_r4_def  # 방어력 누락분 완전 결속

        # [규칙 5번 - 5-1 산출] 최종 보정 및 1차 기본 기대 득실점 산출
        h_max_g = h_base_g * (1 + h_tot_atk_pct / 100.0)
        h_min_c = h_base_c * (1 + h_tot_def_pct / 100.0)
        a_max_g = a_base_g * (1 + a_tot_atk_pct / 100.0)
        a_min_c = a_base_c * (1 + a_tot_def_pct / 100.0)

        h_final_exp_g = max(0.2, (h_max_g + (2.0 - a_min_c)) / 2.0)
        h_final_exp_c = max(0.2, (h_min_c + (2.0 - a_max_g)) / 2.0)
        a_final_exp_g = max(0.2, (a_max_g + (2.0 - h_min_c)) / 2.0)
        a_final_exp_c = max(0.2, (a_min_c + (2.0 - h_max_g)) / 2.0)


        # ==============================================================================
        # 📊 [규칙 5번 - 5-2 영역] 동급 티어 실전 7경기 교차 검증 및 실전 평균 득실 추출 규격
        # ==============================================================================
        
        # 1. 2단계 체급 및 상대 연동 체급 확정
        h_opp_at = s_a_at if 's_a_at' in locals() else "Tier C"
        h_opp_de = s_a_de if 's_a_de' in locals() else "Tier C"
        a_opp_at = s_h_at if 's_h_at' in locals() else "Tier C"
        a_opp_de = s_h_de if 's_h_de' in locals() else "Tier C"

        home_raw_pool = []
        away_raw_pool = []
        stadium_form_block = target_detail.get("meta_details", {}).get("stadium_form", {})
        if stadium_form_block:
            home_raw_pool = stadium_form_block.get("home_matches", [])
            away_raw_pool = stadium_form_block.get("away_matches", [])
        if not home_raw_pool:
            home_raw_pool = s_home_matches if 's_home_matches' in locals() and s_home_matches else (h_matches if 'h_matches' in locals() else [])
        if not away_raw_pool:
            away_raw_pool = s_away_matches if 's_away_matches' in locals() and s_away_matches else (a_matches if 'a_matches' in locals() else [])

        # 2. 친선전 제외 및 동급 티어 매칭 7경기 필터링 함수 (시계열 최신순 정렬 포함)
        def get_real_matches_without_friendlies(match_list):
            if not match_list or not isinstance(match_list, list): return []
            valid = []
            for fix in match_list:
                if not isinstance(fix, dict): continue
                league_raw = str(fix.get("league", "")).lower()
                if any(k in league_raw for k in ["친선", "friendly", "int cf", "club friendlies", "friendlies"]):
                    continue
                score_str = str(fix.get("score", "") or fix.get("result", ""))
                scores_arr = fix.get("ft_scores", [])
                if not score_str and (scores_arr and len(scores_arr) >= 2):
                    score_str = f"{scores_arr[0]} : {scores_arr[1]}"
                if score_str or scores_arr:
                    valid.append(fix)
            return valid

        def filter_matched_tier_games_engine(match_list, target_at_name, target_de_name):
            valid_pool = get_real_matches_without_friendlies(match_list)
            if not valid_pool: return []

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
                    except: pass
                op_at_name = atk_tier_nm(oa) if 'atk_tier_nm' in globals() else "Tier C"
                op_de_name = def_tier_nm(od) if 'def_tier_nm' in globals() else "Tier C"
                
                op_at_val = tier_score_map.get(op_at_name, 3)
                op_de_val = tier_score_map.get(op_de_name, 3)

                diff_at = abs(t_at_val - op_at_val)
                diff_de = abs(t_de_val - op_de_val)
                match_score = diff_at + diff_de
                scored_pool.append((match_score, m))

            scored_pool.sort(key=lambda x: x[0])
            sorted_matches = [item[1] for item in scored_pool[:7]]
            try:
                sorted_matches.sort(key=lambda x: str(x.get("match_time", "")), reverse=True)
            except: pass
            return sorted_matches

        home_matched_7 = filter_matched_tier_games_engine(home_raw_pool, h_opp_at, h_opp_de)
        away_matched_7 = filter_matched_tier_games_engine(away_raw_pool, a_opp_at, a_opp_de)

        # 3. 5-2 실전 득실 평균 산출 헬퍼 함수
        def compute_52_real_avg(match_list, team_label, my_at, my_de):
            if not match_list: return 0.0, 0.0
            tot_gf = tot_ga = 0.0
            cnt = len(match_list)
            for m in match_list:
                if not isinstance(m, dict): continue
                scores_arr = m.get("ft_scores", [])
                m_score = str(m.get("score", "") or m.get("result", "0 : 0"))
                if scores_arr and len(scores_arr) >= 2:
                    m_score = f"{scores_arr[0]} : {scores_arr[1]}"
                
                teams_str = str(m.get("teams", ""))
                is_team_home = True
                if " vs " in teams_str:
                    t_parts = [p.strip() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2 and team_label.strip() in t_parts[1] and team_label.strip() not in t_parts[0]:
                        is_team_home = False

                raw_s1 = raw_s2 = 0
                try:
                    parts = m_score.replace("-", ":").split(":")
                    if len(parts) >= 2:
                        raw_s1 = int(parts[0].strip())
                        raw_s2 = int(parts[1].strip())
                except: pass

                gf = raw_s2 if (not is_team_home and " vs " in teams_str) else raw_s1
                ga = raw_s1 if (not is_team_home and " vs " in teams_str) else raw_s2

                # 5-2 공수 대칭 교차 보정 독립 적용
                tier_info = m.get("opponent_tier_info", "")
                oa, od = 1.3, 1.2
                if tier_info and "/" in tier_info:
                    try:
                        oa, od = map(float, tier_info.split("/"))
                    except: pass
                at_name = atk_tier_nm(oa) if 'atk_tier_nm' in globals() else "Tier C"
                df_name = def_tier_nm(od) if 'def_tier_nm' in globals() else "Tier C"

                mult_gf = mult_ga = 1.0
                if my_at == "Tier A" and df_name == "Tier E": mult_gf = 0.5
                elif my_at == "Tier E" and df_name == "Tier A": mult_gf = 1.5
                if my_de == "Tier A" and at_name == "Tier E": mult_ga = 1.5
                elif my_de == "Tier E" and at_name == "Tier A": mult_ga = 0.5

                tot_gf += (gf * mult_gf)
                tot_ga += (ga * mult_ga)

            return (tot_gf / cnt if cnt > 0 else 0.0), (tot_ga / cnt if cnt > 0 else 0.0)

        # 최종 실전 평균 득실 산출 (5-2 표 핵심 결과물)
        h_agf, h_aga = compute_52_real_avg(home_matched_7, home_name, h_base_g, h_base_c)
        a_agf, a_aga = compute_52_real_avg(away_matched_7, away_name, a_base_g, a_base_c)
        
        # 4. 안전 방어 수용
        h_agf = float(target_detail.get("h_agf", h_agf if h_agf > 0 else h_base_g))
        h_aga = float(target_detail.get("h_aga", h_aga if h_aga > 0 else h_base_c))
        a_agf = float(target_detail.get("a_agf", a_agf if a_agf > 0 else a_base_g))
        a_aga = float(target_detail.get("a_aga", a_aga if a_aga > 0 else a_base_c))
# ==============================================================================
        # 📈 [규칙 5-3 영역] 다득점/체급차 변동성 보정 (Over Factor) 및 최종 람다 결합
        # ==============================================================================
        
        # 1. 1단계/2단계 체급 안전 참조 (base_h_at 또는 h_current_at 호환 방어)
        h_at_ref = base_h_at if 'base_h_at' in locals() else (h_current_at if 'h_current_at' in locals() else "Tier C")
        a_at_ref = base_a_at if 'base_a_at' in locals() else (a_current_at if 'a_current_at' in locals() else "Tier C")

        tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
        h_tier_val = tier_ranks.get(h_at_ref, 3)
        a_tier_val = tier_ranks.get(a_at_ref, 3)
        tier_diff = abs(h_tier_val - a_tier_val)

        # 2. 오버 팩터 계수 초기화
        h_over_factor = 0.0
        a_over_factor = 0.0

        # 3. 체급 격차형 및 동급 난타전형 조건 판정
        if tier_diff >= 2:
            add_rate = 0.10 + (tier_diff - 2) * 0.10
            if h_tier_val > a_tier_val: 
                h_over_factor = add_rate
            else: 
                a_over_factor = add_rate
        elif (h_final_exp_g + a_final_exp_g > 3.2) or (h_final_exp_c >= 1.50 or a_final_exp_c >= 1.50):
            h_over_factor = 0.15
            a_over_factor = 0.15

        # 4. 💡 최종 람다(Expected Goals) 산정 시 [5-1/5-2 1차 기대치+실전 평균]과 [5-3 오버 팩터] 정밀 결합 연동
        h_final = max(0.2, ((h_final_exp_g * (1 + h_over_factor)) + h_agf) / 2.0)
        a_final = max(0.2, ((a_final_exp_g * (1 + a_over_factor)) + a_agf) / 2.0)
        total_expected_goals = h_final + a_final

        # ==============================================================================
        # 📊 [5-4] 이원화 동적 골 범위 행렬 확정 및 구획 분류 (엔진 백엔드 연동)
        # ==============================================================================
        if total_expected_goals < 2.2:
            poisson_zone_name = "저득점 통제 구역 (total < 2.2)"
            matrix_range = "0 ~ 3골 범위 (4×4 행렬)"
        elif total_expected_goals <= 3.2 and tier_diff < 2:
            poisson_zone_name = "표준 득점 구역 (2.2 ~ 3.2)"
            matrix_range = "0 ~ 4골 범위 (5×5 행렬 - 기본)"
        else:
            poisson_zone_name = "다득점 변동 구역 (total > 3.2 또는 격차 2단계 이상)"
            matrix_range = "0 ~ 6골 / 0 ~ 7골 동적 확장 행렬"
        
# --------------------------------------------------------------------------
        # 🧮 [규칙 6] 푸아송 분포 및 승무패 확률 / 예측 순위 정밀 연산 블록 (최종 완벽 동기화)
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

        safe_h_final = float(h_final) if 'h_final' in locals() and h_final is not None else 1.0
        safe_a_final = float(a_final) if 'a_final' in locals() and a_final is not None else 1.0

        total_exp_goals = safe_h_final + safe_a_final

        # 동적 행렬 범위 및 푸아송 구역 명칭 확정
        if total_exp_goals < 2.2:
            matrix_max_k = 3
            poisson_zone_name = "저득점 통제 구역 (total < 2.2)"
            matrix_range = "0 ~ 3 골 범위 (4×4 행렬)"
        elif total_exp_goals <= 3.2 and (tier_diff if 'tier_diff' in locals() else 0) < 2:
            matrix_max_k = 4
            poisson_zone_name = "표준 득점 구역 (2.2 ~ 3.2)"
            matrix_range = "0 ~ 4 골 범위 (5×5 행렬 - 기본)"
        else:
            matrix_max_k = 6
            poisson_zone_name = "다득점 변동 구역 (total > 3.2 또는 격차 2단계 이상)"
            matrix_range = "0 ~ 6 골 / 0 ~ 7골 동적 확장 행렬"

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

        # 💡 [핵심] 5-2 표의 실전 평균 득실 값(h_agf, a_agf)을 명확하게 타겟으로 설정
        h_target_52 = float(h_agf) if 'h_agf' in locals() and h_agf is not None else 1.0
        a_target_52 = float(a_agf) if 'a_agf' in locals() and a_agf is not None else 1.0

        # [1순위] 규칙 5-2 결과에 가장 적합한 결과값 최우선 선정 (피트니스 점수 공식 정밀 적용)
        scored_candidates = []
        for item in score_probs:
            hg, ag, prob = item["home_score"], item["away_score"], item["prob"]
            v52_distance = abs(hg - h_target_52) + abs(ag - a_target_52)
            fitness_score = v52_distance - (prob * 3.0)
            scored_candidates.append({"home_score": hg, "away_score": ag, "prob": prob, "fitness": fitness_score})

        sorted_by_fitness = sorted(scored_candidates, key=lambda x: x["fitness"])
        best_match_52 = sorted_by_fitness[0]

        # [2순위] 1순위를 제외한 푸아송 확률 제일 높은 단일 스코어 선정
        sorted_by_prob = sorted(score_probs, key=lambda x: x["prob"], reverse=True)
        second_match = None
        for s in sorted_by_prob:
            if not (s["home_score"] == best_match_52["home_score"] and s["away_score"] == best_match_52["away_score"]):
                second_match = s
                break
        if not second_match:
            second_match = sorted_by_prob[1] if len(sorted_by_prob) > 1 else best_match_52

        # [3순위] 각 점수 차이별 확률 합산 후 가장 많이 차지한 점수 차이 구도 및 상세 산출근거 생성
        diff_probs = {}
        for item in score_probs:
            diff = item["home_score"] - item["away_score"]
            diff_probs[diff] = diff_probs.get(diff, 0.0) + item["prob"]

        sorted_diffs = sorted(diff_probs.items(), key=lambda x: x[1], reverse=True)

        top_diff_item = sorted_diffs[0] if sorted_diffs else (0, 0.1)
        d_val, d_prob_val = top_diff_item[0], top_diff_item[1] * 100

        if d_val > 0:
            s3_name = f"{home_name} {d_val}점차 승리"
        elif d_val < 0:
            s3_name = f"{away_name} {abs(d_val)}점차 승리"
        else:
            s3_name = "무승부 공방"

        s3_desc = f"{s3_name} ({d_prob_val:.1f}%)"

        # 차순위 구도 산출근거 문자열 조합
        calc_basis_parts = []
        for diff_key, p_val in sorted_diffs[1:3]:
            pct = p_val * 100
            if diff_key > 0:
                p_name = f"{home_name} {diff_key}점차승"
            elif diff_key < 0:
                p_name = f"{away_name} {abs(diff_key)}점차승"
            else:
                p_name = "무승부"
            calc_basis_parts.append(f"{p_name} ({pct:.1f}%)")

        s3_calc_basis = ", ".join(calc_basis_parts) if calc_basis_parts else "기타 점수차 구도 분산"

        # 오버 팩터 묘사 문자열 자동 생성
        h_ov_val = int(h_over_factor * 100) if 'h_over_factor' in locals() and h_over_factor is not None else 0
        a_ov_val = int(a_over_factor * 100) if 'a_over_factor' in locals() and a_over_factor is not None else 0
        over_factor_desc = f"홈 +{h_ov_val}% / 원정 +{a_ov_val}% 가산 반영"

return {
            "status": True,
            "home_win_pct": calc_home_win,
            "draw_pct": calc_draw,
            "away_win_pct": calc_away_win,
            "score_1st": f"{best_match_52['home_score']} : {best_match_52['away_score']}",
            "p1_rate": best_match_52["prob"] * 100,
            "score_2nd": f"{second_match['home_score']} : {second_match['away_score']}",
            "p2_rate": second_match["prob"] * 100,
            "s3_desc": s3_desc,
            
            # 💡 [표 6번 렌더링 완벽 지원용 추가 메타 데이터]
            "poisson_zone_name": poisson_zone_name,
            "matrix_range": matrix_range,
            "s3_calc_basis": s3_calc_basis,
            "over_factor_desc": over_factor_desc,
            "d_prob_val": d_prob_val,

            # 💡 [디버그 센터 연동용 단계별 공수 보정치 안전 송신 세트]
            "h_step0_atk": h_step0_atk if 'h_step0_atk' in locals() else 0.0,
            "h_step0_def": h_step0_def if 'h_step0_def' in locals() else 0.0,
            "h_r1_atk": h_r1_atk if 'h_r1_atk' in locals() else 0.0,
            "h_r1_def": h_r1_def if 'h_r1_def' in locals() else 0.0,
            "h_r2_atk": h_r2_atk if 'h_r2_atk' in locals() else 0.0,
            "h_r2_def": h_r2_def if 'h_r2_def' in locals() else 0.0,
            "h_r3_tot_atk": h_r3_tot_atk if 'h_r3_tot_atk' in locals() else 0.0,
            "h_r3_tot_def": h_r3_tot_def if 'h_r3_tot_def' in locals() else 0.0,
            "h_r4_atk": h_r4_atk if 'h_r4_atk' in locals() else 0.0,
            "h_r4_def": h_r4_def if 'h_r4_def' in locals() else 0.0,
            "h_tot_atk_pct": h_tot_atk_pct if 'h_tot_atk_pct' in locals() else 0.0,
            "h_tot_def_pct": h_tot_def_pct if 'h_tot_def_pct' in locals() else 0.0,
            
            "a_step0_atk": a_step0_atk if 'a_step0_atk' in locals() else 0.0,
            "a_step0_def": a_step0_def if 'a_step0_def' in locals() else 0.0,
            "a_r1_atk": a_r1_atk if 'a_r1_atk' in locals() else 0.0,
            "a_r1_def": a_r1_def if 'a_r1_def' in locals() else 0.0,
            "a_r2_atk": a_r2_atk if 'a_r2_atk' in locals() else 0.0,
            "a_r2_def": a_r2_def if 'a_r2_def' in locals() else 0.0,
            "a_r3_tot_atk": a_r3_tot_atk if 'a_r3_tot_atk' in locals() else 0.0,
            "a_r3_tot_def": a_r3_tot_def if 'a_r3_tot_def' in locals() else 0.0,
            "a_r4_atk": a_r4_atk if 'a_r4_atk' in locals() else 0.0,
            "a_r4_def": a_r4_def if 'a_r4_def' in locals() else 0.0,
            "a_tot_atk_pct": a_tot_atk_pct if 'a_tot_atk_pct' in locals() else 0.0,
            "a_tot_def_pct": a_tot_def_pct if 'a_tot_def_pct' in locals() else 0.0
        }
# ==============================================================================
# 📦 [공통] 데이터 로딩 함수 5종 (app.py 호환)
# ==============================================================================
def load_match_data_for_engine():
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_updated": "안전 모드 (데이터 없음)", "daily_matches": {}}

def load_all_match_details_for_engine():
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

def load_v3_match_details_for_engine():
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

def load_v4_match_details_for_engine():
    v4_file = "match_details_v4.json"
    if os.path.exists(v4_file):
        try:
            with open(v4_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                return file_data.get("leagues", {})
        except Exception:
            pass
    return {}

def load_v5_match_details_for_engine():
    v5_file = "match_details_v5.json"
    if os.path.exists(v5_file):
        try:
            with open(v5_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                return file_data.get("lineup_details", {})
        except Exception:
            pass
    return {}

def load_v5_1_match_details_for_engine():
    v5_1_file = "match_details_v5-1.json"
    if os.path.exists(v5_1_file):
        try:
            with open(v5_1_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                return file_data.get("squad_details", {})
        except Exception:
            pass
    return {}


# 전역 딕셔너리 초기화 셋
engine_data = load_match_data_for_engine()
engine_daily_matches = engine_data.get("daily_matches", {})
all_details_dict = load_all_match_details_for_engine()
v3_details_dict = load_v3_match_details_for_engine()
v4_leagues_dict = load_v4_match_details_for_engine()
v5_details_dict = load_v5_match_details_for_engine()
v5_1_details_dict = load_v5_1_match_details_for_engine()


# ==============================================================================
# 🛠️ [공통 유틸리티] 퍼센트 파싱 및 country.json 로드
# ==============================================================================
def parse_pct(val_str):
    if isinstance(val_str, (int, float)):
        return float(val_str)
    if isinstance(val_str, str):
        cleaned = val_str.replace('%', '').replace('+', '').strip()
        try:
            return float(cleaned)
        except Exception:
            return 0.0
    return 0.0

def load_country_data_for_engine():
    if os.path.exists("country.json"):
        try:
            with open("country.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# ==============================================================================
# 🚀 [마스터 계산 엔진] 단계별 규칙 블록이 밀착 내장된 메인 함수
# ==============================================================================
def compute_match_prediction_master(target_detail, home_name, away_name, league_name=""):
    if not target_detail or not isinstance(target_detail, dict):
        return {"status": False, "msg": "상세 정량 데이터 없음"}

    try:
        meta_details = target_detail.get("meta_details", {})
        rankings_raw = meta_details.get("rankings", [])
        
        # ----------------------------------------------------------------------
        # [0단계 영역] 메타 및 국가 등급 정밀 판정 (안전장치 완비)
        # ----------------------------------------------------------------------
        def resolve_country_and_grade(rank_val, team_val, current_league_name="", country_data=None):
            try:
                if not country_data:
                    country_data = load_country_data_for_engine()
                grades = country_data.get("grades", {})
                rank_str = str(rank_val).strip()
                team_str = str(team_val).strip().lower()
                clean_league = str(current_league_name).strip().replace(" ", "").lower()

                if "k리그" in clean_league or "kor" in rank_str.upper():
                    for c in grades.get("C", []):
                        if c.get("code") == "KOR" or c.get("country_code") == "KOR":
                            return c.get("grade", "C"), parse_pct(c.get("attack_bonus", "+9%")), parse_pct(c.get("defense_bonus", "-9%"))
                    return "C", 9.0, -9.0

                extracted_code = ""
                if rank_str and rank_str != "-":
                    token = re.split(r'[\s\-]+', rank_str)[0].strip().upper()
                    if token and not token.isdigit():
                        extracted_code = token

                if extracted_code:
                    for grade_key, countries in grades.items():
                        if grade_key == "F": continue
                        if isinstance(countries, list):
                            for c in countries:
                                c_code = str(c.get("code", "")).strip().upper()
                                c_ccode = str(c.get("country_code", "")).strip().upper()
                                leagues_list = [str(l).strip().upper() for l in c.get("leagues", [])]
                                if (c_code and c_code == extracted_code) or (c_ccode and c_ccode == extracted_code) or any(extracted_code == l.split()[0] for l in leagues_list if l):
                                    return c.get("grade", "E"), parse_pct(c.get("attack_bonus", "+3%")), parse_pct(c.get("defense_bonus", "-3%"))

                for grade_key, countries in grades.items():
                    if grade_key == "F": continue
                    if isinstance(countries, list):
                        for c in countries:
                            kor_league = str(c.get("league_kor_name", "")).strip().replace(" ", "").lower()
                            c_name = str(c.get("name", "")).strip().lower()
                            if (kor_league and (kor_league == clean_league or f" {kor_league} " in f" {clean_league} ")) or (c_name and (c_name in clean_league or c_name in team_str)):
                                return c.get("grade", "E"), parse_pct(c.get("attack_bonus", "+3%")), parse_pct(c.get("defense_bonus", "-3%"))

                return "F", 0.0, 0.0
            except Exception:
                return "F", 0.0, 0.0

        h_step0_atk, h_step0_def = 0.0, 0.0
        a_step0_atk, a_step0_def = 0.0, 0.0
        clean_home_target = str(home_name).strip().replace(" ", "").lower()
        clean_away_target = str(away_name).strip().replace(" ", "").lower()
        found_home = found_away = False

        if rankings_raw and isinstance(rankings_raw, list):
            for r in rankings_raw:
                if not isinstance(r, dict): continue
                r_team = str(r.get("team", "-"))
                r_code = str(r.get("rank", ""))
                grade, atk_val, def_val = resolve_country_and_grade(r_code, r_team, league_name)
                clean_row_team = r_team.strip().replace(" ", "").lower()
                
                if not found_home and (clean_home_target == clean_row_team or clean_home_target in clean_row_team or clean_row_team in clean_home_target):
                    h_step0_atk, h_step0_def = atk_val, def_val
                    found_home = True
                elif not found_away and (clean_away_target == clean_row_team or clean_away_target in clean_row_team or clean_row_team in clean_home_target):
                    a_step0_atk, a_step0_def = atk_val, def_val
                    found_away = True


# ----------------------------------------------------------------------
        # [규칙 1번 영역] LIFO 10경기, 친선전 보완 및 공수 교차 대칭 특수 룰 완벽 연동
        # ----------------------------------------------------------------------
        recent_form = meta_details.get("recent_form", {})
        raw_h_matches = recent_form.get("home_matches", [])
        raw_a_matches = recent_form.get("away_matches", [])

        # 1. 공식 경기 우선 필터링 및 10경기 확보 함수
        def filter_and_supplement_matches(match_list, max_count=10):
            if not match_list or not isinstance(match_list, list): return []
            official = [m for m in match_list if isinstance(m, dict) and not any(k in str(m.get("league", "")).upper() for k in ["CF", "친선", "FRIENDLY"])]
            friendly = [m for m in match_list if isinstance(m, dict) and m not in official]
            combined = list(official)
            if len(combined) < max_count:
                combined.extend(friendly[:max_count - len(combined)])
            return combined[:max_count]

        h_matches = filter_and_supplement_matches(raw_h_matches, 10)
        a_matches = filter_and_supplement_matches(raw_a_matches, 10)

        h_sum = recent_form.get("home_summary", {})
        a_sum = recent_form.get("away_summary", {})
        
        h_gpg_base = float(target_detail.get("h_gpg", h_sum.get("goals_per_game", 1.2)))
        h_cpg_base = float(target_detail.get("cpg", h_sum.get("conceded_per_game", 1.1)))
        a_gpg_base = float(target_detail.get("a_gpg", a_sum.get("goals_per_game", 1.1)))
        a_cpg_base = float(target_detail.get("a_cpg", a_sum.get("conceded_per_game", 1.2)))

        def get_atk_tier(g):
            if g >= 2.3: return "Tier A", 12.0
            elif g >= 1.7: return "Tier B", 9.0
            elif g >= 1.1: return "Tier C", 6.0
            elif g >= 0.5: return "Tier D", 3.0
            else: return "Tier E", 0.0

        def get_def_tier(c):
            if c < 0.5: return "Tier A", -12.0
            elif c < 0.9: return "Tier B", -9.0
            elif c < 1.3: return "Tier C", -6.0
            elif c < 1.7: return "Tier D", -3.0
            else: return "Tier E", 0.0

        # 2. 공수 교차 대칭 특수 룰 및 E티어 할인 룰을 포함한 정밀 산출 함수
        def compute_rule1_stats_with_cross_tier(matches, tname, base_gpg, base_cpg):
            if not matches or not isinstance(matches, list):
                return base_gpg, base_cpg, "Tier C", "Tier C", 6.0, -6.0

            # Step 1: 1차 예비 산출 (기본 평균으로 초기 체급 판정)
            pre_at, _ = get_atk_tier(base_gpg)
            pre_de, _ = get_def_tier(base_cpg)

            eff_scored = 0.0
            eff_conceded = 0.0

            # Step 2: 확정된 체급 기반 공수 교차 보정치 대칭 적용
            for m in matches:
                if not isinstance(m, dict): continue
                teams = m.get("teams", "-")
                scores = m.get("ft_scores", ["0", "0"])
                try:
                    s1, s2 = int(scores[0]), int(scores[1])
                except Exception:
                    s1 = s2 = 0
                
                sc, cc = s1, s2
                if " vs " in teams:
                    pair = teams.split(" vs ")
                    if len(pair) == 2:
                        if tname in pair[0]: sc, cc = s1, s2
                        elif tname in pair[1]: sc, cc = s2, s1

                mult_gf = 1.0
                mult_ga = 1.0
                tier_info = m.get("opponent_tier_info", "")
                
                if tier_info and "/" in tier_info:
                    try:
                        oa, od = map(float, tier_info.split("/"))
                        at_name, _ = get_atk_tier(oa)  # 상대 공격 티어
                        df_name, _ = get_def_tier(od)  # 상대 방어 티어

                        # 공격 대칭 교차 룰
                        if pre_at == "Tier A" and (df_name == "Tier E" or od >= 2.0):
                            mult_gf = 0.5
                        elif pre_at == "Tier E" and (df_name == "Tier A" or od < 0.5):
                            mult_gf = 1.5

                        # 방어 대칭 교차 룰
                        if pre_de == "Tier A" and (at_name == "Tier E" or oa < 0.5):
                            mult_ga = 1.5
                        elif pre_de == "Tier E" and (at_name == "Tier A" or oa >= 2.3):
                            mult_ga = 0.5
                    except Exception:
                        pass

                eff_scored += (sc * mult_gf)
                eff_conceded += (cc * mult_ga)

            cnt = len(matches)
            gpg = round(eff_scored / cnt, 2) if cnt > 0 else base_gpg
            cpg = round(eff_conceded / cnt, 2) if cnt > 0 else base_cpg

            final_at, at_val = get_atk_tier(gpg)
            final_de, def_val = get_def_tier(cpg)
            return gpg, cpg, final_at, final_de, at_val, def_val

        h_base_g, h_base_c, base_h_at, base_h_de, h_r1_atk, h_r1_def = compute_rule1_stats_with_cross_tier(h_matches, home_name, h_gpg_base, h_cpg_base)
        a_base_g, a_base_c, base_a_at, base_a_de, a_r1_atk, a_r1_def = compute_rule1_stats_with_cross_tier(a_matches, away_name, a_gpg_base, a_cpg_base)
        
        # 구장 Shift 룰에서 참조할 수 있도록 하위 변수 동기화
        h_is_triggered = (base_h_at == "Tier A" or base_h_de == "Tier E")
        a_is_triggered = (base_a_at == "Tier A" or base_a_de == "Tier E")
        
        
# ----------------------------------------------------------------------
        # [규칙 2번 영역] 구장별(Stadium Form) Shift 보정 연산 (시계열 정렬 및 2차 교차 보정 완벽 연동)
        # ----------------------------------------------------------------------
        head_info = target_detail.get("head_info", {})
        venue_val = str(head_info.get("stadium", "")) or str(head_info.get("venue", ""))
        home_stadium_val = str(head_info.get("home_stadium", ""))
        
        is_neutral_venue = False
        if venue_val and home_stadium_val and home_stadium_val != "-":
            if venue_val.strip().lower() != home_stadium_val.strip().lower():
                is_neutral_venue = True

        stadium_form = target_detail.get("meta_details", {}).get("stadium_form", {"home_matches": [], "away_matches": []})

        # 1. 시계열 최신순 정렬 기능이 포함된 공식 경기 우선 필터링 함수
        def filter_and_supplement_matches_with_sort(match_list, max_count=10):
            if not match_list or not isinstance(match_list, list):
                return []
            official_matches = []
            friendly_matches = []
            for m in match_list:
                if not isinstance(m, dict): continue
                league_str = str(m.get("league", "")).upper()
                if "CF" in league_str or "친선" in league_str or "FRIENDLY" in league_str:
                    friendly_matches.append(m)
                else:
                    official_matches.append(m)
            
            combined = list(official_matches)
            if len(combined) < max_count:
                needed = max_count - len(combined)
                combined.extend(friendly_matches[:needed])
            
            selected = combined[:max_count]
            # 💡 [시계열 정렬 보장] 경기 일시 기준 최신순 정렬
            try:
                selected.sort(key=lambda x: str(x.get("match_time", "")), reverse=True)
            except Exception:
                pass
            return selected

        # 2. 홈팀 전적 추출 (중립 경기일 경우 원정/중립 성격 경기 정밀 분기)
        s_home_matches = []
        if is_neutral_venue:
            recent_all_pool = []
            if 'h_matches' in locals() and h_matches:
                recent_all_pool = h_matches
            elif stadium_form and "recent_matches" in stadium_form:
                recent_all_pool = stadium_form.get("recent_matches", [])

            neutral_home_away_matches = []
            for m in recent_all_pool:
                if not isinstance(m, dict): continue
                teams_str = str(m.get("teams", ""))
                if " vs " in teams_str:
                    t_parts = [p.strip() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2 and home_name not in t_parts[0]:
                        neutral_home_away_matches.append(m)
                elif m.get("location") == "원정" or m.get("venue_type") == "away":
                    neutral_home_away_matches.append(m)
            
            if not neutral_home_away_matches:
                neutral_home_away_matches = stadium_form.get("away_matches", [])

            s_home_matches = filter_and_supplement_matches_with_sort(neutral_home_away_matches, 10)
        else:
            raw_sh = stadium_form.get("home_matches", [])
            if not raw_sh and 'h_matches' in locals():
                raw_sh = h_matches
            s_home_matches = filter_and_supplement_matches_with_sort(raw_sh, 10)

        # 3. 원정팀 전적 추출 (공식전 우선 10경기 확보 및 최신순 정렬)
        raw_sa = stadium_form.get("away_matches", [])
        if not raw_sa and 'a_matches' in locals():
            raw_sa = a_matches
        s_away_matches = filter_and_supplement_matches_with_sort(raw_sa, 10)

        if not s_home_matches and 'h_matches' in locals(): 
            s_home_matches = filter_and_supplement_matches_with_sort(h_matches, 10)
        if not s_away_matches and 'a_matches' in locals(): 
            s_away_matches = filter_and_supplement_matches_with_sort(a_matches, 10)

        # 4. 구장별 전적 기본 베이스 득실 산출 헬퍼
        def get_base_gpg_cpg(matches, tname):
            if not matches: return 0.0, 0.0
            s_sum, c_sum = 0.0, 0.0
            for m in matches:
                if not isinstance(m, dict): continue
                scores = m.get("ft_scores", ["0", "0"])
                try: s1, s2 = int(scores[0]), int(scores[1])
                except Exception: s1 = s2 = 0
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

        s_h_gpg_base = float(target_detail.get("s_h_gpg", get_base_gpg_cpg(s_home_matches, home_name)[0]))
        s_h_cpg_base = float(target_detail.get("s_h_cpg", get_base_gpg_cpg(s_home_matches, home_name)[1]))
        s_a_gpg_base = float(target_detail.get("s_a_gpg", get_base_gpg_cpg(s_away_matches, away_name)[0]))
        s_a_cpg_base = float(target_detail.get("s_a_cpg", get_base_gpg_cpg(s_away_matches, away_name)[1]))

        # 5. 구장별 1차 예비 체급 산출 및 2차 교차 보정 체계 적용
        def compute_stadium_stats_with_cross_tier(matches, tname, base_gpg, base_cpg):
            if not matches or not isinstance(matches, list):
                return base_gpg, base_cpg, "Tier C", "Tier C"
            
            pre_at, _ = get_atk_tier(base_gpg)
            pre_de, _ = get_def_tier(base_cpg)

            eff_scored = 0.0
            eff_conceded = 0.0

            for m in matches:
                if not isinstance(m, dict): continue
                teams = m.get("teams", "-")
                scores = m.get("ft_scores", ["0", "0"])
                try: s1, s2 = int(scores[0]), int(scores[1])
                except Exception: s1 = s2 = 0
                
                sc, cc = s1, s2
                if " vs " in teams:
                    pair = teams.split(" vs ")
                    if len(pair) == 2:
                        if tname in pair[0]: sc, cc = s1, s2
                        elif tname in pair[1]: sc, cc = s2, s1

                mult_gf = 1.0
                mult_ga = 1.0
                tier_info = m.get("opponent_tier_info", "")
                
                if tier_info and "/" in tier_info:
                    try:
                        oa, od = map(float, tier_info.split("/"))
                        at_name, _ = get_atk_tier(oa)
                        df_name, _ = get_def_tier(od)

                        if pre_at == "Tier A" and (df_name == "Tier E" or od >= 2.0): mult_gf = 0.5
                        elif pre_at == "Tier E" and (df_name == "Tier A" or od < 0.5): mult_gf = 1.5

                        if pre_de == "Tier A" and (at_name == "Tier E" or oa < 0.5): mult_ga = 1.5
                        elif pre_de == "Tier E" and (at_name == "Tier A" or oa >= 2.3): mult_ga = 0.5
                    except Exception:
                        pass

                eff_scored += (sc * mult_gf)
                eff_conceded += (cc * mult_ga)

            cnt = len(matches)
            gpg = round(eff_scored / cnt, 2) if cnt > 0 else base_gpg
            cpg = round(eff_conceded / cnt, 2) if cnt > 0 else base_cpg
            final_at, _ = get_atk_tier(gpg)
            final_de, _ = get_def_tier(cpg)
            return gpg, cpg, final_at, final_de

        s_h_g, s_h_c, s_h_at, s_h_de = compute_stadium_stats_with_cross_tier(s_home_matches, home_name, s_h_gpg_base, s_h_cpg_base)
        s_a_g, s_a_c, s_a_at, s_a_de = compute_stadium_stats_with_cross_tier(s_away_matches, away_name, s_a_gpg_base, s_a_cpg_base)

        tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
        def calc_shift(base_t, stadium_t, is_atk=True):
            b_v = tier_ranks.get(base_t, 3)
            s_v = tier_ranks.get(stadium_t, 3)
            if is_atk:
                if s_v > b_v: return 15.0
                elif s_v < b_v: return -15.0
                return 0.0
            else:
                if s_v < b_v: return 15.0
                elif s_v > b_v: return -15.0
                return 0.0

        h_r2_atk = calc_shift(base_h_at, s_h_at, True)
        h_r2_def = calc_shift(base_h_de, s_h_de, False)
        a_r2_atk = calc_shift(base_a_at, s_a_at, True)
        a_r2_def = calc_shift(base_a_de, s_a_de, False)
   
        
        # [규칙 3번] 선수 전력 누수(3-1) 및 일정 중요도 및 피로 
        
# ----------------------------------------------------------------------
        # [규칙 3-1 영역] 선수 전력 누수 및 결장자 보정 연산 (app.py 3-1 규격 100% 동기화)
        # ----------------------------------------------------------------------
        target_code = str(target_detail.get("match_code", "")).strip()

        def compute_squad_changes_engine(match_code_str, home_name_str, away_name_str):
            h_tot_atk, h_tot_def = 0.0, 0.0
            a_tot_atk, a_tot_def = 0.0, 0.0
            
            try:
                v5_lineup_dict = v5_details_dict.get("lineup_details", v5_details_dict) if 'v5_details_dict' in globals() else {}
                v5_1_squad_dict = v5_1_details_dict.get("squad_details", v5_1_details_dict) if 'v5_1_details_dict' in globals() else {}
                
                clean_home = str(home_name_str).strip().replace(" ", "").lower()
                clean_away = str(away_name_str).strip().replace(" ", "").lower()
                
                # 1. V5 결장자 데이터 매칭
                v5_match_data = {}
                for k, v in v5_lineup_dict.items():
                    if not isinstance(v, dict): continue
                    v_code = str(v.get("match_code", k)).strip()
                    v_h = str(v.get("home", "")).strip().replace(" ", "").lower()
                    v_a = str(v.get("away", "")).strip().replace(" ", "").lower()
                    if v_code == match_code_str or (clean_home in v_h and clean_away in v_a):
                        v5_match_data = v
                        break
                
                raw_home_absentees = []
                raw_away_absentees = []
                if v5_match_data:
                    data_home_name = str(v5_match_data.get("home", "")).strip().replace(" ", "").lower()
                    if clean_home in data_home_name or data_home_name in clean_home:
                        h_raw_list = v5_match_data.get("home_absentees", [])
                        a_raw_list = v5_match_data.get("away_absentees", [])
                    else:
                        h_raw_list = v5_match_data.get("away_absentees", [])
                        a_raw_list = v5_match_data.get("home_absentees", [])
                    
                    raw_home_absentees = [p for p in h_raw_list if isinstance(p, dict) and str(p.get("status", "")).strip() in ["결장", "부상", "징계", "누수", "출전의심/기타"] and str(p.get("name", "")).strip()]
                    raw_away_absentees = [p for p in a_raw_list if isinstance(p, dict) and str(p.get("status", "")).strip() in ["결장", "부상", "징계", "누수", "출전의심/기타"] and str(p.get("name", "")).strip()]

                # 2. V5-1 스쿼드 풀 매칭
                v5_1_match_data = {}
                for k, v in v5_1_squad_dict.items():
                    if not isinstance(v, dict): continue
                    v_code = str(v.get("match_code", k)).strip()
                    v_h = str(v.get("home", "")).strip().replace(" ", "").lower()
                    v_a = str(v.get("away", "")).strip().replace(" ", "").lower()
                    if v_code == match_code_str or (clean_home in v_h and clean_away in v_a):
                        v5_1_match_data = v
                        break
                
                home_squad_pool = []
                away_squad_pool = []
                if v5_1_match_data:
                    data_squad_home = str(v5_1_match_data.get("home", "")).strip().replace(" ", "").lower()
                    if clean_home in data_squad_home or data_squad_home in clean_home:
                        home_squad_pool = v5_1_match_data.get("home_squad", [])
                        away_squad_pool = v5_1_match_data.get("away_squad", [])
                    else:
                        home_squad_pool = v5_1_match_data.get("away_squad", [])
                        away_squad_pool = v5_1_match_data.get("home_squad", [])

                # 3. 개별 팀 보정치 산출 내부 헬퍼 함수 (app.py 3-1 규격 동일 적용)
                def calc_team_absentee_weights(abs_list, squad_list):
                    if not abs_list:
                        return 0.0, 0.0
                    
                    squad_pos_map = {}
                    if squad_list and isinstance(squad_list, list):
                        for p in squad_list:
                            if not isinstance(p, dict): continue
                            p_name = str(p.get("name", "")).strip()
                            p_pos = str(p.get("position", "")).strip()
                            if p_name and p_pos:
                                squad_pos_map[p_name] = p_pos
                                squad_pos_map[p_name.replace(" ", "")] = p_pos
                    
                    t_atk, t_def = 0.0, 0.0
                    for item in abs_list:
                        if not isinstance(item, dict): continue
                        p_name = str(item.get("name", "-")).strip()
                        p_pos = squad_pos_map.get(p_name, squad_pos_map.get(p_name.replace(" ", ""), ""))
                        if not p_pos or p_pos == "-":
                            p_pos = "미드필더"
                        
                        p_type = str(item.get("status", "결장")).strip()
                        stats_dict = item.get("stats", {})
                        raw_grade = str(stats_dict.get("grade", item.get("grade", "C"))).strip().upper()
                        
                        if "A" in raw_grade: rate = 12.0
                        elif "B" in raw_grade: rate = 8.0
                        elif "C" in raw_grade: rate = 4.0
                        else: rate = 0.0
                        
                        is_attacker = any(k in p_pos for k in ["공격수", "FW", "MF"])
                        is_defender = any(k in p_pos for k in ["수비수", "골키퍼", "DF", "GK"])
                        
                        if p_type in ["결장", "부상", "징계", "누수", "출전의심/기타"]:
                            if is_attacker:
                                atk_v, def_v = -rate, rate / 2.0
                            elif is_defender:
                                atk_v, def_v = -rate / 2.0, rate
                            else:
                                atk_v, def_v = -rate, rate / 2.0
                        else:
                            if is_attacker:
                                atk_v, def_v = rate, -rate / 2.0
                            elif is_defender:
                                atk_v, def_v = rate / 2.0, -rate
                            else:
                                atk_v, def_v = rate, -rate / 2.0
                        
                        t_atk += atk_v
                        t_def += def_v
                    return t_atk, t_def

                h_tot_atk, h_tot_def = calc_team_absentee_weights(raw_home_absentees, home_squad_pool)
                a_tot_atk, a_tot_def = calc_team_absentee_weights(raw_away_absentees, away_squad_pool)

            except Exception as e:
                print(f"[Engine 3-1 Error Warning]: {e}")
                
            return h_tot_atk, h_tot_def, a_tot_atk, a_tot_def

        # 엔진 메인 흐름에 3-1 결과 주입
        h_r31_atk, h_r31_def, a_r31_atk, a_r31_def = compute_squad_changes_engine(target_code, home_name, away_name)
        
        
        
        
# ----------------------------------------------------------------------
        # [규칙 3-2 영역] v4 리그 순위표 연동 중요도 판정 및 타임라인 이동 피로도 정밀 산출
        # ----------------------------------------------------------------------
        def get_team_standing_info_engine(target_team_name):
            target_clean = str(target_team_name).strip().replace(" ", "")
            matched_standings = []
            v4_dict = v4_leagues_dict.get("leagues", v4_leagues_dict) if 'v4_leagues_dict' in globals() else {}
            for l_id, l_data in v4_dict.items():
                if not isinstance(l_data, dict): continue
                standings = l_data.get("standings", [])
                league_name = l_data.get("league_name", "해외 리그")
                for row in standings:
                    if not isinstance(row, dict): continue
                    row_team = str(row.get("team", "")).strip().replace(" ", "")
                    if target_clean in row_team or row_team in target_clean:
                        raw_label = str(row.get("tag_label", "일반"))
                        matched_standings.append({
                            "league_name": league_name,
                            "rank": str(row.get("rank", "-")),
                            "team": row.get("team", target_team_name),
                            "tag_label": raw_label
                        })
            return matched_standings

        def determine_match_importance_engine(standing_info_list, league_raw_name):
            league_str = str(league_raw_name)
            if any(k in league_str for k in ["친선", "CF", "탈락", "탈락확정", "강등확정"]):
                return -10.0, 10.0
            if not standing_info_list:
                return 5.0, -5.0
            
            for standing_info in standing_info_list:
                l_name = str(standing_info.get("league_name", ""))
                if l_name in league_str or league_str in l_name or any(k in league_str and k in l_name for k in ["챔피언스", "유로파", "컨퍼런스", "분데스리가", "프리미어", "라리가", "세리에", "리그"]):
                    label = str(standing_info.get("tag_label", ""))
                    if any(k in label for k in ["탈락", "탈락확정", "강등확정"]):
                        return -10.0, 10.0
                    if any(k in label for k in ["진출권", "플레이오프", "승격", "우승", "qualifying", "play-offs", "Playoff"]) or any(k in league_str for k in ["챔피언스", "유로파", "결승", "컵", "ACL", "CL"]):
                        return 15.0, -15.0

            return 5.0, -5.0

        home_standings_list = get_team_standing_info_engine(home_name)
        away_standings_list = get_team_standing_info_engine(away_name)
        tournament_display = str(target_detail.get("tournament", "리그 경기"))

        h_imp_atk, h_imp_def = determine_match_importance_engine(home_standings_list, tournament_display)
        a_imp_atk, a_imp_def = determine_match_importance_engine(away_standings_list, tournament_display)

        # 타임라인 기반 피로도 단계 정밀 산출 (fixtures 데이터 연동)
        fixtures_info = meta_details.get("fixtures", {})
        raw_home_fixes = list(fixtures_info.get("home", []))
        raw_away_fixes = list(fixtures_info.get("away", []))
        match_date_str = str(target_detail.get("match_time", "2026-06-01"))

        def parse_fatigue_stage_strictly(fix_list, recent_list, is_home_team):
            base_dt = datetime.now()
            try:
                base_dt = datetime.strptime(match_date_str.split(" ")[0].replace(".", "-").replace("/", "-")[:10], "%Y-%m-%d")
            except Exception:
                pass

            combined_pool = []
            seen = set()
            for f in list(fix_list) + list(recent_list):
                if not isinstance(f, dict): continue
                uid = f"{f.get('match_time', '')}_{f.get('teams', '')}"
                if uid not in seen:
                    combined_pool.append(f)
                    seen.add(uid)

            past_arr = []
            for f in combined_pool:
                m_time_str = str(f.get("match_time", ""))
                try:
                    c_dt = datetime.strptime(m_time_str.split(" ")[0].replace(".", "-").replace("/", "-")[:10], "%Y-%m-%d")
                    d_diff = (c_dt - base_dt).days
                    if d_diff < 0:
                        past_arr.append((d_diff, f))
                except Exception:
                    continue

            chrono_past = sorted(past_arr, key=lambda x: x[0])
            has_4d_away = False
            has_7d_away = False

            for d_d, f_item in chrono_past:
                abs_d = abs(d_d)
                teams_raw = str(f_item.get("teams", ""))
                # 원정 여부 판정 (팀명이 원정에 위치하거나 로케이션이 원정인 경우)
                is_away_match = ("원정" in str(f_item.get("location", "")) or "away" in str(f_item.get("venue_type", "")))
                
                if 1 <= abs_d <= 4 and is_away_match:
                    has_4d_away = True
                elif 4 < abs_d <= 7 and is_away_match:
                    has_7d_away = True

            acc = 0
            if has_4d_away: acc += 1
            if has_7d_away: acc += 1

            my_loc = "홈" if is_home_team else "원정"
            if acc > 0 and my_loc == "원정":
                return acc + 1
            elif acc > 0:
                return acc
            else:
                return 1 if my_loc == "원정" else 0

        h_fatigue_stage = parse_fatigue_stage_strictly(raw_home_fixes, h_matches, True)
        a_fatigue_stage = parse_fatigue_stage_strictly(raw_away_fixes, a_matches, False)

        h_r32_atk = (-5.0 * h_fatigue_stage)
        h_r32_def = (5.0 * h_fatigue_stage)
        a_r32_atk = (-5.0 * a_fatigue_stage)
        a_r32_def = (5.0 * a_fatigue_stage)

        # 규칙 3번 최종 통합 합산 (3-1 누수 + 3-2 중요도 + 피로도)
        h_r3_tot_atk = h_r31_atk + h_imp_atk + h_r32_atk
        h_r3_tot_def = h_r31_def + h_imp_def + h_r32_def
        a_r3_tot_atk = a_r31_atk + a_imp_atk + a_r32_atk
        a_r3_tot_def = a_r31_def + a_imp_def + a_r32_def

# ----------------------------------------------------------------------
        # [규칙 4번 영역] 맞대결 H2H 상성 및 단방향 10% 룰 (app.py 4단계 100% 동기화)
        # ----------------------------------------------------------------------
        h2h_info = meta_details.get("h2h", {})
        h2h_matches = h2h_info.get("matches", [])
        
        home_wins = 0
        away_wins = 0
        total_games = len(h2h_matches) if isinstance(h2h_matches, list) else 0

        if total_games > 0 and isinstance(h2h_matches, list):
            for m in h2h_matches:
                if not isinstance(m, dict): continue
                row_cols = m.get("row_data", [])
                if len(row_cols) >= 4:
                    h_team_name = str(row_cols[1]).strip()
                    score_str = str(row_cols[2]).strip()
                    try:
                        scores = score_str.replace("：", "-").split("-")
                        h_score = int(scores[0].strip())
                        a_score = int(scores[1].strip())
                        
                        # 홈팀 기준으로 승패 판정
                        if h_team_name == home_name:
                            if h_score > a_score:
                                home_wins += 1
                            elif h_score < a_score:
                                away_wins += 1
                        else:
                            if h_score > a_score:
                                away_wins += 1
                            elif h_score < a_score:
                                home_wins += 1
                    except Exception:
                        pass

        home_win_rate = (home_wins / total_games * 100) if total_games > 0 else 0.0
        away_win_rate = (away_wins / total_games * 100) if total_games > 0 else 0.0

        h_r4_atk, h_r4_def = 0.0, 0.0
        a_r4_atk, a_r4_def = 0.0, 0.0

        # 표본 5경기 이상 및 승률 50% 이상 우세 팀에만 단방향 보정(+10% / -10%) 부여
        if total_games >= 5:
            if home_win_rate >= 50.0:
                h_r4_atk, h_r4_def = 10.0, -10.0
            elif away_win_rate >= 50.0:
                a_r4_atk, a_r4_def = 10.0, -10.0

        # ==============================================================================
        # 🎯 [0~5단계 통합 누적 합산 규격] 공격력 및 방어력 보정치 전 단계 완벽 결속 (5-1 표 연동)
        # ==============================================================================
        h_tot_atk_pct = h_step0_atk + h_r1_atk + h_r2_atk + h_r3_tot_atk + h_r4_atk
        h_tot_def_pct = h_step0_def + h_r1_def + h_r2_def + h_r3_tot_def + h_r4_def  # 방어력 누락분 완전 결속

        a_tot_atk_pct = a_step0_atk + a_r1_atk + a_r2_atk + a_r3_tot_atk + a_r4_atk
        a_tot_def_pct = a_step0_def + a_r1_def + a_r2_def + a_r3_tot_def + a_r4_def  # 방어력 누락분 완전 결속

        # [규칙 5번 - 5-1 산출] 최종 보정 및 1차 기본 기대 득실점 산출
        h_max_g = h_base_g * (1 + h_tot_atk_pct / 100.0)
        h_min_c = h_base_c * (1 + h_tot_def_pct / 100.0)
        a_max_g = a_base_g * (1 + a_tot_atk_pct / 100.0)
        a_min_c = a_base_c * (1 + a_tot_def_pct / 100.0)

        h_final_exp_g = max(0.2, (h_max_g + (2.0 - a_min_c)) / 2.0)
        h_final_exp_c = max(0.2, (h_min_c + (2.0 - a_max_g)) / 2.0)
        a_final_exp_g = max(0.2, (a_max_g + (2.0 - h_min_c)) / 2.0)
        a_final_exp_c = max(0.2, (a_min_c + (2.0 - h_max_g)) / 2.0)


        # ==============================================================================
        # 📊 [규칙 5번 - 5-2 영역] 동급 티어 실전 7경기 교차 검증 및 실전 평균 득실 추출 규격
        # ==============================================================================
        
        # 1. 2단계 체급 및 상대 연동 체급 확정
        h_opp_at = s_a_at if 's_a_at' in locals() else "Tier C"
        h_opp_de = s_a_de if 's_a_de' in locals() else "Tier C"
        a_opp_at = s_h_at if 's_h_at' in locals() else "Tier C"
        a_opp_de = s_h_de if 's_h_de' in locals() else "Tier C"

        home_raw_pool = []
        away_raw_pool = []
        stadium_form_block = target_detail.get("meta_details", {}).get("stadium_form", {})
        if stadium_form_block:
            home_raw_pool = stadium_form_block.get("home_matches", [])
            away_raw_pool = stadium_form_block.get("away_matches", [])
        if not home_raw_pool:
            home_raw_pool = s_home_matches if 's_home_matches' in locals() and s_home_matches else (h_matches if 'h_matches' in locals() else [])
        if not away_raw_pool:
            away_raw_pool = s_away_matches if 's_away_matches' in locals() and s_away_matches else (a_matches if 'a_matches' in locals() else [])

        # 2. 친선전 제외 및 동급 티어 매칭 7경기 필터링 함수 (시계열 최신순 정렬 포함)
        def get_real_matches_without_friendlies(match_list):
            if not match_list or not isinstance(match_list, list): return []
            valid = []
            for fix in match_list:
                if not isinstance(fix, dict): continue
                league_raw = str(fix.get("league", "")).lower()
                if any(k in league_raw for k in ["친선", "friendly", "int cf", "club friendlies", "friendlies"]):
                    continue
                score_str = str(fix.get("score", "") or fix.get("result", ""))
                scores_arr = fix.get("ft_scores", [])
                if not score_str and (scores_arr and len(scores_arr) >= 2):
                    score_str = f"{scores_arr[0]} : {scores_arr[1]}"
                if score_str or scores_arr:
                    valid.append(fix)
            return valid

        def filter_matched_tier_games_engine(match_list, target_at_name, target_de_name):
            valid_pool = get_real_matches_without_friendlies(match_list)
            if not valid_pool: return []

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
                    except: pass
                op_at_name = atk_tier_nm(oa) if 'atk_tier_nm' in globals() else "Tier C"
                op_de_name = def_tier_nm(od) if 'def_tier_nm' in globals() else "Tier C"
                
                op_at_val = tier_score_map.get(op_at_name, 3)
                op_de_val = tier_score_map.get(op_de_name, 3)

                diff_at = abs(t_at_val - op_at_val)
                diff_de = abs(t_de_val - op_de_val)
                match_score = diff_at + diff_de
                scored_pool.append((match_score, m))

            scored_pool.sort(key=lambda x: x[0])
            sorted_matches = [item[1] for item in scored_pool[:7]]
            try:
                sorted_matches.sort(key=lambda x: str(x.get("match_time", "")), reverse=True)
            except: pass
            return sorted_matches

        home_matched_7 = filter_matched_tier_games_engine(home_raw_pool, h_opp_at, h_opp_de)
        away_matched_7 = filter_matched_tier_games_engine(away_raw_pool, a_opp_at, a_opp_de)

        # 3. 5-2 실전 득실 평균 산출 헬퍼 함수
        def compute_52_real_avg(match_list, team_label, my_at, my_de):
            if not match_list: return 0.0, 0.0
            tot_gf = tot_ga = 0.0
            cnt = len(match_list)
            for m in match_list:
                if not isinstance(m, dict): continue
                scores_arr = m.get("ft_scores", [])
                m_score = str(m.get("score", "") or m.get("result", "0 : 0"))
                if scores_arr and len(scores_arr) >= 2:
                    m_score = f"{scores_arr[0]} : {scores_arr[1]}"
                
                teams_str = str(m.get("teams", ""))
                is_team_home = True
                if " vs " in teams_str:
                    t_parts = [p.strip() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2 and team_label.strip() in t_parts[1] and team_label.strip() not in t_parts[0]:
                        is_team_home = False

                raw_s1 = raw_s2 = 0
                try:
                    parts = m_score.replace("-", ":").split(":")
                    if len(parts) >= 2:
                        raw_s1 = int(parts[0].strip())
                        raw_s2 = int(parts[1].strip())
                except: pass

                gf = raw_s2 if (not is_team_home and " vs " in teams_str) else raw_s1
                ga = raw_s1 if (not is_team_home and " vs " in teams_str) else raw_s2

                # 5-2 공수 대칭 교차 보정 독립 적용
                tier_info = m.get("opponent_tier_info", "")
                oa, od = 1.3, 1.2
                if tier_info and "/" in tier_info:
                    try:
                        oa, od = map(float, tier_info.split("/"))
                    except: pass
                at_name = atk_tier_nm(oa) if 'atk_tier_nm' in globals() else "Tier C"
                df_name = def_tier_nm(od) if 'def_tier_nm' in globals() else "Tier C"

                mult_gf = mult_ga = 1.0
                if my_at == "Tier A" and df_name == "Tier E": mult_gf = 0.5
                elif my_at == "Tier E" and df_name == "Tier A": mult_gf = 1.5
                if my_de == "Tier A" and at_name == "Tier E": mult_ga = 1.5
                elif my_de == "Tier E" and at_name == "Tier A": mult_ga = 0.5

                tot_gf += (gf * mult_gf)
                tot_ga += (ga * mult_ga)

            return (tot_gf / cnt if cnt > 0 else 0.0), (tot_ga / cnt if cnt > 0 else 0.0)

        # 최종 실전 평균 득실 산출 (5-2 표 핵심 결과물)
        h_agf, h_aga = compute_52_real_avg(home_matched_7, home_name, h_base_g, h_base_c)
        a_agf, a_aga = compute_52_real_avg(away_matched_7, away_name, a_base_g, a_base_c)
        
        # 4. 안전 방어 수용
        h_agf = float(target_detail.get("h_agf", h_agf if h_agf > 0 else h_base_g))
        h_aga = float(target_detail.get("h_aga", h_aga if h_aga > 0 else h_base_c))
        a_agf = float(target_detail.get("a_agf", a_agf if a_agf > 0 else a_base_g))
        a_aga = float(target_detail.get("a_aga", a_aga if a_aga > 0 else a_base_c))
# ==============================================================================
        # 📈 [규칙 5-3 영역] 다득점/체급차 변동성 보정 (Over Factor) 및 최종 람다 결합
        # ==============================================================================
        
        # 1. 1단계/2단계 체급 안전 참조 (base_h_at 또는 h_current_at 호환 방어)
        h_at_ref = base_h_at if 'base_h_at' in locals() else (h_current_at if 'h_current_at' in locals() else "Tier C")
        a_at_ref = base_a_at if 'base_a_at' in locals() else (a_current_at if 'a_current_at' in locals() else "Tier C")

        tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
        h_tier_val = tier_ranks.get(h_at_ref, 3)
        a_tier_val = tier_ranks.get(a_at_ref, 3)
        tier_diff = abs(h_tier_val - a_tier_val)

        # 2. 오버 팩터 계수 초기화
        h_over_factor = 0.0
        a_over_factor = 0.0

        # 3. 체급 격차형 및 동급 난타전형 조건 판정
        if tier_diff >= 2:
            add_rate = 0.10 + (tier_diff - 2) * 0.10
            if h_tier_val > a_tier_val: 
                h_over_factor = add_rate
            else: 
                a_over_factor = add_rate
        elif (h_final_exp_g + a_final_exp_g > 3.2) or (h_final_exp_c >= 1.50 or a_final_exp_c >= 1.50):
            h_over_factor = 0.15
            a_over_factor = 0.15

        # 4. 💡 최종 람다(Expected Goals) 산정 시 [5-1/5-2 1차 기대치+실전 평균]과 [5-3 오버 팩터] 정밀 결합 연동
        h_final = max(0.2, ((h_final_exp_g * (1 + h_over_factor)) + h_agf) / 2.0)
        a_final = max(0.2, ((a_final_exp_g * (1 + a_over_factor)) + a_agf) / 2.0)
        total_expected_goals = h_final + a_final

        # ==============================================================================
        # 📊 [5-4] 이원화 동적 골 범위 행렬 확정 및 구획 분류 (엔진 백엔드 연동)
        # ==============================================================================
        if total_expected_goals < 2.2:
            poisson_zone_name = "저득점 통제 구역 (total < 2.2)"
            matrix_range = "0 ~ 3골 범위 (4×4 행렬)"
        elif total_expected_goals <= 3.2 and tier_diff < 2:
            poisson_zone_name = "표준 득점 구역 (2.2 ~ 3.2)"
            matrix_range = "0 ~ 4골 범위 (5×5 행렬 - 기본)"
        else:
            poisson_zone_name = "다득점 변동 구역 (total > 3.2 또는 격차 2단계 이상)"
            matrix_range = "0 ~ 6골 / 0 ~ 7골 동적 확장 행렬"
        
# --------------------------------------------------------------------------
        # 🧮 [규칙 6] 푸아송 분포 및 승무패 확률 / 예측 순위 정밀 연산 블록 (최종 완벽 동기화)
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

        safe_h_final = float(h_final) if 'h_final' in locals() and h_final is not None else 1.0
        safe_a_final = float(a_final) if 'a_final' in locals() and a_final is not None else 1.0

        total_exp_goals = safe_h_final + safe_a_final

        # 동적 행렬 범위 및 푸아송 구역 명칭 확정
        if total_exp_goals < 2.2:
            matrix_max_k = 3
            poisson_zone_name = "저득점 통제 구역 (total < 2.2)"
            matrix_range = "0 ~ 3 골 범위 (4×4 행렬)"
        elif total_exp_goals <= 3.2 and (tier_diff if 'tier_diff' in locals() else 0) < 2:
            matrix_max_k = 4
            poisson_zone_name = "표준 득점 구역 (2.2 ~ 3.2)"
            matrix_range = "0 ~ 4 골 범위 (5×5 행렬 - 기본)"
        else:
            matrix_max_k = 6
            poisson_zone_name = "다득점 변동 구역 (total > 3.2 또는 격차 2단계 이상)"
            matrix_range = "0 ~ 6 골 / 0 ~ 7골 동적 확장 행렬"

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

        # 💡 [핵심] 5-2 표의 실전 평균 득실 값(h_agf, a_agf)을 명확하게 타겟으로 설정
        h_target_52 = float(h_agf) if 'h_agf' in locals() and h_agf is not None else 1.0
        a_target_52 = float(a_agf) if 'a_agf' in locals() and a_agf is not None else 1.0

        # [1순위] 규칙 5-2 결과에 가장 적합한 결과값 최우선 선정 (피트니스 점수 공식 정밀 적용)
        scored_candidates = []
        for item in score_probs:
            hg, ag, prob = item["home_score"], item["away_score"], item["prob"]
            v52_distance = abs(hg - h_target_52) + abs(ag - a_target_52)
            fitness_score = v52_distance - (prob * 3.0)
            scored_candidates.append({"home_score": hg, "away_score": ag, "prob": prob, "fitness": fitness_score})

        sorted_by_fitness = sorted(scored_candidates, key=lambda x: x["fitness"])
        best_match_52 = sorted_by_fitness[0]

        # [2순위] 1순위를 제외한 푸아송 확률 제일 높은 단일 스코어 선정
        sorted_by_prob = sorted(score_probs, key=lambda x: x["prob"], reverse=True)
        second_match = None
        for s in sorted_by_prob:
            if not (s["home_score"] == best_match_52["home_score"] and s["away_score"] == best_match_52["away_score"]):
                second_match = s
                break
        if not second_match:
            second_match = sorted_by_prob[1] if len(sorted_by_prob) > 1 else best_match_52

        # [3순위] 각 점수 차이별 확률 합산 후 가장 많이 차지한 점수 차이 구도 및 상세 산출근거 생성
        diff_probs = {}
        for item in score_probs:
            diff = item["home_score"] - item["away_score"]
            diff_probs[diff] = diff_probs.get(diff, 0.0) + item["prob"]

        sorted_diffs = sorted(diff_probs.items(), key=lambda x: x[1], reverse=True)

        top_diff_item = sorted_diffs[0] if sorted_diffs else (0, 0.1)
        d_val, d_prob_val = top_diff_item[0], top_diff_item[1] * 100

        if d_val > 0:
            s3_name = f"{home_name} {d_val}점차 승리"
        elif d_val < 0:
            s3_name = f"{away_name} {abs(d_val)}점차 승리"
        else:
            s3_name = "무승부 공방"

        s3_desc = f"{s3_name} ({d_prob_val:.1f}%)"

        # 차순위 구도 산출근거 문자열 조합
        calc_basis_parts = []
        for diff_key, p_val in sorted_diffs[1:3]:
            pct = p_val * 100
            if diff_key > 0:
                p_name = f"{home_name} {diff_key}점차승"
            elif diff_key < 0:
                p_name = f"{away_name} {abs(diff_key)}점차승"
            else:
                p_name = "무승부"
            calc_basis_parts.append(f"{p_name} ({pct:.1f}%)")

        s3_calc_basis = ", ".join(calc_basis_parts) if calc_basis_parts else "기타 점수차 구도 분산"

        # 오버 팩터 묘사 문자열 자동 생성
        h_ov_val = int(h_over_factor * 100) if 'h_over_factor' in locals() and h_over_factor is not None else 0
        a_ov_val = int(a_over_factor * 100) if 'a_over_factor' in locals() and a_over_factor is not None else 0
        over_factor_desc = f"홈 +{h_ov_val}% / 원정 +{a_ov_val}% 가산 반영"

return {
            "status": True,
            "home_win_pct": calc_home_win,
            "draw_pct": calc_draw,
            "away_win_pct": calc_away_win,
            "score_1st": f"{best_match_52['home_score']} : {best_match_52['away_score']}",
            "p1_rate": best_match_52["prob"] * 100,
            "score_2nd": f"{second_match['home_score']} : {second_match['away_score']}",
            "p2_rate": second_match["prob"] * 100,
            "s3_desc": s3_desc,
            
            # 💡 [표 6번 렌더링 완벽 지원용 추가 메타 데이터]
            "poisson_zone_name": poisson_zone_name,
            "matrix_range": matrix_range,
            "s3_calc_basis": s3_calc_basis,
            "over_factor_desc": over_factor_desc,
            "d_prob_val": d_prob_val,

            # 💡 [디버그 센터 연동용 단계별 공수 보정치 안전 송신 세트]
            "h_step0_atk": h_step0_atk if 'h_step0_atk' in locals() else 0.0,
            "h_step0_def": h_step0_def if 'h_step0_def' in locals() else 0.0,
            "h_r1_atk": h_r1_atk if 'h_r1_atk' in locals() else 0.0,
            "h_r1_def": h_r1_def if 'h_r1_def' in locals() else 0.0,
            "h_r2_atk": h_r2_atk if 'h_r2_atk' in locals() else 0.0,
            "h_r2_def": h_r2_def if 'h_r2_def' in locals() else 0.0,
            "h_r3_tot_atk": h_r3_tot_atk if 'h_r3_tot_atk' in locals() else 0.0,
            "h_r3_tot_def": h_r3_tot_def if 'h_r3_tot_def' in locals() else 0.0,
            "h_r4_atk": h_r4_atk if 'h_r4_atk' in locals() else 0.0,
            "h_r4_def": h_r4_def if 'h_r4_def' in locals() else 0.0,
            "h_tot_atk_pct": h_tot_atk_pct if 'h_tot_atk_pct' in locals() else 0.0,
            "h_tot_def_pct": h_tot_def_pct if 'h_tot_def_pct' in locals() else 0.0,
            
            "a_step0_atk": a_step0_atk if 'a_step0_atk' in locals() else 0.0,
            "a_step0_def": a_step0_def if 'a_step0_def' in locals() else 0.0,
            "a_r1_atk": a_r1_atk if 'a_r1_atk' in locals() else 0.0,
            "a_r1_def": a_r1_def if 'a_r1_def' in locals() else 0.0,
            "a_r2_atk": a_r2_atk if 'a_r2_atk' in locals() else 0.0,
            "a_r2_def": a_r2_def if 'a_r2_def' in locals() else 0.0,
            "a_r3_tot_atk": a_r3_tot_atk if 'a_r3_tot_atk' in locals() else 0.0,
            "a_r3_tot_def": a_r3_tot_def if 'a_r3_tot_def' in locals() else 0.0,
            "a_r4_atk": a_r4_atk if 'a_r4_atk' in locals() else 0.0,
            "a_r4_def": a_r4_def if 'a_r4_def' in locals() else 0.0,
            "a_tot_atk_pct": a_tot_atk_pct if 'a_tot_atk_pct' in locals() else 0.0,
            "a_tot_def_pct": a_tot_def_pct if 'a_tot_def_pct' in locals() else 0.0
        }

