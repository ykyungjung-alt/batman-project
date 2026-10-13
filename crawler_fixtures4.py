def parse_standings(soup, color_to_label, default_standings):
    """💡 실제 스코어맨 페이지 구조(팀순위 텍스트 및 목록)에 맞춘 정밀 파싱 모듈"""
    parsed_standings = []
    seen_teams = set()
    
    try:
        # '팀순위' 헤더 근처의 컨테이너나 리스트 요소 탐색
        # 실제 페이지 소스 구조에 맞춰 li, tr, 혹은 div 등 모든 후보군 탐색
        rows = soup.select('ul.list li, div.standing_table li, .team_list li, li')
        
        for row in rows:
            text = row.text.strip()
            # 팀순위 데이터 행 특징: 순위(숫자), 팀명, 경기수, 승, 무, 패, 득실, 승점 패턴 포함
            parts = text.split()
            if len(parts) >= 8:
                # 예: ["1", "인터밀란", "6", "5", "1", "0", "10", "16"] 형태 검증
                rank_val = parts[0]
                if rank_val.isdigit() and int(rank_val) <= 30:
                    team_val = parts[1]
                    if team_val in ["구단", "PTS", "순위", "승점"]:
                        continue
                        
                    # 스탯 매칭 (경기수, 승, 무, 패, 득실, 승점)
                    p_val = parts[2]
                    w_val = parts[3]
                    d_val = parts[4]
                    l_val = parts[5]
                    gd_val = parts[6]
                    pts_val = parts[7]
                    
                    if p_val.isdigit() and pts_val.isdigit():
                        if team_val not in seen_teams:
                            seen_teams.add(team_val)
                            
                            # 태그 컬러 추출 시도
                            style_attr = row.get("style", "")
                            tag_color = ""
                            if "--tagcolor:" in style_attr:
                                try:
                                    tag_color = style_attr.split("--tagcolor:")[1].split(";")[0].strip().upper()
                                except:
                                    pass
                            tag_label = color_to_label.get(tag_color, "일반")

                            parsed_standings.append({
                                "rank": rank_val,
                                "team": team_val,
                                "tag_color": tag_color,
                                "tag_label": tag_label,
                                "경기수": p_val,
                                "승": w_val,
                                "무": d_val,
                                "패": l_val,
                                "득실": gd_val,
                                "승점": pts_val
                            })

        if parsed_standings:
            parsed_standings.sort(key=lambda x: int(x['rank']))
            return parsed_standings, None
            
        return default_standings, "[조건 불일치] 페이지 내 팀순위 텍스트 패턴과 일치하는 행을 찾지 못했습니다."
    except Exception as e:
        return default_standings, f"[코드 에러] 랭킹표 파싱 중 런타임 예외 발생: {str(e)}"
