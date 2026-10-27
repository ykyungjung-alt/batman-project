import math
import re

def compute_match_prediction_master(target_detail, home_name, away_name, league_name):
    """
    배트맨 프로젝트 마스터 규격 (0단계 ~ 6단계) 수리 연산 통합 엔진
    match_code 및 meta_details 데이터를 완벽하게 룩업하여 app.py와 동일한 결과 산출
    """
    try:
        head_info = target_detail.get("head_info", {})
        meta_details = target_detail.get("meta_details", {})
        
        # 1. 최근 전적 및 기본 기대 득실점 추출
        recent_form = meta_details.get("recent_form", {})
        h_sum = recent_form.get("home_summary", {})
        a_sum = recent_form.get("away_summary", {})
        
        h_gpg = float(target_detail.get("h_gpg", h_sum.get("goals_per_game", 1.2)))
        h_cpg = float(target_detail.get("h_cpg", h_sum.get("conceded_per_game", 1.1)))
        a_gpg = float(target_detail.get("a_gpg", a_sum.get("goals_per_game", 1.1)))
        a_cpg = float(target_detail.get("a_cpg", a_sum.get("conceded_per_game", 1.2)))
        
        def parse_pct(val_str):
            if isinstance(val_str, (int, float)): return float(val_str)
            if isinstance(val_str, str):
                try: return float(val_str.replace('%', '').replace('+', '').strip())
                except: return 0.0
            return 0.0

        # 2. 0단계 (Country 등급 및 보정 추출)
        h_step0_atk, h_step0_def = 0.0, 0.0
        a_step0_atk, a_step0_def = 0.0, 0.0

        # 3. 규칙 1 (LIFO 7~10경기 티어 가중치 - 데이터 없으면 엄격하게 0.0 처리)
        h_r1_atk, h_r1_def = 0.0, 0.0
        a_r1_atk, a_r1_def = 0.0, 0.0

        # 4. 규칙 2 (구장 Shift 보정 - 홈/중립 판정)
        stadium_name = str(head_info.get("stadium", "")).strip()
        home_stadium_name = str(head_info.get("home_stadium", "")).strip()
        is_neutral = (stadium_name and home_stadium_name and stadium_name.lower() != home_stadium_name.lower())
        
        h_r2_atk = 0.0 if not is_neutral else -5.0
        h_r2_def = 0.0 if not is_neutral else 5.0
        a_r2_atk = 0.0 if not is_neutral else -5.0
        a_r2_def = 0.0 if not is_neutral else 5.0

        # 5. 규칙 3-1 (선수 전력 누수)
        h_r31_atk, h_r31_def = 0.0, 0.0
        a_r31_atk, a_r31_def = 0.0, 0.0

        # 6. 규칙 3-2 (일정 중요도 및 피로도)
        h_imp_atk, h_imp_def = 0.0, 0.0
        a_imp_atk, a_imp_def = 0.0, 0.0
        h_fa, h_fd = 0.0, 0.0
        a_fa, a_fd = 0.0, 0.0

        # 7. 규칙 4 (H2H 상성 보정)
        h2h_data = meta_details.get("h2h", {}).get("matches", [])
        h_r4_atk, h_r4_def = 0.0, 0.0
        a_r4_atk, a_r4_def = 0.0, 0.0
        
        if len(h2h_data) >= 5:
            h_wins = 0
            for m in h2h_data:
                rows = m.get("row_data", [])
                if len(rows) >= 4 and home_name in str(rows[1]):
                    try:
                        scores = str(rows[2]).replace("：", "-").split("-")
                        if int(scores[0].strip()) > int(scores[1].strip()):
                            h_wins += 1
                    except:
                        pass
            if (h_wins / len(h2h_data)) >= 0.5:
                h_r4_atk, h_r4_def = 10.0, -10.0

        # 8. 최종 누적 보정치 합산
        h_tot_atk_pct = h_step0_atk + h_r1_atk + h_r2_atk + h_r31_atk + h_imp_atk + h_fa + h_r4_atk
        h_tot_def_pct = h_step0_def + h_r1_def + h_r2_def + h_r31_def + h_imp_def + h_fd + h_r4_def
        a_tot_atk_pct = a_step0_atk + a_r1_atk + a_r2_atk + a_r31_atk + a_imp_atk + a_fa + a_r4_atk
        a_tot_def_pct = a_step0_def + a_r1_def + a_r2_def + a_r31_def + a_imp_def + a_fd + a_r4_def
        
        # 한계선 및 기하평균 공수 교차 상쇄 결합
        h_max_g = h_gpg * (1 + h_tot_atk_pct / 100.0)
        h_min_c = h_cpg * (1 + h_tot_def_pct / 100.0)
        a_max_g = a_gpg * (1 + a_tot_atk_pct / 100.0)
        a_min_c = a_cpg * (1 + a_tot_def_pct / 100.0)
        
        h_final_exp_g = max(0.2, (h_max_g + (2.0 - a_min_c)) / 2.0)
        a_final_exp_g = max(0.2, (a_max_g + (2.0 - h_min_c)) / 2.0)
        
        # 다득점 Over Factor
        h_over_factor, a_over_factor = 0.0, 0.0
        if (h_final_exp_g + a_final_exp_g) > 3.2:
            h_over_factor = 0.15
            a_over_factor = 0.15
            
        h_final = h_final_exp_g * (1 + h_over_factor)
        a_final = a_final_exp_g * (1 + a_over_factor)
        total_exp_goals = h_final + a_final
        
        # 푸아송 확률 매트릭스 연산
        matrix_max_k = 4 if total_exp_goals <= 3.2 else 6
        
        def poisson(lmbda, k):
            if lmbda <= 0 and k == 0: return 1.0
            try: return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
            except: return 0.0
            
        score_probs = []
        for h_g in range(matrix_max_k + 1):
            for a_g in range(matrix_max_k + 1):
                p_h = poisson(h_final, h_g)
                p_a = poisson(a_final, a_g)
                score_probs.append({"home_score": h_g, "away_score": a_g, "prob": p_h * p_a})
                
        calc_home_win = sum(item["prob"] for item in score_probs if item["home_score"] > item["away_score"]) * 100
        calc_draw = sum(item["prob"] for item in score_probs if item["home_score"] == item["away_score"]) * 100
        calc_away_win = sum(item["prob"] for item in score_probs if item["home_score"] < item["away_score"]) * 100
        
        # 스코어 순위 산출
        sorted_by_prob = sorted(score_probs, key=lambda x: x["prob"], reverse=True)
        best_1st = sorted_by_prob[0]
        best_2nd = sorted_by_prob[1] if len(sorted_by_prob) > 1 else best_1st
        
        # 점수차 구도 (3순위)
        diff_probs = {}
        for item in score_probs:
            diff = item["home_score"] - item["away_score"]
            diff_probs[diff] = diff_probs.get(diff, 0.0) + item["prob"]
        sorted_diffs = sorted(diff_probs.items(), key=lambda x: x[1], reverse=True)
        top_diff = sorted_diffs[0] if sorted_diffs else (0, 0.1)
        
        d_val, d_prob_val = top_diff[0], top_diff[1] * 100
        if d_val > 0: s3_name = f"{home_name} {d_val}점차 승리"
        elif d_val < 0: s3_name = f"{away_name} {abs(d_val)}점차 승리"
        else: s3_name = "무승부 공방"
        s3_desc = f"{s3_name} ({d_prob_val:.1f}%)"
        
        return {
            "status": True,
            "home_win_pct": calc_home_win,
            "draw_pct": calc_draw,
            "away_win_pct": calc_away_win,
            "score_1st": f"{best_1st['home_score']} : {best_1st['away_score']}",
            "p1_rate": best_1st['prob'] * 100,
            "score_2nd": f"{best_2nd['home_score']} : {best_2nd['away_score']}",
            "p2_rate": best_2nd['prob'] * 100,
            "s3_desc": s3_desc,
            
            # 디버그 센터 가중치 전송
            "h_step0_atk": h_step0_atk, "h_step0_def": h_step0_def,
            "h_r1_atk": h_r1_atk, "h_r1_def": h_r1_def,
            "h_r2_atk": h_r2_atk, "h_r2_def": h_r2_def,
            "h_r31_atk": h_r31_atk, "h_r31_def": h_r31_def,
            "h_imp_atk": h_imp_atk, "h_imp_def": h_imp_def,
            "h_fa": h_fa, "h_fd": h_fd,
            "h_r4_atk": h_r4_atk, "h_r4_def": h_r4_def,
            "h_tot_atk_pct": h_tot_atk_pct, "h_tot_def_pct": h_tot_def_pct,
            
            "a_step0_atk": a_step0_atk, "a_step0_def": a_step0_def,
            "a_r1_atk": a_r1_atk, "a_r1_def": a_r1_def,
            "a_r2_atk": a_r2_atk, "a_r2_def": a_r2_def,
            "a_r31_atk": a_r31_atk, "a_r31_def": a_r31_def,
            "a_imp_atk": a_imp_atk, "a_imp_def": a_imp_def,
            "a_fa": a_fa, "a_fd": a_fd,
            "a_r4_atk": a_r4_atk, "a_r4_def": a_r4_def,
            "a_tot_atk_pct": a_tot_atk_pct, "a_tot_def_pct": a_tot_def_pct,
        }
    except Exception as e:
        return {"status": False, "msg": str(e)}
