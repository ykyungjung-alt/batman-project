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
        
======================================================================
        # 🟢 [0단계] Country 등급 및 공격/수비 보정치 산출 (앱 연동 완벽 일치 규격)
        # ======================================================================
        def resolve_country_and_grade(rank_val, team_val, current_league_name="", country_data=None):
            try:
                if not country_data:
                    country_data = load_country_data_for_engine()
                grades = country_data.get("grades", {})
                rank_str = str(rank_val).strip()
                team_str = str(team_val).strip().lower()
                clean_league = str(current_league_name).strip().replace(" ", "").lower()

                # 1. 최우선 방어: K리그 또는 KOR 관련 키워드 검출
                if "k리그" in clean_league or "kor" in rank_str.upper():
                    for c in grades.get("C", []):
                        if c.get("code") == "KOR" or c.get("country_code") == "KOR":
                            return c.get("grade", "C"), parse_pct(c.get("attack_bonus", "+9%")), parse_pct(c.get("defense_bonus", "-9%"))
                    return "C", 9.0, -9.0

                # 2. 1차 시도: 순위표 rank_str에서 국가/리그 코드 토큰 추출 (예: ITA D1, BRA D1 등)
                extracted_code = ""
                if rank_str and rank_str != "-" and not rank_str.isdigit():
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
                                    return c.get("grade", grade_key), parse_pct(c.get("attack_bonus", "+3%")), parse_pct(c.get("defense_bonus", "-3%"))

                # 3. 2차 시도: 리그명 그대로 엄격한 분리 대조 (브라질 vs 이탈리아 세리에 A 명확한 구분)
                for grade_key, countries in grades.items():
                    if grade_key == "F": continue
                    if isinstance(countries, list):
                        for c in countries:
                            kor_league = str(c.get("league_kor_name", "")).strip().replace(" ", "").lower()
                            c_code = str(c.get("country_code", "")).strip().upper()
                            c_name = str(c.get("name", "")).strip().lower()
                            
                            # 💡 브라질("세리에 a"가 있더라도 리그명에 명시적으로 브라질이 없으면 브라질 매칭 건너뜀)
                            if c_code == "BRA" and "브라질" not in clean_league:
                                continue
                            # 💡 이탈리아(리그명에 '브라질'이 들어가거나 순수 '세리에'가 아니면 이탈리아 매칭 건너뜀)
                            if c_code == "ITA" and "브라질" in clean_league:
                                continue

                            # 완전 일치 또는 포함 관계 검증
                            match_kor = kor_league and (kor_league == clean_league or clean_league == kor_league or (len(clean_league) >= 4 and clean_league in kor_league))
                            match_name = c_name and (c_name in clean_league or c_name in team_str)

                            if match_kor or match_name:
                                return c.get("grade", grade_key), parse_pct(c.get("attack_bonus", "+3%")), parse_pct(c.get("defense_bonus", "-3%"))

                # 4. 3차 시도: 영문 리그 코드 대조
                for grade_key, countries in grades.items():
                    if grade_key == "F": continue
                    if isinstance(countries, list):
                        for c in countries:
                            leagues_list = [str(l).strip().lower() for l in c.get("leagues", [])]
                            if any(l == clean_league or l in clean_league for l in leagues_list if l):
                                return c.get("grade", grade_key), parse_pct(c.get("attack_bonus", "+3%")), parse_pct(c.get("defense_bonus", "-3%"))

                # 5. 최종 매칭 실패 시 F등급 폴백 처리
                f_info = grades.get("F", {})
                return "F", parse_pct(f_info.get("attack_bonus", "0%")), parse_pct(f_info.get("defense_bonus", "0%"))
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
                elif not found_away and (clean_away_target == clean_row_team or clean_away_target in clean_row_team or clean_row_team in clean_away_target):
                    a_step0_atk, a_step0_def = atk_val, def_val
                    found_away = True


