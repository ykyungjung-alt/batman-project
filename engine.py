import math
import re
import os
import json

def compute_match_prediction_master(target_detail, home_name, away_name, league_name="", v5_details=None, v5_1_details=None, v4_leagues=None):
    """
    배트맨 프로젝트 0단계 ~ 6단계 마스터 수리 정량 분석 엔진
    app.py의 0~6단계 모든 규칙별 가중치 산출 로직과 완벽히 동기화된 최종 규격입니다.
    """
    try:
        meta = target_detail.get("meta_details", {})
        head = target_detail.get("head_info", {})
        
        clean_home = str(home_name).strip().replace(" ", "").lower()
        clean_away = str(away_name).strip().replace(" ", "").lower()
        target_match_code = str(target_detail.get("match_code", "")).strip()

        # ==================================================================
        # 1. 0단계: 공식 팀 순위 및 country.json 기반 등급·가중치 연동 모사
        # ==================================================================
        rankings_raw = meta.get("rankings", [])
        h_step0_atk, h_step0_def = 0.0, 0.0
        a_step0_atk, a_step0_def = 0.0, 0.0

        for r in rankings_raw:
            team_str = str(r.get("team", "")).strip().replace(" ", "").lower()
            rank_code = str(r.get("rank", "")).upper()
            if clean_home in team_str or team_str in clean_home:
                if "KOR" in rank_code or "k리그" in str(league_name).lower():
                    h_step0_atk, h_step0_def = 9.0, -9.0
                else:
                    h_step0_atk, h_step0_def = 9.0, -9.0
            elif clean_away in team_str or team_str in clean_away:
                if "KOR" in rank_code or "k리그" in str(league_name).lower():
                    a_step0_atk, a_step0_def = 9.0, -9.0
                else:
                    a_step0_atk, a_step0_def = 9.0, -9.0

        # ==================================================================
        # 2. 규칙 1번: 종합 최근 10경기 LIFO 및 공수 티어 가중치 산출
        # ==================================================================
        recent_form = meta.get("recent_form", {})
        h_summary = recent_form.get("home_summary", {})
        a_summary = recent_form.get("away_summary", {})

        h_base_gpg = float(h_summary.get("goals_per_game", 1.2))
        h_base_cpg = float(h_summary.get("conceded_per_game", 1.1))
        a_base_gpg = float(a_summary.get("goals_per_game", 1.1))
        a_base_cpg = float(a_summary.get("conceded_per_game", 1.2))

        def get_atk_tier_weight(g):
            if g >= 2.3: return 12.0
            elif g >= 1.7: return 9.0
            elif g >= 1.1: return 6.0
            elif g >= 0.5: return 3.0
            else: return 0.0

        def get_def_tier_weight(c):
            if c < 0.5: return -12.0
            elif c < 0.9: return -9.0
            elif c < 1.3: return -6.0
            elif c < 1.7: return -3.0
            else: return 0.0

        h_r1_atk = get_atk_tier_weight(h_base_gpg)
        h_r1_def = get_def_tier_weight(h_base_cpg)
        a_r1_atk = get_atk_tier_weight(a_base_gpg)
        a_r1_def = get_def_tier_weight(a_base_cpg)

        # ==================================================================
        # 3. 규칙 2번: 구장 환경 Shift 검증 (홈/중립 경기판정 및 ±15% 규격)
        # ==================================================================
        venue_val = str(head.get("stadium", ""))
        home_stadium_val = str(head.get("home_stadium", ""))
        is_neutral = False
        if venue_val and home_stadium_val:
            if venue_val.strip().lower() != home_stadium_val.strip().lower():
                is_neutral = True

        # 홈 구장이면 0%, 중립구장 혹은 원정이면 Shift 보정 적용
        h_r2_atk, h_r2_def = (0.0, 0.0) if not is_neutral else (-15.0, 15.0)
        a_r2_atk, a_r2_def = -15.0, 15.0  # 원정팀은 기본 구장 Shift 적용

        # ==================================================================
        # 4. 규칙 3-1번: V5 결장자 + V5-1 포지션 매핑 및 반감 연산
        # ==================================================================
        def engine_compute_squad_weights(absentees_list, squad_list):
            if not absentees_list or not isinstance(absentees_list, list):
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

            tot_atk, tot_def = 0.0, 0.0
            for item in absentees_list:
                if not isinstance(item, dict): continue
                p_name = str(item.get("name", "-")).strip()
                p_pos = squad_pos_map.get(p_name, squad_pos_map.get(p_name.replace(" ", ""), ""))
                if not p_pos or p_pos == "-": p_pos = "미드필더"
                
                p_type = str(item.get("status", "결장")).strip()
                stats_dict = item.get("stats", {}) if isinstance(item.get("stats"), dict) else {}
                raw_grade = str(stats_dict.get("grade", item.get("grade", "C"))).strip().upper()
                
                if "A" in raw_grade: rate = 12.0
                elif "B" in raw_grade: rate = 8.0
                elif "C" in raw_grade: rate = 4.0
                else: rate = 0.0
                
                is_attacker = any(k in p_pos for k in ["공격수", "미드필더", "FW", "MF"])
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
                
            return tot_atk, tot_def

        h_r31_atk, h_r31_def = 0.0, 0.0
        a_r31_atk, a_r31_def = 0.0, 0.0

        if v5_details and isinstance(v5_details, dict):
            v5_lineup = v5_details.get("lineup_details", v5_details)
            for k, v in v5_lineup.items():
                if not isinstance(v, dict): continue
                v_code = str(v.get("match_code", k)).strip()
                v_h = str(v.get("home", "")).strip().replace(" ", "").lower()
                if v_code == target_match_code or (clean_home in v_h):
                    h_abs = v.get("home_absentees", [])
                    a_abs = v.get("away_absentees", [])
                    h_squad = v5_1_details.get("squad_details", {}).get(k, {}).get("home_squad", []) if v5_1_details else []
                    a_squad = v5_1_details.get("squad_details", {}).get(k, {}).get("away_squad", []) if v5_1_details else []
                    
                    h_r31_atk, h_r31_def = engine_compute_squad_weights(h_abs, h_squad)
                    a_r31_atk, a_r31_def = engine_compute_squad_weights(a_abs, a_squad)
                    break

        # ==================================================================
        # 5. 규칙 3-2번: 일정 중요도 및 이동 피로도 산출
        # ==================================================================
        h_imp_atk, h_imp_def = 5.0, -5.0
        a_imp_atk, a_imp_def = 5.0, -5.0

        h_fa, h_fd = 0.0, 0.0
        a_fa, a_fd = -5.0, 5.0  # 원정 1단계 기본 피로

        h_r3_tot_atk = h_r31_atk + h_imp_atk + h_fa
        h_r3_tot_def = h_r31_def + h_imp_def + h_fd
        a_r3_tot_atk = a_r31_atk + a_imp_atk + a_fa
        a_r3_tot_def = a_r31_def + a_imp_def + a_fd

        # ==================================================================
        # 6. 규칙 4번: 역대 H2H 상성 전수 조사 및 단방향 10% 룰
        # ==================================================================
        h2h_matches = meta.get("h2h", {}).get("matches", [])
        total_h2h = len(h2h_matches)
        home_h2h_wins, away_h2h_wins = 0, 0
        for m in h2h_matches:
            row_cols = m.get("row_data", [])
            if len(row_cols) >= 4:
                try:
                    s_parts = row_cols[2].replace("：", "-").split("-")
                    s1, s2 = int(s_parts[0].strip()), int(s_parts[1].strip())
                    if row_cols[1] == home_name:
                        if s1 > s2: home_h2h_wins += 1
                        elif s1 < s2: away_h2h_wins += 1
                    else:
                        if s1 > s2: away_h2h_wins += 1
                        elif s1 < s2: home_h2h_wins += 1
                except: pass

        home_win_rate = (home_h2h_wins / total_h2h * 100) if total_h2h >= 5 else 0.0
        away_win_rate = (away_h2h_wins / total_h2h * 100) if total_h2h >= 5 else 0.0

        h_r4_atk, h_r4_def = (10.0, -10.0) if home_win_rate >= 50.0 else (0.0, 0.0)
        a_r4_atk, a_r4_def = (10.0, -10.0) if away_win_rate >= 50.0 else (0.0, 0.0)

        # ==================================================================
        # 7. 규칙 5번 & 6번: 최종 보정, 람다 및 푸아송 확률 산출
        # ==================================================================
        h_tot_atk_pct = h_step0_atk + h_r1_atk + h_r2_atk + h_r3_tot_atk + h_r4_atk
        h_tot_def_pct = h_step0_def + h_r1_def + h_r2_def + h_r3_tot_def + h_r4_def
        a_tot_atk_pct = a_step0_atk + a_r1_atk + a_r2_atk + a_r3_tot_atk + a_r4_atk
        a_tot_def_pct = a_step0_def + a_r1_def + a_r2_def + a_r3_tot_def + a_r4_def

        h_max_g = h_base_gpg * (1 + h_tot_atk_pct / 100.0)
        h_min_c = h_base_cpg * (1 + h_tot_def_pct / 100.0)
        a_max_g = a_base_gpg * (1 + a_tot_atk_pct / 100.0)
        a_min_c = a_base_cpg * (1 + a_tot_def_pct / 100.0)

        h_final_exp_g = max(0.2, (h_max_g + (2.0 - a_min_c)) / 2.0)
        h_final_exp_c = max(0.2, (h_min_c + (2.0 - a_max_g)) / 2.0)
        a_final_exp_g = max(0.2, (a_max_g + (2.0 - h_min_c)) / 2.0)
        a_final_exp_c = max(0.2, (a_min_c + (2.0 - h_max_g)) / 2.0)

        h_over_factor, a_over_factor = (0.15, 0.15) if (h_final_exp_g + a_final_exp_g > 3.2) else (0.0, 0.0)
        h_final = h_final_exp_g * (1 + h_over_factor)
        a_final = a_final_exp_g * (1 + a_over_factor)
        total_exp_goals = h_final + a_final

        def poisson_prob(lmbda, k):
            if lmbda <= 0 and k == 0: return 1.0
            try: return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
            except: return 0.0

        matrix_max_k = 4 if total_exp_goals <= 3.2 else 6
        win_loss_probs, score_probs = [], []

        for h_g in range(matrix_max_k + 1):
            for a_g in range(matrix_max_k + 1):
                p_h = poisson_prob(h_final_exp_g, h_g)
                p_a = poisson_prob(a_final_exp_g, a_g)
                win_loss_probs.append({"home_score": h_g, "away_score": a_g, "prob": p_h * p_a})
                
                p_h_fin = poisson_prob(h_final, h_g)
                p_a_fin = poisson_prob(a_final, a_g)
                score_probs.append({"home_score": h_g, "away_score": a_g, "prob": p_h_fin * p_a_fin})

        calc_home_win = sum(item["prob"] for item in win_loss_probs if item["home_score"] > item["away_score"]) * 100
        calc_draw = sum(item["prob"] for item in win_loss_probs if item["home_score"] == item["away_score"]) * 100
        calc_away_win = sum(item["prob"] for item in win_loss_probs if item["home_score"] < item["away_score"]) * 100

        sorted_scores = sorted(score_probs, key=lambda x: x["prob"], reverse=True)
        best_1st, best_2nd = sorted_scores[0], sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0]

        diff_probs = {}
        for item in score_probs:
            diff = item["home_score"] - item["away_score"]
            diff_probs[diff] = diff_probs.get(diff, 0.0) + item["prob"]
        sorted_diffs = sorted(diff_probs.items(), key=lambda x: x[1], reverse=True)
        d_val, d_prob_val = sorted_diffs[0][0], sorted_diffs[0][1] * 100

        if d_val > 0: s3_name = f"{home_name} {d_val}점차 승리"
        elif d_val < 0: s3_name = f"{away_name} {abs(d_val)}점차 승리"
        else: s3_name = "무승부 공방"
        s3_desc = f"{s3_name} ({d_prob_val:.1f}%)"

        return {
            "status": True,
            "home_win_pct": calc_home_win, "draw_pct": calc_draw, "away_win_pct": calc_away_win,
            "score_1st": f"{best_1st['home_score']} : {best_1st['away_score']}", "p1_rate": best_1st["prob"] * 100,
            "score_2nd": f"{best_2nd['home_score']} : {best_2nd['away_score']}", "p2_rate": best_2nd["prob"] * 100,
            "s3_desc": s3_desc,
            
            # 💡 7단계 디버그 센터 가중치 매칭 값 완벽 리턴
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
            "a_tot_atk_pct": a_tot_atk_pct, "a_tot_def_pct": a_tot_def_pct
        }

    except Exception as e:
        return {"status": False, "msg": str(e)}
