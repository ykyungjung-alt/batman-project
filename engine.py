import math
import os
import json
import re
from datetime import datetime
import pandas as pd

# ==============================================================================
# 📦 [공통] 데이터 로딩 함수 5종 (전역 레벨)
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
# ⚽ [공통 티어 및 특수 룰 유틸리티]
# ==============================================================================
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

def check_special_rule_trigger(matches, tname, base_gpg, base_cpg):
    at_nm, _ = get_atk_tier(base_gpg)
    df_nm, _ = get_def_tier(base_cpg)
    if not matches:
        return at_nm == "Tier A" or df_nm == "Tier E"
    
    raw_s, raw_c = 0.0, 0.0
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
        raw_s += sc
        raw_c += cc
        
    cnt = len(matches)
    tmp_gpg = raw_s / cnt if cnt > 0 else base_gpg
    tmp_cpg = raw_c / cnt if cnt > 0 else base_cpg
    
    at_nm_tmp, _ = get_atk_tier(tmp_gpg)
    df_nm_tmp, _ = get_def_tier(tmp_cpg)
    return (at_nm_tmp == "Tier A") or (df_nm_tmp == "Tier E")

def compute_adjusted_stats_with_discount(matches, tname, base_gpg, base_cpg, is_triggered=False):
    if not matches or not isinstance(matches, list):
        return base_gpg, base_cpg
        
    eff_scored = 0.0
    eff_conceded = 0.0
    
    for m in matches:
        if not isinstance(m, dict): continue
        teams = str(m.get("teams", "-"))
        scores = m.get("ft_scores", ["0", "0"])
        try: s1, s2 = int(scores[0]), int(scores[1])
        except Exception: s1 = s2 = 0
            
        sc, cc = s1, s2
        if " vs " in teams:
            pair = teams.split(" vs ")
            if len(pair) == 2:
                t1, t2 = pair[0].strip(), pair[1].strip()
                if tname in t1: sc, cc = s1, s2
                elif tname in t2: sc, cc = s2, s1
                
        mult = 1.0
        tier_info = m.get("opponent_tier_info", "")
        if tier_info and "/" in tier_info:
            try:
                oa, od = map(float, tier_info.split("/"))
                at_name, _ = get_atk_tier(oa)
                df_name, _ = get_def_tier(od)
                if is_triggered and (at_name == "Tier E" or df_name == "Tier E"):
                    mult = 0.5
            except Exception:
                pass
                
        eff_scored += (sc * mult)
        eff_conceded += (cc * mult)
        
    cnt = len(matches)
    gpg = round(eff_scored / cnt, 2) if cnt > 0 else base_gpg
    cpg = round(eff_conceded / cnt, 2) if cnt > 0 else base_cpg
    return gpg, cpg

# ==============================================================================
# 🚀 [마스터 계산 엔진] 단일 메인 순차 파이프라인 함수
# ==============================================================================
def compute_match_prediction_master(target_detail, home_name, away_name, league_name=""):
    # 💡 [안전망 장치] 데이터 누락 시 기본 디폴트 세션 구축
    if not target_detail or not isinstance(target_detail, dict):
        target_detail = {
            "head_info": {"stadium": "-", "home_stadium": "-"},
            "meta_details": {
                "rankings": [],
                "recent_form": {"home_summary": {"goals_per_game": 1.2, "conceded_per_game": 1.1}, "away_summary": {"goals_per_game": 1.1, "conceded_per_game": 1.2}, "home_matches": [], "away_matches": []},
                "stadium_form": {"home_matches": [], "away_matches": []},
                "h2h": {"matches": []},
                "fixtures": {"home": [], "away": []}
            }
        }

    try:
        meta_details = target_detail.get("meta_details", {})
        rankings_raw = meta_details.get("rankings", [])
        
        # ======================================================================
        # 🟢 [0단계] Country 등급 및 공격/수비 보정치 산출
        # ======================================================================
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

