def parse_team_squad(driver, team_summary_url):
    """
    💡 데이터 밀림 현상을 역이용하여, 필드명을 알맞게 매핑하고 나이 추출 로직을 완전히 제거한 파서
    """
    if team_summary_url in _team_squad_cache:
        return _team_squad_cache[team_summary_url]

    squad_list = []
    try:
        driver.get(team_summary_url)
        time.sleep(0.5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        lineup_ul = soup.find("ul", id="lineupList")
        if not lineup_ul:
            return squad_list
            
        player_items = lineup_ul.find_all("li", class_="lineuplis")
        
        for li in player_items:
            try:
                # 1. [이름 추출] span.name 안에서 순수 선수 이름 추출
                name_span = li.find("span", class_="name")
                player_name = ""
                if name_span:
                    des_span = name_span.find("span", class_="des")
                    if des_span:
                        des_text = des_span.get_text(strip=True)
                        full_text = name_span.get_text(strip=True)
                        player_name = full_text.replace(des_text, "").strip()
                    else:
                        player_name = name_span.get_text(strip=True)

                # 2. [직계 span 추출] name 영역을 제외한 나머지 데이터 수집
                child_spans = li.find_all("span", recursive=False)
                
                valid_texts = []
                for s in child_spans:
                    if "name" in s.get("class", []):
                        continue
                    txt = s.get_text(strip=True)
                    if txt:
                        valid_texts.append(txt)

                # 3. [필드 재매핑] 밀려서 들어오는 순서 그대로 변수 지정 (나이 추출 로직 삭제)
                # 첫 번째 칸(이름+등번호+국적) -> player_number_info로 지정
                # 두 번째 칸(포지션 명칭) -> position으로 지정
                number_info = valid_texts[0] if len(valid_texts) > 0 else "-"
                position = valid_texts[1] if len(valid_texts) > 1 else "-"
                
                if player_name:
                    player_info = {
                        "name": player_name,
                        "player_number_info": number_info,  # 기존 position 위치에 들어오던 값
                        "position": position                 # 기존 age 위치에 들어오던 포지션 값
                    }
                    squad_list.append(player_info)
            except Exception:
                continue
                
    except Exception as e:
        print(f"  - 선수 명단 파싱 예외: {e}")
        
    _team_squad_cache[team_summary_url] = squad_list
    return squad_list
