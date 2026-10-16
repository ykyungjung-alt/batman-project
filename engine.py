import math
import os
import json
import re

def parse_pct(val_str):
    """퍼센트 문자열 및 숫자를 안전한 float 가중치 값으로 변환"""
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
    """engine 내부에서 country.json을 안전하게 로드"""
    if os.path.exists("country.json"):
        try:
            with open("country.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def resolve_country_and_grade(rank_val, team_val, current_league_name="", country_data=None):
    """
    [0단계 핵심 연동] 순위표 정보(리그순위 코드, 팀명, 리그명)를 바탕으로 
    country.json에서 국가 코드, 등급 및 공수 보정치를 정밀 대조·추출하는 함수
    (데이터 없거나 매칭 실패 시 F등급 / 0% 안전장치 적용)
    """
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

    # 안전장치: 매칭 실패 또는 F등급일 경우 가중치 무조건 0% 고정
    return "F", 0.0, 0.0

# --------------------------------------------------------------------------
# 💡 [규칙 1번 전용 보조 함수] 티어 산정 및 E티어 득실점 50% 할인 특수 룰 연동
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

def check_rule1_trigger(matches, tname, base_gpg, base_cpg):
    """규칙 1번 특수 룰(E티어 득실점 50% 할인) 발동 여부 선행 판정"""
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

def process_rule1_lifo_stats(matches, tname, base_gpg, base_cpg, is_triggered=False):
    """LIFO 10경기 전수 조사 및 E티어 상대 득실점 50% 할인(0.5배) 반영 보정 평균 산출"""
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


def compute_match_prediction_master(target_detail, home_name, away_name, league_name=""):
    """
    [배트맨 프로젝트 순수 마스터 계산 엔진]
    - 0단계(country.json 등급 가중치) + 규칙 1(LIFO 10경기 및 E티어 50% 할인) 연동
    - 1~4단계 보정 및 5~6단계 푸아송 예측까지 완벽 통합 수행
    """
    if not target_detail or not isinstance(target_detail, dict):
        return {"status": False, "msg": "상세 정량 데이터 없음"}

    try:
        # 0. 0단계 등급 및 공수 가중치 추출 (rankings 데이터 활용)
        meta_details = target_detail.get("meta_details", {})
        rankings_raw = meta_details.get("rankings", [])
        
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

        # 1. 규칙 1번 (LIFO 10경기 전수 조사 및 E티어 득실점 50% 할인 룰 적용)
        recent_form = meta_details.get("recent_form", {})
        h_matches = recent_form.get("home_matches", [])
        a_matches = recent_form.get("away_matches", [])

        h_sum = recent_form.get("home_summary", {})
        a_sum = recent_form.get("away_summary", {})
        
        h_gpg_base = float(target_detail.get("h_gpg", h_sum.get("goals_per_game", 1.2)))
        h_cpg_base = float(target_detail.get("h_cpg", h_sum.get("conceded_per_game", 1.1)))
        a_gpg_base = float(target_detail.get("a_gpg", a_sum.get("goals_per_game", 1.1)))
        a_cpg_base = float(target_detail.get("a_cpg", a_sum.get("conceded_per_game", 1.2)))

        h_is_triggered = check_rule1_trigger(h_matches, home_name, h_gpg_base, h_cpg_base)
        a_is_triggered = check_rule1_trigger(a_matches, away_name, a_gpg_base, a_cpg_base)

        h_base_g, h_base_c = process_rule1_lifo_stats(h_matches, home_name, h_gpg_base, h_cpg_base, h_is_triggered)
        a_base_g, a_base_c = process_rule1_lifo_stats(a_matches, away_name, a_gpg_base, a_cpg_base, a_is_triggered)

        _, h_r1_atk = get_atk_tier(h_base_g)
        _, h_r1_def = get_def_tier(h_base_c)
        _, a_r1_atk = get_atk_tier(a_base_g)
        _, a_r1_def = get_def_tier(a_base_c)

        # 2. 누적 보정치 합산 (0단계 + 규칙 1번 가중치 + v3 내부에 산출된 후속 보정치 통합)
        h_tot_atk_pct = h_step0_atk + h_r1_atk + float(target_detail.get("h_tot_atk_pct", 0.0))
        h_tot_def_pct = h_step0_def + h_r1_def + float(target_detail.get("h_tot_def_pct", 0.0))
        a_tot_atk_pct = a_step0_atk + a_r1_atk + float(target_detail.get("a_tot_atk_pct", 0.0))
        a_tot_def_pct = a_step0_def + a_r1_def + float(target_detail.get("a_tot_def_pct", 0.0))

        # 실전 평균 득실 (5-2 검증용)
        h_agf = float(target_detail.get("h_agf", h_base_g))
        a_agf = float(target_detail.get("a_agf", a_base_g))

        # 티어 정보
        h_current_at, _ = get_atk_tier(h_base_g)
        a_current_at, _ = get_atk_tier(a_base_g)

        # 3. 5단계: 화력 한계선 및 기하평균 교차 상쇄 연산
        h_max_g = h_base_g * (1 + h_tot_atk_pct / 100.0)
        h_min_c = h_base_c * (1 + h_tot_def_pct / 100.0)
        a_max_g = a_base_g * (1 + a_tot_atk_pct / 100.0)
        a_min_c = a_base_c * (1 + a_tot_def_pct / 100.0)

        h_final_exp_g = max(0.2, (h_max_g + (2.0 - a_min_c)) / 2.0)
        h_final_exp_c = max(0.2, (h_min_c + (2.0 - a_max_g)) / 2.0)
        a_final_exp_g = max(0.2, (a_max_g + (2.0 - h_min_c)) / 2.0)
        a_final_exp_c = max(0.2, (a_min_c + (2.0 - h_max_g)) / 2.0)

        # 4. 5-3 오버팩터 (Over Factor) 산출
        tier_ranks = {"Tier A": 5, "Tier B": 4, "Tier C": 3, "Tier D": 2, "Tier E": 1}
        h_tier_val = tier_ranks.get(h_current_at, 3)
        a_tier_val = tier_ranks.get(a_current_at, 3)
        tier_diff = abs(h_tier_val - a_tier_val)

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

        h_final = h_final_exp_g * (1 + h_over_factor)
        a_final = a_final_exp_g * (1 + a_over_factor)
        total_expected_goals = h_final + a_final

        # 5. 6단계: 푸아송 분포 및 승무패 확률 / 스코어 순위 산출
        if total_expected_goals < 2.2:
            matrix_max_k = 3
        elif total_expected_goals <= 3.2 and tier_diff < 2:
            matrix_max_k = 4
        else:
            matrix_max_k = 6

        win_loss_probs = []
        for h_g in range(matrix_max_k + 1):
            for a_g in range(matrix_max_k + 1):
                p_h = (math.exp(-h_final_exp_g) * (h_final_exp_g ** h_g)) / math.factorial(h_g)
                p_a = (math.exp(-a_final_exp_g) * (a_final_exp_g ** a_g)) / math.factorial(a_g)
                win_loss_probs.append({"home_score": h_g, "away_score": a_g, "prob": p_h * p_a})

        score_probs = []
        for h_g in range(matrix_max_k + 1):
            for a_g in range(matrix_max_k + 1):
                p_h = (math.exp(-h_final) * (h_final ** h_g)) / math.factorial(h_g)
                p_a = (math.exp(-a_final) * (a_final ** a_g)) / math.factorial(a_g)
                score_probs.append({"home_score": h_g, "away_score": a_g, "prob": p_h * p_a})

        calc_home_win = sum(item["prob"] for item in win_loss_probs if item["home_score"] > item["away_score"]) * 100
        calc_away_win = sum(item["prob"] for item in win_loss_probs if item["home_score"] < item["away_score"]) * 100
        calc_draw = sum(item["prob"] for item in win_loss_probs if item["home_score"] == item["away_score"]) * 100

        # 1순위 (최적합)
        scored_candidates = []
        for item in score_probs:
            hg, ag, prob = item["home_score"], item["away_score"], item["prob"]
            v52_distance = abs(hg - h_agf) + abs(ag - a_agf)
            fitness_score = v52_distance - (prob * 3.0)
            scored_candidates.append({"home_score": hg, "away_score": ag, "prob": prob, "fitness": fitness_score})

        best_match_52 = sorted(scored_candidates, key=lambda x: x["fitness"])[0]

        # 2순위 (차선책)
        sorted_by_prob = sorted(score_probs, key=lambda x: x["prob"], reverse=True)
        second_match = next((s for s in sorted_by_prob if not (s["home_score"] == best_match_52["home_score"] and s["away_score"] == best_match_52["away_score"])), sorted_by_prob[1] if len(sorted_by_prob) > 1 else best_match_52)

        # 3순위 (대안책 - 점수차 구도)
        diff_probs = {}
        for item in score_probs:
            diff = item["home_score"] - item["away_score"]
            diff_probs[diff] = diff_probs.get(diff, 0.0) + item["prob"]
        sorted_diffs = sorted(diff_probs.items(), key=lambda x: x[1], reverse=True)
        d_val, d_prob_val = (sorted_diffs[0] if sorted_diffs else (0, 0.1))
        d_prob_pct = d_prob_val * 100

        if d_val > 0:
            s3_name = f"{home_name} {d_val}점차 승리"
        elif d_val < 0:
            s3_name = f"{away_name} {abs(d_val)}점차 승리"
        else:
            s3_name = "무승부 공방"
        s3_desc = f"{s3_name} ({d_prob_pct:.1f}%)"

        return {
            "status": True,
            "home_win_pct": calc_home_win,
            "draw_pct": calc_draw,
            "away_win_pct": calc_away_win,
            "score_1st": f"{best_match_52['home_score']} : {best_match_52['away_score']}",
            "p1_rate": best_match_52["prob"] * 100,
            "score_2nd": f"{second_match['home_score']} : {second_match['away_score']}",
            "p2_rate": second_match["prob"] * 100,
            "s3_desc": s3_desc
        }

    except Exception as e:
        return {"status": False, "msg": str(e)}