# ======================================================================
        # 🟢 [1단계 순수 백엔드 연산] LIFO 최근 10경기 및 독립 특수룰 파이프라인
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
        h_gpg_base = round(float(h_sum.get("goals_per_game", 0)), 2)
        h_cpg_base = round(float(h_sum.get("conceded_per_game", 0)), 2)
        
        a_gpg_base = round(float(a_sum.get("goals_per_game", 0)), 2)
        a_cpg_base = round(float(a_sum.get("conceded_per_game", 0)), 2)

        def engine_atk_tier(g):
            if g >= 2.3: return "Tier A", "+12.0%"
            elif g >= 1.7: return "Tier B", "+9.0%"
            elif g >= 1.1: return "Tier C", "+6.0%"
            elif g >= 0.5: return "Tier D", "+3.0%"
            else: return "Tier E", "0.0%"

        def engine_def_tier(c):
            if c < 0.5: return "Tier A", "-12.0%"
            elif c < 0.9: return "Tier B", "-9.0%"
            elif c < 1.3: return "Tier C", "-6.0%"
            elif c < 1.7: return "Tier D", "-3.0%"
            else: return "Tier E", "0.0%"

        def engine_local_make_df_with_trigger(matches, tname, def_gpg, def_cpg, my_at="Tier C", my_de="Tier C"):
            if not matches or not isinstance(matches, list):
                return def_gpg, def_cpg, 0.0, 0.0, False
            
            eff_scored = 0.0
            eff_conceded = 0.0
            raw_scored_total = 0.0
            raw_conceded_total = 0.0
            is_triggered_flag = False
            
            for m in matches:
                if not isinstance(m, dict): continue
                scores_arr = m.get("ft_scores", [])
                score_str = str(m.get("score", "") or m.get("result", ""))
                
                s1, s2 = 0, 0
                if scores_arr and len(scores_arr) >= 2:
                    try: s1, s2 = int(scores_arr[0]), int(scores_arr[1])
                    except: pass
                elif score_str:
                    try:
                        parts_s = score_str.replace("：", ":").replace("-", ":").split(":")
                        if len(parts_s) >= 2:
                            s1 = int(parts_s[0].strip())
                            s2 = int(parts_s[1].strip())
                    except: pass
                    
                teams = str(m.get("teams", "-"))
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
                
                mult_gf = 1.0
                mult_ga = 1.0
                tier_info = str(m.get("opponent_tier_info", ""))
                at_name, df_name = "Tier C", "Tier C"
                
                if tier_info:
                    try:
                        atk_match = re.search(r'공격([A-E])\(([\d\.]+)\)', tier_info)
                        def_match = re.search(r'방어([A-E])\(([\d\.]+)\)', tier_info)
                        if atk_match: at_name = f"Tier {atk_match.group(1)}"
                        if def_match: df_name = f"Tier {def_match.group(1)}"
                        
                        if my_at in ["Tier A", "Tier E"]:
                            if my_at == "Tier A" and df_name == "Tier E":
                                mult_gf = 0.5
                                is_triggered_flag = True
                            elif my_at == "Tier E" and df_name == "Tier A":
                                mult_gf = 1.5
                                is_triggered_flag = True

                        if my_de in ["Tier A", "Tier E"]:
                            if my_de == "Tier A" and at_name == "Tier E":
                                mult_ga = 1.5
                                is_triggered_flag = True
                            elif my_de == "Tier E" and at_name == "Tier A":
                                mult_ga = 0.5
                                is_triggered_flag = True
                    except: pass
                        
                eff_scored += (sc * mult_gf)
                eff_conceded += (cc * mult_ga)
                
            cnt = len(matches)
            gpg = round(eff_scored / cnt, 2) if cnt > 0 else def_gpg
            cpg = round(eff_conceded / cnt, 2) if cnt > 0 else def_cpg
            return gpg, cpg, raw_scored_total, raw_conceded_total, is_triggered_flag

        # 1단계 1차 예비 산출
        h_gpg_pre, h_cpg_pre, h_raw_s, h_raw_c, _ = engine_local_make_df_with_trigger(h_matches, home_name, h_gpg_base, h_cpg_base, "Tier C", "Tier C")
        h_cnt = len(h_matches) if h_matches else 10
        h_pure_gpg = round(h_raw_s / h_cnt, 2) if h_cnt > 0 else (h_gpg_base if h_gpg_base > 0 else 1.2)
        h_pure_cpg = round(h_raw_c / h_cnt, 2) if h_cnt > 0 else (h_cpg_base if h_cpg_base > 0 else 1.1)
        h_at_pre, _ = engine_atk_tier(h_pure_gpg)
        h_de_pre, _ = engine_def_tier(h_pure_cpg)

        a_gpg_pre, a_cpg_pre, a_raw_s_a, a_raw_c_a, _ = engine_local_make_df_with_trigger(a_matches, away_name, a_gpg_base, a_cpg_base, "Tier C", "Tier C")
        a_cnt = len(a_matches) if a_matches else 10
        a_pure_gpg = round(a_raw_s_a / a_cnt, 2) if a_cnt > 0 else (a_gpg_base if a_gpg_base > 0 else 1.1)
        a_pure_cpg = round(a_raw_c_a / a_cnt, 2) if a_cnt > 0 else (a_cpg_base if a_cpg_base > 0 else 1.2)
        a_at_pre, _ = engine_atk_tier(a_pure_gpg)
        a_de_pre, _ = engine_def_tier(a_pure_cpg)

        # 1단계 2차 최종 보정 산출 및 플래그 확정
        h_gpg, h_cpg, _, _, h_is_triggered = engine_local_make_df_with_trigger(h_matches, home_name, h_gpg_base, h_cpg_base, h_at_pre, h_de_pre)
        a_gpg, a_cpg, _, _, a_is_triggered = engine_local_make_df_with_trigger(a_matches, away_name, a_gpg_base, a_cpg_base, a_at_pre, a_de_pre)

        base_h_at, h_atw_str = engine_atk_tier(h_gpg)
        base_h_de, h_dew_str = engine_def_tier(h_cpg)
        base_a_at, a_atw_str = engine_atk_tier(a_gpg)
        base_a_de, a_dew_str = engine_def_tier(a_cpg)

        h_r1_atk = parse_pct(h_atw_str) if 'parse_pct' in globals() else 6.0
        h_r1_def = parse_pct(h_dew_str) if 'parse_pct' in globals() else -6.0
        a_r1_atk = parse_pct(a_atw_str) if 'parse_pct' in globals() else 6.0
        a_r1_def = parse_pct(a_dew_str) if 'parse_pct' in globals() else -6.0