# ======================================================================
        # 🟢 [1단계] LIFO 최근 경기 득실 산출 및 기본 기대치 실시간 연동 (UI 완벽 일치 교정)
        # ======================================================================
        recent_form = meta_details.get("recent_form", {})
        raw_h_matches = recent_form.get("home_matches", [])
        raw_a_matches = recent_form.get("away_matches", [])

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
        
        # UI와 동일한 키 체인 우선 적용 후, 0 이하일 경우 10경기 풀 직접 연산값으로 폴백
        h_gpg_base = round(float(h_sum.get("goals_per_game", h_sum.get("gpg", target_detail.get("h_gpg", 0)))), 2)
        h_cpg_base = round(float(h_sum.get("conceded_per_game", h_sum.get("cpg", target_detail.get("h_cpg", 0)))), 2)
        a_gpg_base = round(float(a_sum.get("goals_per_game", a_sum.get("gpg", target_detail.get("a_gpg", 0)))), 2)
        a_cpg_base = round(float(a_sum.get("conceded_per_game", a_sum.get("cpg", target_detail.get("a_cpg", 0)))), 2)

        # 💡 만약 요약 데이터가 비어있거나 0이라면 실제 h_matches / a_matches 배열을 직접 집계하여 GPG/CPG 산출
        def compute_direct_gpg_cpg(matches, tname):
            if not matches or not isinstance(matches, list): return 0.0, 0.0
            tot_sc, tot_cc = 0.0, 0.0
            cnt = len(matches)
            for m in matches:
                if not isinstance(m, dict): continue
                scores = m.get("ft_scores", ["0", "0"])
                try: s1, s2 = int(scores[0]), int(scores[1])
                except: s1 = s2 = 0
                teams = str(m.get("teams", ""))
                sc, cc = s1, s2
                if " vs " in teams:
                    pair = teams.split(" vs ")
                    if len(pair) == 2:
                        if tname in pair[0]: sc, cc = s1, s2
                        elif tname in pair[2] if len(pair) > 2 else tname in pair[1]: sc, cc = s2, s1
                tot_sc += sc
                tot_cc += cc
            return (tot_sc / cnt if cnt > 0 else 1.2), (tot_cc / cnt if cnt > 0 else 1.1)

        if h_gpg_base <= 0 or h_cpg_base <= 0:
            dir_hg, dir_hc = compute_direct_gpg_cpg(h_matches, home_name)
            if h_gpg_base <= 0: h_gpg_base = round(dir_hg, 2)
            if h_cpg_base <= 0: h_cpg_base = round(dir_hc, 2)

        if a_gpg_base <= 0 or a_cpg_base <= 0:
            dir_ag, dir_ac = compute_direct_gpg_cpg(a_matches, away_name)
            if a_gpg_base <= 0: a_gpg_base = round(dir_ag, 2)
            if a_cpg_base <= 0: a_cpg_base = round(dir_ac, 2)

        # 최후의 안전 방어
        if h_gpg_base <= 0: h_gpg_base = 1.2
        if h_cpg_base <= 0: h_cpg_base = 1.1
        if a_gpg_base <= 0: a_gpg_base = 1.1
        if a_cpg_base <= 0: a_cpg_base = 1.2

        h_is_triggered = check_special_rule_trigger(h_matches, home_name, h_gpg_base, h_cpg_base)
        a_is_triggered = check_special_rule_trigger(a_matches, away_name, a_gpg_base, a_cpg_base)

        calc_h_base_g, calc_h_base_c = compute_adjusted_stats_with_discount(h_matches, home_name, h_gpg_base, h_cpg_base, h_is_triggered)
        calc_a_base_g, calc_a_base_c = compute_adjusted_stats_with_discount(a_matches, away_name, a_gpg_base, a_cpg_base, a_is_triggered)

        # 최종 엔진 베이스 득실 확정
        h_base_g = calc_h_base_g if calc_h_base_g > 0 else h_gpg_base
        h_base_c = calc_h_base_c if calc_h_base_c > 0 else h_cpg_base
        a_base_g = calc_a_base_g if calc_a_base_g > 0 else a_gpg_base
        a_base_c = calc_a_base_c if calc_a_base_c > 0 else a_cpg_base

        base_h_at, h_r1_atk = get_atk_tier(h_base_g)
        base_h_de, h_r1_def = get_def_tier(h_base_c)
        base_a_at, a_r1_atk = get_atk_tier(a_base_g)
        base_a_de, a_r1_def = get_def_tier(a_base_c)
        
