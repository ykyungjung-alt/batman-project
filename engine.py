import math
import re

def compute_match_prediction_master(target_detail, home_name, away_name, country_data=None):
    """
    [배트맨 프로젝트 순수 계산 엔진]
    - 화면 렌더링(Streamlit) 없이 오직 0~6단계 정량 수치 연산 및 푸아송 예측만 수행
    - 7단계 멀티 대시보드 및 단일 분석에서 공용으로 호출 가능
    """
    if not target_detail or not isinstance(target_detail, dict):
        return {"status": False, "msg": "상세 정량 데이터 없음"}

    try:
        # 1. 1단계 기본 기대치 (LIFO 득실)
        h_sum = target_detail.get("meta_details", {}).get("recent_form", {}).get("home_summary", {})
        a_sum = target_detail.get("meta_details", {}).get("recent_form", {}).get("away_summary", {})
        
        h_base_g = float(target_detail.get("h_gpg", h_sum.get("goals_per_game", 1.2)))
        h_base_c = float(target_detail.get("h_cpg", h_sum.get("conceded_per_game", 1.1)))
        a_base_g = float(target_detail.get("a_gpg", a_sum.get("goals_per_game", 1.1)))
        a_base_c = float(target_detail.get("a_cpg", a_sum.get("conceded_per_game", 1.2)))

        # 2. 누적 보정치 추출 (v3/상세 데이터 내부에 산출된 값 또는 기본값)
        h_tot_atk_pct = float(target_detail.get("h_tot_atk_pct", 0.0))
        h_tot_def_pct = float(target_detail.get("h_tot_def_pct", 0.0))
        a_tot_atk_pct = float(target_detail.get("a_tot_atk_pct", 0.0))
        a_tot_def_pct = float(target_detail.get("a_tot_def_pct", 0.0))

        # 실전 평균 득실 (5-2 검증용)
        h_agf = float(target_detail.get("h_agf", h_base_g))
        a_agf = float(target_detail.get("a_agf", a_base_g))

        # 티어 정보
        h_current_at = target_detail.get("h_current_at", "Tier C")
        a_current_at = target_detail.get("a_current_at", "Tier C")

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
