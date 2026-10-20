def crawl_player_details(session, headers, player_id):
    """선수 고유 ID를 받아 이미지-텍스트-스팬 구조를 고려하여 라벨(span) 기준 순수 수치만 정확히 추출합니다."""
    player_url = f"https://football.scoreman123.com/team/player/{player_id}"
    
    player_stats = {
        "player_id": player_id,
        "matches_played": 0,
        "total_play_time": 0,
        "avg_play_time": 0.0,
        "grade": "D",
        "important_stats": {}
    }
    
    try:
        resp = session.get(player_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # ul#techImportant 내부의 각 li 항목 탐색
            important_items = soup.select('ul#techImportant > li')
            matches = 0
            play_time = 0
            imp_stats = {}
            
            for item in important_items:
                # 1) 라벨이 들어있는 <span> 태그를 정확히 찾습니다.
                span_tag = item.select_one('span')
                if span_tag:
                    label = span_tag.text.strip()
                    
                    # 2) <li> 안에서 <img> 등 불필요한 태그를 제거하고 남은 텍스트를 가져옵니다.
                    # 이미지 태그 제거
                    for img in item.select('img'):
                        img.decompose()
                    # 라벨 span 태그 제거
                    span_tag.decompose()
                    
                    # 남은 텍스트가 바로 순수 수치 데이터 (예: "3", "217", "7.61" 등)
                    val = item.text.strip()
                    imp_stats[label] = val
                    
                    # 3) 수치 매핑 추출 (정규식 활용)
                    if "경기" in label and "평점" not in label:
                        numbers = re.findall(r'\d+', val)
                        if numbers:
                            try: matches = int(numbers[0])
                            except: pass
                    elif "출전시간" in label:
                        numbers = re.findall(r'\d+', val)
                        if numbers:
                            try: play_time = int(numbers[0])
                            except: pass
            
            player_stats["important_stats"] = imp_stats
            player_stats["matches_played"] = matches
            player_stats["total_play_time"] = play_time
            
            # 평균 출전 시간 계산 및 A~D 등급 판정
            if matches > 0:
                avg_time = play_time / matches
                player_stats["avg_play_time"] = round(avg_time, 1)
                
                if avg_time >= 70:
                    player_stats["grade"] = "A"
                elif avg_time >= 50:
                    player_stats["grade"] = "B"
                elif avg_time >= 30:
                    player_stats["grade"] = "C"
                else:
                    player_stats["grade"] = "D"
            else:
                player_stats["grade"] = "D"
                
    except Exception as e:
        print(f"⚠️ [선수 스탯 파싱 오류 - ID: {player_id}]: {e}")
        
    return player_stats