# ======================================================================
        # 🟢 [2단계] 구장(Stadium Form) Shift 보정 연산 (APP 규격 100% 동기화 완벽 교정)
        # ======================================================================
        head_info = target_detail.get("head_info", {})
        venue_val = str(head_info.get("stadium", "")) or str(head_info.get("venue", ""))
        home_stadium_val = str(head_info.get("home_stadium", ""))
        
        is_neutral_venue = False
        if venue_val and home_stadium_val and home_stadium_val != "-":
            if venue_val.strip().lower() != home_stadium_val.strip().lower():
                is_neutral_venue = True

        stadium_form = target_detail.get("meta_details", {}).get("stadium_form", {"home_matches": [], "away_matches": []})

        def filter_and_supplement_matches_with_sort(match_list, max_count=10):
            if not match_list or not isinstance(match_list, list): return []
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
                combined.extend(friendly_matches[:max_count - len(combined)])
            
            selected = combined[:max_count]
            try:
                selected.sort(key=lambda x: str(x.get("match_time", "1970-01-01")), reverse=True)
            except Exception:
                pass
            return selected

        s_home_matches = []
        if is_neutral_venue:
            recent_all_pool = []
            if 'h_matches' in locals() and h_matches:
                recent_all_pool = h_matches
            elif stadium_form and "recent_matches" in stadium_form:
                recent_all_pool = stadium_form.get("recent_matches", [])

            neutral_home_away_matches = []
            clean_home_check = str(home_name).strip().lower()
            for m in recent_all_pool:
                if not isinstance(m, dict): continue
                teams_str = str(m.get("teams", ""))
                if " vs " in teams_str:
                    t_parts = [p.strip().lower() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2 and clean_home_check not in t_parts[0]:
                        neutral_home_away_matches.append(m)
                elif str(m.get("location", "")) == "원정" or str(m.get("venue_type", "")) == "away":
                    neutral_home_away_matches.append(m)
            
            if not neutral_home_away_matches:
                neutral_home_away_matches = stadium_form.get("away_matches", [])

            s_home_matches = filter_and_supplement_matches_with_sort(neutral_home_away_matches, 10)
        else:
            raw_sh = stadium_form.get("home_matches", [])
            if not raw_sh and 'h_matches' in locals():
                raw_sh = h_matches
            s_home_matches = filter_and_supplement_matches_with_sort(raw_sh, 10)

        raw_sa = stadium_form.get("away_matches", [])
        if not raw_sa and 'a_matches' in locals():
            raw_sa = a_matches
        s_away_matches = filter_and_supplement_matches_with_sort(raw_sa, 10)

        if not s_home_matches and 'h_matches' in locals(): 
            s_home_matches = filter_and_supplement_matches_with_sort(h_matches, 10)
        if not s_away_matches and 'a_matches' in locals(): 
            s_away_matches = filter_and_supplement_matches_with_sort(a_matches, 10)

        def get_base_gpg_cpg(matches, tname):
            if not matches: return 0.0, 0.0
            s_sum, c_sum = 0.0, 0.0
            t_clean = str(tname).strip().lower()
            for m in matches:
                if not isinstance(m, dict): continue
                scores = m.get("ft_scores", ["0", "0"])
                try: s1, s2 = int(scores[0]), int(scores[1])
                except Exception: s1 = s2 = 0
                teams = str(m.get("teams", "")).lower()
                sc, cc = s1, s2
                if " vs " in teams:
                    pair = teams.split(" vs ")
                    if len(pair) == 2:
                        if t_clean in pair[0]: sc, cc = s1, s2
                        elif t_clean in pair[1]: sc, cc = s2, s1
                s_sum += sc
                c_sum += cc
            cnt = len(matches)
            return (s_sum / cnt if cnt > 0 else 0.0), (c_sum / cnt if cnt > 0 else 0.0)

        s_h_gpg_base = float(target_detail.get("s_h_gpg", get_base_gpg_cpg(s_home_matches, home_name)[0]))
        s_h_cpg_base = float(target_detail.get("s_h_cpg", get_base_gpg_cpg(s_home_matches, home_name)[1]))
        s_a_gpg_base = float(target_detail.get("s_a_gpg", get_base_gpg_cpg(s_away_matches, away_name)[0]))
        s_a_cpg_base = float(target_detail.get("s_a_cpg", get_base_gpg_cpg(s_away_matches, away_name)[1]))

        s_h_g, s_h_c = compute_adjusted_stats_with_discount(s_home_matches, home_name, s_h_gpg_base, s_h_cpg_base, h_is_triggered)
        s_a_g, s_a_c = compute_adjusted_stats_with_discount(s_away_matches, away_name, s_a_gpg_base, s_a_cpg_base, a_is_triggered)

        s_h_at, _ = get_atk_tier(s_h_g)
        s_h_de, _ = get_def_tier(s_h_c)
        s_a_at, _ = get_atk_tier(s_a_g)
        s_a_de, _ = get_def_tier(s_a_c)

        tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
        
        # 💡 [APP 규격 완벽 일치] 2단계 구장 Shift 보정치 산출 함수
        def calc_shift(base_t, stadium_t, is_atk=True):
            b_v = tier_ranks.get(base_t, 3)
            s_v = tier_ranks.get(stadium_t, 3)
            if is_atk:
                if s_v > b_v: return 15.0      # 공격 상향 ➔ +15%
                elif s_v < b_v: return -15.0   # 공격 하향 ➔ -15%
                return 0.0
            else:
                # 방어: s_v < b_v (실점 감소/수비 상향, 예: D➔C) 이면 -15%, 악화(s_v > b_v)면 +15%
                if s_v < b_v: return -15.0
                elif s_v > b_v: return 15.0
                return 0.0

        # 💡 [핵심 동기화] 중립구장 여부와 무관하게 APP와 동일하게 보정치 연동 (또는 APP의 중립구장 조건 반영)
        h_r2_atk = calc_shift(base_h_at, s_h_at, True)
        h_r2_def = calc_shift(base_h_de, s_h_de, False)
        a_r2_atk = calc_shift(base_a_at, s_a_at, True)
        a_r2_def = calc_shift(base_a_de, s_a_de, False)

# ======================================================================
        # 🟢 [3단계] 선수 전력 누수(3-1) 및 일정 중요도·피로도(3-2) 복합 가중치 정밀 연산
        # ======================================================================
        target_code = str(target_detail.get("match_code", "")).strip()

        # 1. [3-1] 선수 전력 누수 가중치 독립 산출
        h_r31_atk, h_r31_def = compute_single_team_absentee_engine(target_code, home_name, is_home=True)
        a_r31_atk, a_r31_def = compute_single_team_absentee_engine(target_code, away_name, is_home=False)

        # 2. [3-2] 리그 순위표 및 중요도 태그 연동 함수
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
                    row_team = str(row.get("team", "")).strip().replace(" ", "").lower()
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
                            "tag_label": kor_label
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

        # 3. [3-2] 타임라인 기반 이동 피로도 단계 및 가중치 산출
        fixtures_info = meta_details.get("fixtures", {})
        raw_home_fixes = list(fixtures_info.get("home", []))
        raw_away_fixes = list(fixtures_info.get("away", []))
        match_date_str = str(target_detail.get("match_time", "2026-06-01"))

        def parse_fatigue_stage_strictly_engine(fix_list, recent_list, is_home_team):
            base_dt = datetime.now()
            try:
                base_clean = match_date_str.split(" ")[0].replace(".", "-").replace("/", "-")
                base_dt = datetime.strptime(base_clean[:10], "%Y-%m-%d")
            except Exception: pass

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
                    c_clean = m_time_str.split(" ")[0].replace(".", "-").replace("/", "-")
                    c_dt = datetime.strptime(c_clean[:10], "%Y-%m-%d")
                    d_diff = (c_dt - base_dt).days
                    if d_diff < 0: past_arr.append((d_diff, f))
                except Exception: continue

            chrono_past = sorted(past_arr, key=lambda x: x[0])
            past_7d_count = past_4d_count = 0

            for d_d, f_item in chrono_past:
                abs_d = abs(d_d)
                is_away_match = ("원정" in str(f_item.get("location", "")) or "away" in str(f_item.get("venue_type", "")))
                if 1 <= abs_d <= 4 and is_away_match: past_4d_count += 1
                elif 4 < abs_d <= 7 and is_away_match: past_7d_count += 1

            current_fatigue_acc = 0
            if past_4d_count > 0: current_fatigue_acc += 1
            if past_7d_count > 0: current_fatigue_acc += 1

            my_loc = "홈" if is_home_team else "원정"
            if current_fatigue_acc > 0 and my_loc == "원정":
                final_match_fatigue_stage = current_fatigue_acc + 1
            elif current_fatigue_acc > 0:
                final_match_fatigue_stage = current_fatigue_acc
            else:
                final_match_fatigue_stage = 1 if my_loc == "원정" else 0

            return final_match_fatigue_stage

        h_fatigue_stage = parse_fatigue_stage_strictly_engine(raw_home_fixes, h_matches, True)
        a_fatigue_stage = parse_fatigue_stage_strictly_engine(raw_away_fixes, a_matches, False)

        # 피로도에 따른 2종류 가중치 변환 (단계별 공격 -5%, 방어 +5%)
        h_fa = -5.0 * h_fatigue_stage
        h_fd = 5.0 * h_fatigue_stage
        a_fa = -5.0 * a_fatigue_stage
        a_fd = 5.0 * a_fatigue_stage

        # 4. 규칙 3번 최종 토탈 합산 (3-1 누수 + 3-2 중요도 + 3-2 피로도 2종류 모두 포함)
        h_r3_tot_atk = h_r31_atk + h_imp_atk + h_fa
        h_r3_tot_def = h_r31_def + h_imp_def + h_fd
        a_r3_tot_atk = a_r31_atk + a_imp_atk + a_fa
        a_r3_tot_def = a_r31_def + a_imp_def + a_fd
       
        
        # ======================================================================
        # 🟢 [4단계] H2H 맞대결 상성 가중치 연산
        # ======================================================================
        h2h_info = meta_details.get("h2h", {})
        h2h_matches = h2h_info.get("matches", [])
        
        home_wins = away_wins = 0
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
                        h_score, a_score = int(scores[0].strip()), int(scores[1].strip())
                        if h_team_name == home_name:
                            if h_score > a_score: home_wins += 1
                            elif h_score < a_score: away_wins += 1
                        else:
                            if h_score > a_score: away_wins += 1
                            elif h_score < a_score: home_wins += 1
                    except Exception: pass

        home_win_rate = (home_wins / total_games * 100) if total_games > 0 else 0.0
        away_win_rate = (away_wins / total_games * 100) if total_games > 0 else 0.0

        h_r4_atk = h_r4_def = a_r4_atk = a_r4_def = 0.0
        if total_games >= 5:
            if home_win_rate >= 50.0: h_r4_atk, h_r4_def = 10.0, -10.0
            elif away_win_rate >= 50.0: a_r4_atk, a_r4_def = 10.0, -10.0

        # ======================================================================
        # 🟢 [5단계] 누적 보정치 합산 및 교차 결합 득실점 산출
        # ======================================================================
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

        h_opp_at = s_a_at if 's_a_at' in locals() else "Tier C"
        h_opp_de = s_a_de if 's_a_de' in locals() else "Tier C"
        a_opp_at = s_h_at if 's_h_at' in locals() else "Tier C"
        a_opp_de = s_h_de if 's_h_de' in locals() else "Tier C"

        home_raw_pool = stadium_form.get("home_matches", []) if stadium_form else []
        away_raw_pool = stadium_form.get("away_matches", []) if stadium_form else []
        if not home_raw_pool: home_raw_pool = s_home_matches if 's_home_matches' in locals() else h_matches
        if not away_raw_pool: away_raw_pool = s_away_matches if 's_away_matches' in locals() else a_matches

        def get_real_matches_without_friendlies(match_list):
            if not match_list or not isinstance(match_list, list): return []
            valid = []
            for fix in match_list:
                if not isinstance(fix, dict): continue
                league_raw = str(fix.get("league", "")).lower()
                if any(k in league_raw for k in ["친선", "friendly", "int cf", "club friendlies"]): continue
                if str(fix.get("score", "")) or fix.get("ft_scores", []): valid.append(fix)
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
                    try: oa, od = map(float, tier_info.split("/")[:2])
                    except: pass
                op_at_name, _ = get_atk_tier(oa)
                op_de_name, _ = get_def_tier(od)
                match_score = abs(t_at_val - tier_score_map.get(op_at_name, 3)) + abs(t_de_val - tier_score_map.get(op_de_name, 3))
                scored_pool.append((match_score, m))

            scored_pool.sort(key=lambda x: x[0])
            sorted_matches = [item[1] for item in scored_pool[:7]]
            try: sorted_matches.sort(key=lambda x: str(x.get("match_time", "")), reverse=True)
            except: pass
            return sorted_matches

        home_matched_7 = filter_matched_tier_games_engine(home_raw_pool, h_opp_at, h_opp_de)
        away_matched_7 = filter_matched_tier_games_engine(away_raw_pool, a_opp_at, a_opp_de)

        def compute_52_real_avg(match_list, team_label):
            if not match_list: return 0.0, 0.0
            tot_gf = tot_ga = 0.0
            cnt = len(match_list)
            for m in match_list:
                if not isinstance(m, dict): continue
                scores_arr = m.get("ft_scores", [])
                m_score = str(m.get("score", "") or m.get("result", "0 : 0"))
                if scores_arr and len(scores_arr) >= 2: m_score = f"{scores_arr[0]} : {scores_arr[1]}"
                
                teams_str = str(m.get("teams", ""))
                is_team_home = True
                if " vs " in teams_str:
                    t_parts = [p.strip() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2 and team_label.strip() in t_parts[1] and team_label.strip() not in t_parts[0]:
                        is_team_home = False

                raw_s1 = raw_s2 = 0
                try:
                    parts = m_score.replace("-", ":").split(":")
                    if len(parts) >= 2: raw_s1, raw_s2 = int(parts[0].strip()), int(parts[1].strip())
                except: pass

                gf = raw_s2 if (not is_team_home and " vs " in teams_str) else raw_s1
                ga = raw_s1 if (not is_team_home and " vs " in teams_str) else raw_s2
                tot_gf += gf
                tot_ga += ga
            return (tot_gf / cnt if cnt > 0 else 0.0), (tot_ga / cnt if cnt > 0 else 0.0)

        h_agf, h_aga = compute_52_real_avg(home_matched_7, home_name)
        a_agf, a_aga = compute_52_real_avg(away_matched_7, away_name)
        
        h_agf = float(target_detail.get("h_agf", h_agf if h_agf > 0 else h_base_g))
        h_aga = float(target_detail.get("h_aga", h_aga if h_aga > 0 else h_base_c))
        a_agf = float(target_detail.get("a_agf", a_agf if a_agf > 0 else a_base_g))
        a_aga = float(target_detail.get("a_aga", a_aga if a_aga > 0 else a_base_c))

        h_at_ref = base_h_at if 'base_h_at' in locals() else "Tier C"
        a_at_ref = base_a_at if 'base_a_at' in locals() else "Tier C"
        h_tier_val = tier_ranks.get(h_at_ref, 3)
        a_tier_val = tier_ranks.get(a_at_ref, 3)
        tier_diff = abs(h_tier_val - a_tier_val)

        h_over_factor = a_over_factor = 0.0
        if tier_diff >= 2:
            add_rate = 0.10 + (tier_diff - 2) * 0.10
            if h_tier_val > a_tier_val: h_over_factor = add_rate
            else: a_over_factor = add_rate
        elif (h_final_exp_g + a_final_exp_g > 3.2) or (h_final_exp_c >= 1.50 or a_final_exp_c >= 1.50):
            h_over_factor = a_over_factor = 0.15

        h_final = max(0.2, ((h_final_exp_g * (1 + h_over_factor)) + h_agf) / 2.0)
        a_final = max(0.2, ((a_final_exp_g * (1 + a_over_factor)) + a_agf) / 2.0)
        total_expected_goals = h_final + a_final

        # ======================================================================
        # 🟢 [6단계] 푸아송 분포 및 승무패/스코어 최종 확률 도출
        # ======================================================================
        def poisson_prob(lmbda, k):
            if lmbda <= 0 and k == 0: return 1.0
            try: return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
            except: return 0.0

        if total_expected_goals < 2.2:
            matrix_max_k = 3
            poisson_zone_name = "저득점 통제 구역 (total < 2.2)"
            matrix_range = "0 ~ 3골 범위 (4×4 행렬)"
        elif total_expected_goals <= 3.2 and tier_diff < 2:
            matrix_max_k = 4
            poisson_zone_name = "표준 득점 구역 (2.2 ~ 3.2)"
            matrix_range = "0 ~ 4골 범위 (5×5 행렬 - 기본)"
        else:
            matrix_max_k = 6
            poisson_zone_name = "다득점 변동 구역 (total > 3.2 또는 격차 2단계 이상)"
            matrix_range = "0 ~ 6골 / 0 ~ 7골 동적 확장 행렬"

        win_loss_probs = []
        score_probs = []
        for h_g in range(matrix_max_k + 1):
            for a_g in range(matrix_max_k + 1):
                p_h = poisson_prob(h_final_exp_g, h_g)
                p_a = poisson_prob(a_final_exp_g, a_g)
                win_loss_probs.append({"home_score": h_g, "away_score": a_g, "prob": p_h * p_a})

                p_h2 = poisson_prob(h_final, h_g)
                p_a2 = poisson_prob(a_final, a_g)
                score_probs.append({"home_score": h_g, "away_score": a_g, "prob": p_h2 * p_a2})

        calc_home_win = sum(item["prob"] for item in win_loss_probs if item["home_score"] > item["away_score"]) * 100
        calc_away_win = sum(item["prob"] for item in win_loss_probs if item["home_score"] < item["away_score"]) * 100
        calc_draw = sum(item["prob"] for item in win_loss_probs if item["home_score"] == item["away_score"]) * 100

        scored_candidates = []
        for item in score_probs:
            hg, ag, prob = item["home_score"], item["away_score"], item["prob"]
            fitness_score = (abs(hg - h_agf) + abs(ag - a_agf)) - (prob * 3.0)
            scored_candidates.append({"home_score": hg, "away_score": ag, "prob": prob, "fitness": fitness_score})

        sorted_by_fitness = sorted(scored_candidates, key=lambda x: x["fitness"])
        best_match_52 = sorted_by_fitness[0]

        sorted_by_prob = sorted(score_probs, key=lambda x: x["prob"], reverse=True)
        second_match = next((s for s in sorted_by_prob if not (s["home_score"] == best_match_52["home_score"] and s["away_score"] == best_match_52["away_score"])), sorted_by_prob[1] if len(sorted_by_prob) > 1 else best_match_52)

        diff_probs = {}
        for item in score_probs:
            diff = item["home_score"] - item["away_score"]
            diff_probs[diff] = diff_probs.get(diff, 0.0) + item["prob"]

        sorted_diffs = sorted(diff_probs.items(), key=lambda x: x[1], reverse=True)
        top_diff_item = sorted_diffs[0] if sorted_diffs else (0, 0.1)
        d_val, d_prob_val = top_diff_item[0], top_diff_item[1] * 100

        if d_val > 0: s3_name = f"{home_name} {d_val}점차 승리"
        elif d_val < 0: s3_name = f"{away_name} {abs(d_val)}점차 승리"
        else: s3_name = "무승부 공방"
        s3_desc = f"{s3_name} ({d_prob_val:.1f}%)"

        calc_basis_parts = []
        for diff_key, p_val in sorted_diffs[1:3]:
            pct = p_val * 100
            p_name = f"{home_name} {diff_key}점차승" if diff_key > 0 else (f"{away_name} {abs(diff_key)}점차승" if diff_key < 0 else "무승부")
            calc_basis_parts.append(f"{p_name} ({pct:.1f}%)")
        s3_calc_basis = ", ".join(calc_basis_parts) if calc_basis_parts else "기타 점수차 구도 분산"

        over_factor_desc = f"홈 +{int(h_over_factor * 100)}% / 원정 +{int(a_over_factor * 100)}% 가산 반영"

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
            
            "poisson_zone_name": poisson_zone_name,
            "matrix_range": matrix_range,
            "s3_calc_basis": s3_calc_basis,
            "over_factor_desc": over_factor_desc,
            "d_prob_val": d_prob_val,

            # 디버그 센터 싱크로율 유지를 위한 베이스 득실 전송
            "h_gpg": h_base_g,
            "h_cpg": h_base_c,
            "a_gpg": a_base_g,
            "a_cpg": a_base_c,

            # 🏠 홈팀 단계별 보정치 (규칙 3번 세분화 키 완벽 포함)
            "h_step0_atk": h_step0_atk, "h_step0_def": h_step0_def,
            "h_r1_atk": h_r1_atk, "h_r1_def": h_r1_def,
            "h_r2_atk": h_r2_atk, "h_r2_def": h_r2_def,
            "h_r31_atk": h_r31_atk, "h_r31_def": h_r31_def,
            "h_imp_atk": h_imp_atk, "h_imp_def": h_imp_def,
            "h_fa": h_fa, "h_fd": h_fd,
            "h_r3_tot_atk": h_r3_tot_atk, "h_r3_tot_def": h_r3_tot_def,
            "h_r4_atk": h_r4_atk, "h_r4_def": h_r4_def,
            "h_tot_atk_pct": h_tot_atk_pct, "h_tot_def_pct": h_tot_def_pct,
            
            # ✈️ 원정팀 단계별 보정치 (규칙 3번 세분화 키 완벽 포함)
            "a_step0_atk": a_step0_atk, "a_step0_def": a_step0_def,
            "a_r1_atk": a_r1_atk, "a_r1_def": a_r1_def,
            "a_r2_atk": a_r2_atk, "a_r2_def": a_r2_def,
            "a_r31_atk": a_r31_atk, "a_r31_def": a_r31_def,
            "a_imp_atk": a_imp_atk, "a_imp_def": a_imp_def,
            "a_fa": a_fa, "a_fd": a_fd,
            "a_r3_tot_atk": a_r3_tot_atk, "a_r3_tot_def": a_r3_tot_def,
            "a_r4_atk": a_r4_atk, "a_r4_def": a_r4_def,
            "a_tot_atk_pct": a_tot_atk_pct, "a_tot_def_pct": a_tot_def_pct
        }

    except Exception as e:
        print(f"[Engine Master Critical Error]: {e}")
        return {"status": False, "msg": str(e)}