# ======================================================================
        # 🟢 [2단계] 구장(Stadium Form) Shift 보정 연산 (특수룰 플래그 완벽 연동)
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

        # 💡 1단계에서 정상 정의된 h_is_triggered와 a_is_triggered가 에러 없이 안전하게 연동됨
        s_h_g, s_h_c = compute_adjusted_stats_with_discount(s_home_matches, home_name, s_h_gpg_base, s_h_cpg_base, h_is_triggered)
        s_a_g, s_a_c = compute_adjusted_stats_with_discount(s_away_matches, away_name, s_a_gpg_base, s_a_cpg_base, a_is_triggered)

        s_h_at, _ = engine_atk_tier(s_h_g)
        s_h_de, _ = engine_def_tier(s_h_c)
        s_a_at, _ = engine_atk_tier(s_a_g)
        s_a_de, _ = engine_def_tier(s_a_c)

        tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
        
        def calc_shift(base_t, stadium_t, is_atk=True):
            b_v = tier_ranks.get(base_t, 3)
            s_v = tier_ranks.get(stadium_t, 3)
            if is_atk:
                if s_v > b_v: return 15.0
                elif s_v < b_v: return -15.0
                return 0.0
            else:
                # 💡 방어 보정 부호 교정: 구장 체급이 높을 때(s_v > b_v) 수비 상향/실점 감소이므로 마이너스(-) 보정
                if s_v > b_v: return -15.0
                elif s_v < b_v: return 15.0
                return 0.0

        h_r2_atk = calc_shift(base_h_at, s_h_at, True)
        h_r2_def = calc_shift(base_h_de, s_h_de, False)
        a_r2_atk = calc_shift(base_a_at, s_a_at, True)
        a_r2_def = calc_shift(base_a_de, s_a_de, False)
        
        # ======================================================================
        # 🟢 [규칙 3단계 통합] 선수 전력 누수(3-1) 및 일정 중요도·피로도(3-2) 정밀 연산 브릿지
        # ======================================================================
        target_code = str(target_detail.get("match_code", "")).strip()

        # 0. 선수 전력 누수 가중치 독립 산출 엔진 함수 (3-1)
        def compute_single_team_absentee_engine(match_code_str, team_name_str, is_home=True):
            tot_atk, tot_def = 0.0, 0.0
            try:
                v5_lineup_dict = v5_details_dict.get("lineup_details", v5_details_dict) if 'v5_details_dict' in globals() else {}
                v5_1_squad_dict = v5_1_details_dict.get("squad_details", v5_1_details_dict) if 'v5_1_details_dict' in globals() else {}
                
                clean_target = str(team_name_str).strip().replace(" ", "").lower()
                
                v5_match_data = {}
                for k, v in v5_lineup_dict.items():
                    if not isinstance(v, dict): continue
                    v_code = str(v.get("match_code", k)).strip()
                    v_h = str(v.get("home", "")).strip().replace(" ", "").lower()
                    v_a = str(v.get("away", "")).strip().replace(" ", "").lower()
                    if v_code == match_code_str or clean_target in v_h or clean_target in v_a:
                        v5_match_data = v
                        break
                
                abs_list = []
                if v5_match_data:
                    data_home_name = str(v5_match_data.get("home", "")).strip().replace(" ", "").lower()
                    if clean_target in data_home_name or data_home_name in clean_target:
                        abs_list = v5_match_data.get("home_absentees", []) if is_home else v5_match_data.get("away_absentees", [])
                    else:
                        abs_list = v5_match_data.get("away_absentees", []) if is_home else v5_match_data.get("home_absentees", [])
                    
                    abs_list = [p for p in abs_list if isinstance(p, dict) and str(p.get("status", "")).strip() in ["결장", "부상", "징계", "누수", "출전의심/기타"] and str(p.get("name", "")).strip()]

                v5_1_match_data = {}
                for k, v in v5_1_squad_dict.items():
                    if not isinstance(v, dict): continue
                    v_code = str(v.get("match_code", k)).strip()
                    v_h = str(v.get("home", "")).strip().replace(" ", "").lower()
                    v_a = str(v.get("away", "")).strip().replace(" ", "").lower()
                    if v_code == match_code_str or clean_target in v_h or clean_target in v_a:
                        v5_1_match_data = v
                        break
                
                squad_list = []
                if v5_1_match_data:
                    data_squad_home = str(v5_1_match_data.get("home", "")).strip().replace(" ", "").lower()
                    if clean_target in data_squad_home or data_squad_home in clean_target:
                        squad_list = v5_1_match_data.get("home_squad", []) if is_home else v5_1_match_data.get("away_squad", [])
                    else:
                        squad_list = v5_1_match_data.get("away_squad", []) if is_home else v5_1_match_data.get("home_squad", [])

                squad_pos_map = {}
                if squad_list and isinstance(squad_list, list):
                    for p in squad_list:
                        if not isinstance(p, dict): continue
                        p_name = str(p.get("name", "")).strip()
                        p_pos = str(p.get("position", "")).strip()
                        if p_name and p_pos:
                            squad_pos_map[p_name] = p_pos
                            squad_pos_map[p_name.replace(" ", "")] = p_pos
                
                for item in abs_list:
                    if not isinstance(item, dict): continue
                    p_name = str(item.get("name", "-")).strip()
                    p_pos = squad_pos_map.get(p_name, squad_pos_map.get(p_name.replace(" ", ""), ""))
                    if not p_pos or p_pos == "-": p_pos = "미드필더"
                    
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
                        if is_attacker: atk_v, def_v = -rate, rate / 2.0
                        elif is_defender: atk_v, def_v = -rate / 2.0, rate
                        else: atk_v, def_v = -rate, rate / 2.0
                    else:
                        if is_attacker: atk_v, def_v = rate, -rate / 2.0
                        elif is_defender: atk_v, def_v = rate / 2.0, -rate
                        else: atk_v, def_v = rate, -rate / 2.0
                    
                    tot_atk += atk_v
                    tot_def += def_v
            except Exception:
                pass
            return tot_atk, tot_def

        # 1. [3-1] 선수 전력 누수 가중치 산출 실행
        h_r31_atk, h_r31_def = compute_single_team_absentee_engine(target_code, home_name, is_home=True)
        a_r31_atk, a_r31_def = compute_single_team_absentee_engine(target_code, away_name, is_home=False)

        # 2. [3-2] 리그 순위표 및 중요도 태그 연동 엔진 함수
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

        # 홈/원정 중요도 독립 분리 매핑 (오타 원천 차단)
        h_imp_atk_val, h_imp_def_val = determine_match_importance_engine(home_standings_list, tournament_display)
        a_imp_atk_val, a_imp_def_val = determine_match_importance_engine(away_standings_list, tournament_display)
        
        h_imp_atk = h_imp_atk_val
        h_imp_def = h_imp_def_val
        a_imp_atk = a_imp_atk_val
        a_imp_def = a_imp_def_val

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

        # 피로도에 따른 가중치 변환 (단계별 공격 -5%, 방어 +5%)
        h_fa = -5.0 * h_fatigue_stage
        h_fd = 5.0 * h_fatigue_stage
        a_fa = -5.0 * a_fatigue_stage
        a_fd = 5.0 * a_fatigue_stage

        # 4. 규칙 3번 최종 토탈 합산 (홈/원정 변수명 대칭 일치 100% 검증 완료)
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
        # 🟢 [5단계] 5-1(최종 보정 및 1차 기대치) & 5-2(실전 7경기) 완전 정비 통합 연산 블록
        # ======================================================================
        
        # 1. 1단계 최종 보정 평균 득실을 5단계 베이스 득실로 확실하게 매핑
        h_base_g = float(h_gpg) if 'h_gpg' in locals() and h_gpg > 0 else 1.2
        h_base_c = float(h_cpg) if 'h_cpg' in locals() and h_cpg > 0 else 1.1
        a_base_g = float(a_gpg) if 'a_gpg' in locals() and a_gpg > 0 else 1.1
        a_base_c = float(a_cpg) if 'a_cpg' in locals() and a_cpg > 0 else 1.2

        # 2. 0단계(country.json) 가중치 안전 확보 (없을 시 0% 방어)
        h_step0_atk = parse_pct(h_atk_bonus_str) if 'h_atk_bonus_str' in locals() else 0.0
        h_step0_def = parse_pct(h_def_bonus_str) if 'h_def_bonus_str' in locals() else 0.0
        a_step0_atk = parse_pct(a_atk_bonus_str) if 'a_atk_bonus_str' in locals() else 0.0
        a_step0_def = parse_pct(a_def_bonus_str) if 'a_def_bonus_str' in locals() else 0.0

        # 3. 5-1 파트: 모든 규칙 보정치 누적 합산 및 1차 기본 기대 득실점 산출
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
        # [5-2 파트] 동급 티어 실전 7경기 교차 검증 및 보정 후 실전 평균 산출
        # --------------------------------------------------------------------------
        h_opp_at = s_a_at if 's_a_at' in locals() else "Tier C"
        h_opp_de = s_a_de if 's_a_de' in locals() else "Tier C"
        a_opp_at = s_h_at if 's_h_at' in locals() else "Tier C"
        a_opp_de = s_h_de if 's_h_de' in locals() else "Tier C"

        home_merged_pool = list(s_home_matches or []) + list(h_matches or [])
        away_merged_pool = list(s_away_matches or []) + list(a_matches or [])

        def engine_filter_matched_tier_games(match_list, target_at_name, target_de_name):
            if not match_list or not isinstance(match_list, list): return []
            tier_score_map = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
            t_at_val = tier_score_map.get(target_at_name, 3)
            t_de_val = tier_score_map.get(target_de_name, 3)
            scored_pool = []
            for m in match_list:
                if not isinstance(m, dict): continue
                tier_info = m.get("opponent_tier_info", "")
                oa, od = 1.3, 1.2
                if tier_info:
                    try:
                        atk_match = re.search(r'공격([A-E])\(([\d\.]+)\)', tier_info)
                        def_match = re.search(r'방어([A-E])\(([\d\.]+)\)', tier_info)
                        if atk_match: oa = float(atk_match.group(2))
                        if def_match: od = float(def_match.group(2))
                    except: pass
                op_at_name = atk_tier_nm(oa) if 'atk_tier_nm' in globals() else "Tier C"
                op_de_name = def_tier_nm(od) if 'def_tier_nm' in globals() else "Tier C"
                match_score = abs(t_at_val - tier_score_map.get(op_at_name, 3)) + abs(t_de_val - tier_score_map.get(op_de_name, 3))
                scored_pool.append((match_score, m))
            scored_pool.sort(key=lambda x: x[0])
            sorted_matches = [item[1] for item in scored_pool[:7]]
            try: sorted_matches.sort(key=lambda x: str(x.get("match_time", "")), reverse=True)
            except: pass
            return sorted_matches

        home_matched_7 = engine_filter_matched_tier_games(home_merged_pool, h_opp_at, h_opp_de)
        away_matched_7 = engine_filter_matched_tier_games(away_merged_pool, a_opp_at, a_opp_de)

        def engine_compute_52_real_avg(match_list, team_label, my_corrected_at, my_corrected_de):
            if not match_list: return 0.0, 0.0
            tot_gf_app, tot_ga_app = 0.0, 0.0
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
                
                oa, od = 1.3, 1.2
                tier_info = m.get("opponent_tier_info", "")
                at_name, df_name = "Tier C", "Tier C"
                if tier_info:
                    try:
                        atk_match = re.search(r'공격([A-E])\(([\d\.]+)\)', tier_info)
                        def_match = re.search(r'방어([A-E])\(([\d\.]+)\)', tier_info)
                        if atk_match: at_name = f"Tier {atk_match.group(1)}"
                        if def_match: df_name = f"Tier {def_match.group(1)}"
                    except: pass

                mult_gf = mult_ga = 1.0
                if my_corrected_at in ["Tier A", "Tier E"]:
                    if my_corrected_at == "Tier A" and df_name == "Tier E": mult_gf = 0.5
                    elif my_corrected_at == "Tier E" and df_name == "Tier A": mult_gf = 1.5
                if my_corrected_de in ["Tier A", "Tier E"]:
                    if my_corrected_de == "Tier A" and at_name == "Tier E": mult_ga = 1.5
                    elif my_corrected_de == "Tier E" and at_name == "Tier A": mult_ga = 0.5

                tot_gf_app += (float(gf) * mult_gf)
                tot_ga_app += (float(ga) * mult_ga)

            app_agf = tot_gf_app / cnt if cnt > 0 else 0.0
            app_aga = tot_ga_app / cnt if cnt > 0 else 0.0
            return app_agf, app_aga

        home_my_at = s_h_at if 's_h_at' in locals() else "Tier C"
        home_my_de = s_h_de if 's_h_de' in locals() else "Tier C"
        away_my_at = s_a_at if 's_a_at' in locals() else "Tier C"
        away_my_de = s_a_de if 's_a_de' in locals() else "Tier C"

        h_app_agf, h_app_aga = engine_compute_52_real_avg(home_matched_7, home_name, home_my_at, home_my_de)
        a_app_agf, a_app_aga = engine_compute_52_real_avg(away_matched_7, away_name, away_my_at, away_my_de)
        
        h_agf = h_app_agf if h_app_agf > 0 else h_final_exp_g
        h_aga = h_app_aga if h_app_aga > 0 else h_final_exp_c
        a_agf = a_app_agf if a_app_agf > 0 else a_final_exp_g
        a_aga = a_app_aga if a_app_aga > 0 else a_final_exp_c

        # --------------------------------------------------------------------------
        # [최종 람다 결합 파트] 다득점 Over Factor 및 5-1/5-2 최종 융합
        # --------------------------------------------------------------------------
        tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
        h_tier_val = tier_ranks.get(home_my_at, 3)
        a_tier_val = tier_ranks.get(away_my_at, 3)
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
        # 🟢 [6단계] 푸아송 분포 및 승무패/스코어 최종 확률 도출 (안전 방어 장치 적용)
        # ======================================================================
        def poisson_prob(lmbda, k):
            if lmbda <= 0 and k == 0: return 1.0
            try: return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
            except: return 0.0

        # 안전 변수 매핑 방어
        _h_exp_g = h_final_exp_g if 'h_final_exp_g' in locals() else 1.2
        _a_exp_g = a_final_exp_g if 'a_final_exp_g' in locals() else 1.1
        _h_final = h_final if 'h_final' in locals() else _h_exp_g
        _a_final = a_final if 'a_final' in locals() else _a_exp_g
        
        _tot_exp = _h_exp_g + _a_exp_g
        _h_agf = h_agf if 'h_agf' in locals() else _h_exp_g
        _a_agf = a_agf if 'a_agf' in locals() else _a_exp_g
        _h_over = h_over_factor if 'h_over_factor' in locals() else 0.0
        _a_over = a_over_factor if 'a_over_factor' in locals() else 0.0

        if _tot_exp < 2.2:
            matrix_max_k = 3
            poisson_zone_name = "저득점 통제 구역 (total < 2.2)"
            matrix_range = "0 ~ 3골 범위 (4×4 행렬)"
        elif _tot_exp <= 3.2:
            matrix_max_k = 4
            poisson_zone_name = "표준 득점 구역 (2.2 ~ 3.2)"
            matrix_range = "0 ~ 4골 범위 (5×5 행렬 - 기본)"
        else:
            matrix_max_k = 6
            poisson_zone_name = "다득점 변동 구역 (total > 3.2)"
            matrix_range = "0 ~ 6골 / 0 ~ 7골 동적 확장 행렬"

        win_loss_probs = []
        score_probs = []
        for h_g in range(matrix_max_k + 1):
            for a_g in range(matrix_max_k + 1):
                p_h = poisson_prob(_h_exp_g, h_g)
                p_a = poisson_prob(_a_exp_g, a_g)
                win_loss_probs.append({"home_score": h_g, "away_score": a_g, "prob": p_h * p_a})

                p_h2 = poisson_prob(_h_final, h_g)
                p_a2 = poisson_prob(_a_final, a_g)
                score_probs.append({"home_score": h_g, "away_score": a_g, "prob": p_h2 * p_a2})

        calc_home_win = sum(item["prob"] for item in win_loss_probs if item["home_score"] > item["away_score"]) * 100
        calc_away_win = sum(item["prob"] for item in win_loss_probs if item["home_score"] < item["away_score"]) * 100
        calc_draw = sum(item["prob"] for item in win_loss_probs if item["home_score"] == item["away_score"]) * 100

        scored_candidates = []
        for item in score_probs:
            hg, ag, prob = item["home_score"], item["away_score"], item["prob"]
            fitness_score = (abs(hg - _h_agf) + abs(ag - _a_agf)) - (prob * 3.0)
            scored_candidates.append({"home_score": hg, "away_score": ag, "prob": prob, "fitness": fitness_score})

        sorted_by_fitness = sorted(scored_candidates, key=lambda x: x["fitness"])
        best_match_52 = sorted_by_fitness[0] if sorted_by_fitness else {"home_score": 1, "away_score": 1, "prob": 0.1}

        sorted_by_prob = sorted(score_probs, key=lambda x: x["prob"], reverse=True)
        second_match = next((s for s in sorted_by_prob if not (s["home_score"] == best_match_52["home_score"] and s["away_score"] == best_match_52["away_score"])), sorted_by_prob[1] if len(sorted_by_prob) > 1 else best_match_52)

        diff_probs = {}
        for item in score_probs:
            diff = item["home_score"] - item["away_score"]
            diff_probs[diff] = diff_probs.get(diff, 0.0) + item["prob"]

        sorted_diffs = sorted(diff_probs.items(), key=lambda x: x[1], reverse=True)
        top_diff_item = sorted_diffs[0] if sorted_diffs else (0, 0.1)
        d_val, d_prob_val = top_diff_item[0], top_diff_item[1] * 100

        _home_n = home_name if 'home_name' in locals() else "홈팀"
        _away_n = away_name if 'away_name' in locals() else "원정팀"

        if d_val > 0: s3_name = f"{_home_n} {d_val}점차 승리"
        elif d_val < 0: s3_name = f"{_away_n} {abs(d_val)}점차 승리"
        else: s3_name = "무승부 공방"
        s3_desc = f"{s3_name} ({d_prob_val:.1f}%)"

        calc_basis_parts = []
        for diff_key, p_val in sorted_diffs[1:3]:
            pct = p_val * 100
            p_name = f"{_home_n} {diff_key}점차승" if diff_key > 0 else (f"{_away_n} {abs(diff_key)}점차승" if diff_key < 0 else "무승부")
            calc_basis_parts.append(f"{p_name} ({pct:.1f}%)")
        s3_calc_basis = ", ".join(calc_basis_parts) if calc_basis_parts else "기타 점수차 구도 분산"

        over_factor_desc = f"홈 +{int(_h_over * 100)}% / 원정 +{int(_a_over * 100)}% 가산 반영"

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

            # 💡 5-1표 1차기본기대 득실점 및 5-2표 실전 평균 명시적 리턴 바인딩
            "h_final_exp_g": h_final_exp_g if 'h_final_exp_g' in locals() else 0.0,
            "h_final_exp_c": h_final_exp_c if 'h_final_exp_c' in locals() else 0.0,
            "a_final_exp_g": a_final_exp_g if 'a_final_exp_g' in locals() else 0.0,
            "a_final_exp_c": a_final_exp_c if 'a_final_exp_c' in locals() else 0.0,
            
            "h_agf": h_agf if 'h_agf' in locals() else 0.0,
            "h_aga": h_aga if 'h_aga' in locals() else 0.0,
            "a_agf": a_agf if 'a_agf' in locals() else 0.0,
            "a_aga": a_aga if 'a_aga' in locals() else 0.0,

            "h_gpg": h_base_g if 'h_base_g' in locals() else 0.0,
            "h_cpg": h_base_c if 'h_base_c' in locals() else 0.0,
            "a_gpg": a_base_g if 'a_base_g' in locals() else 0.0,
            "a_cpg": a_base_c if 'a_base_c' in locals() else 0.0,

            "h_step0_atk": h_step0_atk if 'h_step0_atk' in locals() else 0.0, 
            "h_step0_def": h_step0_def if 'h_step0_def' in locals() else 0.0,
            "h_r1_atk": h_r1_atk if 'h_r1_atk' in locals() else 0.0, 
            "h_r1_def": h_r1_def if 'h_r1_def' in locals() else 0.0,
            "h_r2_atk": h_r2_atk if 'h_r2_atk' in locals() else 0.0, 
            "h_r2_def": h_r2_def if 'h_r2_def' in locals() else 0.0,
            "h_r31_atk": h_r31_atk if 'h_r31_atk' in locals() else 0.0, 
            "h_r31_def": h_r31_def if 'h_r31_def' in locals() else 0.0,
            "h_imp_atk": h_imp_atk_val if 'h_imp_atk_val' in locals() else 0.0, 
            "h_imp_def": h_imp_def_val if 'h_imp_def_val' in locals() else 0.0,
            "h_fa": h_fa if 'h_fa' in locals() else 0.0, 
            "h_fd": h_fd if 'h_fd' in locals() else 0.0,
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
            "a_r31_atk": a_r31_atk if 'a_r31_atk' in locals() else 0.0, 
            "a_r31_def": a_r31_def if 'a_r31_def' in locals() else 0.0,
            "a_imp_atk": a_imp_atk_val if 'a_imp_atk_val' in locals() else 0.0, 
            "a_imp_def": a_imp_def_val if 'a_imp_def_val' in locals() else 0.0,
            "a_fa": a_fa if 'a_fa' in locals() else 0.0, 
            "a_fd": a_fd if 'a_fd' in locals() else 0.0,
            "a_r3_tot_atk": a_r3_tot_atk if 'a_r3_tot_atk' in locals() else 0.0, 
            "a_r3_tot_def": a_r3_tot_def if 'a_r3_tot_def' in locals() else 0.0,
            "a_r4_atk": a_r4_atk if 'a_r4_atk' in locals() else 0.0, 
            "a_r4_def": a_r4_def if 'a_r4_def' in locals() else 0.0,
            "a_tot_atk_pct": a_tot_atk_pct if 'a_tot_atk_pct' in locals() else 0.0, 
            "a_tot_def_pct": a_tot_def_pct if 'a_tot_def_pct' in locals() else 0.0
        }

    except Exception as e:
        print(f"[Engine Master Critical Error]: {e}")
        return {"status": False, "msg": str(e)}
