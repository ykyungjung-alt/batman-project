import math
import os
import json
import re

# --------------------------------------------------------------------------
# 🛠️ [공통 유틸리티] 퍼센트 파싱 및 country.json 로드
# --------------------------------------------------------------------------
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

def load_country_data_for_engine():
    if os.path.exists("country.json"):
        try:
            with open("country.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def resolve_country_and_grade(rank_val, team_val, current_league_name="", country_data=None):
    """[0단계] country.json 기반 등급 및 공수 보정치 정밀 대조 (정보 없을 시 F등급 / 0% 방어)"""
    if not country_data:
        country_data = load_country_data_for_engine()
        
    grades = country_data.get("grades", {})
    rank_str = str(rank_val).strip()
    team_str = str(team_val).strip().lower()
    clean_league = str(current_league_name).strip().replace(" ", "").lower()

    extracted_code = ""
    if rank_str and rank_str != "-":
        token = re.split(r'[\s\-]+', rank_str)[0].strip().upper()
        if token:
            extracted_code = token

    for grade_key, countries in grades.items():
        if grade_key == "F":
            continue
        if isinstance(countries, list):
            for c in countries:
                c_name = str(c.get("name", "")).strip().lower()
                c_code = str(c.get("code", "")).strip().upper()
                kor_league = str(c.get("league_kor_name", "")).strip().replace(" ", "").lower()
                leagues_list = [str(l).lower() for l in c.get("leagues", [])]

                match_by_code = c_code and (c_code == extracted_code or c_code in rank_str.upper())
                match_by_name = c_name and (c_name in team_str or c_name in clean_league)
                match_by_kor_league = kor_league and (kor_league in clean_league or clean_league in kor_league)
                match_by_eng_league = any(l.split()[0] in clean_league for l in leagues_list if l)

                if match_by_code or match_by_name or match_by_kor_league or match_by_eng_league:
                    return c.get("grade", "E"), parse_pct(c.get("attack_bonus", "+3%")), parse_pct(c.get("defense_bonus", "-3%"))

    return "F", 0.0, 0.0


# --------------------------------------------------------------------------
# ⚽ [공통 티어 및 특수 룰 유틸리티] (규칙 1, 2, 5-2 공통 적용)
# --------------------------------------------------------------------------
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
    """E티어 상대전 50% 할인 특수 룰 발동 선행 판정"""
    at_nm, _ = get_atk_tier(base_gpg)
    df_nm, _ = get_def_tier(base_cpg)
    if not matches:
        return at_nm == "Tier A" or df_nm == "Tier E"
    
    raw_s, raw_c = 0.0, 0.0
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
    tmp_gpg = raw_s / cnt if cnt > 0 else base_gpg
    tmp_cpg = raw_c / cnt if cnt > 0 else base_cpg
    
    at_nm_tmp, _ = get_atk_tier(tmp_gpg)
    df_nm_tmp, _ = get_def_tier(tmp_cpg)
    return (at_nm_tmp == "Tier A") or (df_nm_tmp == "Tier E")

def compute_adjusted_stats_with_discount(matches, tname, base_gpg, base_cpg, is_triggered=False):
    """LIFO 경기 풀 또는 구장별 경기 풀을 받아 E티어 상대전 50% 할인 적용 보정 평균 산출"""
    if not matches:
        return base_gpg, base_cpg
        
    eff_scored = 0.0
    eff_conceded = 0.0
    
    for m in matches:
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
            
        mult = 1.0
        tier_info = m.get("opponent_tier_info", "")
        if tier_info and "/" in tier_info:
            try:
                oa, od = map(float, tier_info.split("/"))
                at_name, _ = get_atk_tier(oa)
                df_name, _ = get_def_tier(od)
                if is_triggered and (at_name == "Tier E" or df_name == "Tier E"):
                    mult = 0.5
            except:
                pass
                
        eff_scored += (sc * mult)
        eff_conceded += (cc * mult)
        
    cnt = len(matches)
    gpg = round(eff_scored / cnt, 2) if cnt > 0 else base_gpg
    cpg = round(eff_conceded / cnt, 2) if cnt > 0 else base_cpg
    return gpg, cpg


# --------------------------------------------------------------------------
# 🚀 [마스터 계산 엔진] 순수 백엔드 정량 연산 함수 (0~6단계 통합)
# --------------------------------------------------------------------------
def compute_match_prediction_master(target_detail, home_name, away_name, league_name=""):
    if not target_detail or not isinstance(target_detail, dict):
        return {"status": False, "msg": "상세 정량 데이터 없음"}

    try:
        meta_details = target_detail.get("meta_details", {})
        rankings_raw = meta_details.get("rankings", [])
        
        # [0단계] country.json 등급 및 공수 보정치 추출
        h_step0_atk, h_step0_def = 0.0, 0.0
        a_step0_atk, a_step0_def = 0.0, 0.0
        
        clean_home_target = str(home_name).strip().replace(" ", "")
        clean_away_target = str(away_name).strip().replace(" ", "")
        
        if rankings_raw:
            for r in rankings_raw:
                r_team = str(r.get("team", "-"))
                r_code = str(r.get("rank", ""))
                grade, atk_val, def_val = resolve_country_and_grade(r_code, r_team, league_name)
                
                clean_row_team = r_team.strip().replace(" ", "")
                if clean_home_target in clean_row_team or clean_row_team in clean_home_target:
                    h_step0_atk, h_step0_def = atk_val, def_val
                elif clean_away_target in clean_row_team or clean_row_team in clean_away_target:
                    a_step0_atk, a_step0_def = atk_val, def_val

        # [규칙 1번] 최근 경기(LIFO) 풀 안전 추출 및 E티어 할인 룰 적용
        recent_form = meta_details.get("recent_form", {})
        h_matches = recent_form.get("home_matches", [])
        a_matches = recent_form.get("away_matches", [])

        h_sum = recent_form.get("home_summary", {})
        a_sum = recent_form.get("away_summary", {})
        
        h_gpg_base = float(target_detail.get("h_gpg", h_sum.get("goals_per_game", 1.2)))
        h_cpg_base = float(target_detail.get("h_cpg", h_sum.get("conceded_per_game", 1.1)))
        a_gpg_base = float(target_detail.get("a_gpg", a_sum.get("goals_per_game", 1.1)))
        a_cpg_base = float(target_detail.get("a_cpg", a_sum.get("conceded_per_game", 1.2)))

        h_is_triggered = check_special_rule_trigger(h_matches, home_name, h_gpg_base, h_cpg_base)
        a_is_triggered = check_special_rule_trigger(a_matches, away_name, a_gpg_base, a_cpg_base)

        h_base_g, h_base_c = compute_adjusted_stats_with_discount(h_matches, home_name, h_gpg_base, h_cpg_base, h_is_triggered)
        a_base_g, a_base_c = compute_adjusted_stats_with_discount(a_matches, away_name, a_gpg_base, a_cpg_base, a_is_triggered)

        base_h_at, h_r1_atk = get_atk_tier(h_base_g)
        base_h_de, h_r1_def = get_def_tier(h_base_c)
        base_a_at, a_r1_atk = get_atk_tier(a_base_g)
        base_a_de, a_r1_def = get_def_tier(a_base_c)

# [규칙 2번] 구장별(Stadium Form) Shift 보정 연산 (기본 3번 및 기존 규격 단독 연동)
        head_info = target_detail.get("head_info", {})
        venue_val = str(head_info.get("stadium", ""))
        home_stadium_val = str(head_info.get("home_stadium", ""))
        
        is_neutral_venue = False
        if venue_val and home_stadium_val and home_stadium_val != "-":
            if venue_val.strip().lower() != home_stadium_val.strip().lower():
                is_neutral_venue = True

        # 메타 데이터에서 stadium_form 안전하게 가져오기
        stadium_form = target_detail.get("meta_details", {}).get("stadium_form", {"home_matches": [], "away_matches": []})

        # 1. 홈팀 전적 추출
        s_home_matches = []
        if is_neutral_venue:
            recent_all_pool = stadium_form.get("recent_matches", []) if "recent_matches" in stadium_form else []
            if not recent_all_pool and 'h_matches' in locals():
                recent_all_pool = h_matches

            neutral_home_away_matches = []
            for m in recent_all_pool:
                teams_str = str(m.get("teams", ""))
                if " vs " in teams_str:
                    t_parts = [p.strip() for p in teams_str.split("vs")]
                    if len(t_parts) >= 2 and home_name not in t_parts[0]:
                        neutral_home_away_matches.append(m)
                elif m.get("location") == "원정" or m.get("venue_type") == "away":
                    neutral_home_away_matches.append(m)
            
            if not neutral_home_away_matches:
                neutral_home_away_matches = stadium_form.get("away_matches", [])

            s_home_matches = neutral_home_away_matches[:10]
        else:
            s_home_matches = stadium_form.get("home_matches", [])[:10]

        # 2. 원정팀 전적 추출
        s_away_matches = stadium_form.get("away_matches", [])[:10]

        if not s_home_matches and 'h_matches' in locals(): s_home_matches = h_matches[:10]
        if not s_away_matches and 'a_matches' in locals(): s_away_matches = a_matches[:10]

        s_h_g, s_h_c = compute_adjusted_stats_with_discount(s_home_matches, home_name, h_base_g, h_base_c, h_is_triggered)
        s_a_g, s_a_c = compute_adjusted_stats_with_discount(s_away_matches, away_name, a_base_g, a_base_c, a_is_triggered)
        
        s_h_at, _ = get_atk_tier(s_h_g)
        s_h_de, _ = get_def_tier(s_h_c)
        s_a_at, _ = get_atk_tier(s_a_g)
        s_a_de, _ = get_def_tier(s_a_c)

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
   
        
        # [규칙 3번] 선수 전력 누수(3-1) 및 일정 중요도·피로도(3-2) 화면 연동 일치화
        h_squad_changes = meta_details.get("home_squad_changes", [])
        a_squad_changes = meta_details.get("away_squad_changes", [])

        def calc_squad_weights(changes_list):
            if not changes_list or not isinstance(changes_list, list):
                return 0.0, 0.0
            tot_atk, tot_def = 0.0, 0.0
            for item in changes_list:
                p_pos = str(item.get("position", "-"))
                p_type = str(item.get("type", "누수"))
                p_grade = str(item.get("grade", "중 (Medium)"))
                rate = 14.0 if "상" in p_grade else (7.0 if "중" in p_grade else 0.0)
                if "누수" in p_type:
                    atk_v = -rate
                    def_v = rate if ("FW" in p_pos or "MF" in p_pos) else rate / 2.0
                else:
                    atk_v = rate
                    def_v = -rate if ("DF" in p_pos or "GK" in p_pos) else -rate / 2.0
                tot_atk += atk_v
                tot_def += def_v
            return tot_atk, tot_def

        h_r31_atk, h_r31_def = calc_squad_weights(h_squad_changes)
        a_r31_atk, a_r31_def = calc_squad_weights(a_squad_changes)

        # 💡 [핵심 연동] 화면(tabs[3])과 동일하게 룰 기반 중요도 가중치 추출 (target_detail에 사전 계산값이 없으면 직접 판정)
        h_imp_atk = float(target_detail.get("h_imp_atk", 5.0))
        h_imp_def = float(target_detail.get("h_imp_def", -5.0))
        a_imp_atk = float(target_detail.get("a_imp_atk", 5.0))
        a_imp_def = float(target_detail.get("a_imp_def", -5.0))

        # 만약 target_detail에 뷰어용 중요도 값이 명시되어 있지 않다면 메타의 순위표 태그 기반으로 보정치 재산정
        home_tag = str(target_detail.get("home_tag_label", ""))
        away_tag = str(target_detail.get("away_tag_label", ""))

        def get_importance_weights(tag_str):
            if any(k in tag_str for k in ["탈락", "탈락확정", "강등확정"]):
                return -10.0, 10.0
            elif any(k in tag_str for k in ["진출권", "플레이오프", "승격", "우승", "qualifying", "play-offs", "Playoff"]):
                return 15.0, -15.0
            return 5.0, -5.0

        if home_tag:
            _, h_imp_atk, h_imp_def = ("커스텀",) + get_importance_weights(home_tag)
        if away_tag:
            _, a_imp_atk, a_imp_def = ("커스텀",) + get_importance_weights(away_tag)

        # 이동 피로도 단계 가중치 연동 (단계당 공격 -5%, 방어 +5%)
        h_fatigue_stage = int(target_detail.get("h_fatigue_stage", 0))
        a_fatigue_stage = int(target_detail.get("a_fatigue_stage", 0))

        h_r32_atk = (-5.0 * h_fatigue_stage)
        h_r32_def = (5.0 * h_fatigue_stage)
        a_r32_atk = (-5.0 * a_fatigue_stage)
        a_r32_def = (5.0 * a_fatigue_stage)

        # 규칙 3번 최종 통합 합산
        h_r3_tot_atk = h_r31_atk + h_imp_atk + h_r32_atk
        h_r3_tot_def = h_r31_def + h_imp_def + h_r32_def
        a_r3_tot_atk = a_r31_atk + a_imp_atk + a_r32_atk
        a_r3_tot_def = a_r31_def + a_imp_def + a_r32_def

        # [규칙 4번] 맞대결 H2H 상성 및 단방향 10% 룰
        h2h_info = meta_details.get("h2h", {})
        h2h_matches = h2h_info.get("matches", [])
        home_wins = 0
        away_wins = 0
        total_games = len(h2h_matches) if isinstance(h2h_matches, list) else 0

        if total_games > 0:
            for m in h2h_matches:
                row_cols = m.get("row_data", [])
                if len(row_cols) >= 4:
                    h_team_name = row_cols[1]
                    score_str = row_cols[2]
                    try:
                        scores = score_str.replace("：", "-").split("-")
                        h_score = int(scores[0].strip())
                        a_score = int(scores[1].strip())
                        if h_team_name == home_name:
                            if h_score > a_score: home_wins += 1
                            elif h_score < a_score: away_wins += 1
                        else:
                            if h_score > a_score: away_wins += 1
                            elif h_score < a_score: home_wins += 1
                    except:
                        pass

        home_win_rate = (home_wins / total_games * 100) if total_games > 0 else 0.0
        away_win_rate = (away_wins / total_games * 100) if total_games > 0 else 0.0

        h_r4_atk, h_r4_def = 0.0, 0.0
        a_r4_atk, a_r4_def = 0.0, 0.0

        if total_games >= 5:
            if home_win_rate >= 50.0:
                h_r4_atk, h_r4_def = 10.0, -10.0
            elif away_win_rate >= 50.0:
                a_r4_atk, a_r4_def = 10.0, -10.0

# ==============================================================================
        # 🎯 [0~5단계 통합 누적 합산 규격] 공격력 및 방어력 보정치 전 단계 완벽 결속
        # ==============================================================================
        h_tot_atk_pct = h_step0_atk + h_r1_atk + h_r2_atk + h_r3_tot_atk + h_r4_atk
        h_tot_def_pct = h_step0_def + h_r1_def + h_r2_def + h_r3_tot_def + h_r4_def  # 👈 방어력 누락분 완전 결속

        a_tot_atk_pct = a_step0_atk + a_r1_atk + a_r2_atk + a_r3_tot_atk + a_r4_atk
        a_tot_def_pct = a_step0_def + a_r1_def + a_r2_def + a_r3_tot_def + a_r4_def  # 👈 방어력 누락분 완전 결속

        # 💡 [규칙 5-2 연동] 대시보드 5-2 표의 실전 평균 득실 데이터를 엔진 내부에 안전하게 수용
        h_agf = float(target_detail.get("h_agf", h_base_g))
        a_agf = float(target_detail.get("a_agf", a_base_g))
        
        # [규칙 5번] 최종 보정 및 1차 기본 기대 득실점 산출 (단일 화면과 완벽 동기화)
        h_max_g = h_base_g * (1 + h_tot_atk_pct / 100.0)
        h_min_c = h_base_c * (1 + h_tot_def_pct / 100.0)
        a_max_g = a_base_g * (1 + a_tot_atk_pct / 100.0)
        a_min_c = a_base_c * (1 + a_tot_def_pct / 100.0)

        h_final_exp_g = max(0.2, (h_max_g + (2.0 - a_min_c)) / 2.0)
        h_final_exp_c = max(0.2, (h_min_c + (2.0 - a_max_g)) / 2.0)
        a_final_exp_g = max(0.2, (a_max_g + (2.0 - h_min_c)) / 2.0)
        a_final_exp_c = max(0.2, (a_min_c + (2.0 - h_max_g)) / 2.0)

        h_tier_val = tier_ranks.get(base_h_at, 3)
        a_tier_val = tier_ranks.get(base_a_at, 3)
        tier_diff = abs(h_tier_val - a_tier_val)

        # 5-3 오버 팩터(Over Factor) 변동성 보정 반영
        h_over_factor = 0.0
        a_over_factor = 0.0

        if tier_diff >= 2:
            add_rate = 0.10 + (tier_diff - 2) * 0.10
            if h_tier_val > a_tier_val: 
                h_over_factor = add_rate
            else: 
                a_over_factor = add_rate
        elif (h_final_exp_g + a_final_exp_g > 3.2) or (h_final_exp_c >= 1.50 or a_final_exp_c >= 1.50):
            h_over_factor = 0.15
            a_over_factor = 0.15

        # 💡 최종 람다 산정 시 5-2 실전 평균(h_agf, a_agf)과 오버 팩터 정밀 결합
        h_final = max(0.2, ((h_final_exp_g * (1 + h_over_factor)) + h_agf) / 2.0)
        a_final = max(0.2, ((a_final_exp_g * (1 + a_over_factor)) + a_agf) / 2.0)
        total_expected_goals = h_final + a_final

# --------------------------------------------------------------------------
        # 🧮 [규칙 6] 푸아송 분포 및 승무패 확률 / 예측 순위 정밀 연산 블록 (안전 완벽 방어 버전)
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

        # [1순위] 규칙 5-2 결과에 가장 적합한 결과값 최우선 선정
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

        # [3순위] 각 점수 차이별 확률 합산 후 가장 많이 차지한 점수 차이 구도
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

    except Exception as e:
        return {"status": False, "msg": str(e)}
