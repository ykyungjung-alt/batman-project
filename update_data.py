from datetime import datetime, timezone, timedelta
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = "https://www.scoreman3.com/football/fixture"

# 핵심 주요 리그 화이트리스트
MAJOR_LEAGUES = [
    "K리그1", "K리그 2", 
    "프리미어리그", "잉글랜드 프리미어리그", "세리에 A", "라리가", "분데스리가", "리그 1", "프랑스 리그 1",
    "에레디비시", "메이저 리그 사커", "라리가2", "챔피언쉽", "잉글랜드 챔피언쉽",
    "챔피언스리그", "유로파리그", "유로파 컨퍼런스리그", 
    "AFC챔피언스리그", "AFC 챔피언스리그2", "ASEAN 클럽선수권",
    "FIFA", "월드컵", "아시안컵", "네이션스리그", 
    "아시안게임", "올림픽", "국제 친선경기", 
    "U-23", "U-21", "U-20", "U-17",
    "잉글랜드 FA 컵", "EFL 트로피"
]

def update_json_file():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    KST = timezone(timedelta(hours=9))
    today_kst = datetime.now(KST)
    current_month = today_kst.strftime("%m")
    
    # 4일 치 탭 파라미터 순회
    day_codes = ["sc1", "sc2", "sc3", "sc4"]
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    
    daily_matches = {}
    
    try:
        for idx, code in enumerate(day_codes):
            target_url = f"{BASE_URL}?f={code}"
            driver.get(target_url)
            driver.implicitly_wait(4)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # [핵심] 상단 주황색 박스(현재 선택된 날짜 탭) 영역에서 실제 날짜와 요일 텍스트를 직접 파싱
            date_key = ""
            try:
                # 스코어맨 페이지 상단 날짜 바에서 주황색 배경이 적용되었거나 강조된 요소를 탐색
                active_elem = soup.find(style=re.compile("background.*(orange|ff|rgb\\(255)", re.IGNORECASE))
                if not active_elem:
                    active_elem = soup.select_one(".active, [class*='active']")
                
                if active_elem:
                    text_val = active_elem.get_text(strip=True) # 예: "목08" 또는 "목 08"
                    match_w = re.search(r'[월화수목금토일]', text_val)
                    match_d = re.search(r'\d{1,2}', text_val)
                    
                    if match_w and match_d:
                        w_str = match_w.group()
                        d_str = match_d.group().zfill(2)
                        date_key = f"{current_month}-{d_str} ({w_str})"
            except Exception as e:
                print(f"상단 날짜 박스 파싱 중 예외: {e}")
            
            # 주황색 박스 감지 실패 시 탭 순서(idx)에 따른 안전한 KST 보정 날짜 적용
            if not date_key:
                fallback_date = today_kst + timedelta(days=idx)
                w_str = weekdays[fallback_date.weekday()]
                date_key = fallback_date.strftime(f"%m-%d ({w_str})")
            
            # 가장 첫 번째 페이지(오늘)에만 [오늘] 마크 부착
            if idx == 0 and "[오늘]" not in date_key:
                date_key += " [오늘]"

            print(f"수집 중 ({code} -> 날짜 인식: {date_key}): {target_url}")
            
            current_league = ""
            matches_for_day = []

            rows = soup.find_all("tr")
            for row in rows:
                tds = row.find_all("td")
                text_content = row.get_text(strip=True)

                if not text_content:
                    continue

                # 리그 타이틀 행 감지 (시간 형식이 없는 행)
                if not re.search(r"\d{2}:\d{2}", text_content):
                    cleaned = re.sub(r'^[^\w\s]+\s*', '', text_content).replace("+", "").strip()
                    cleaned = re.sub(r'경기수\s*\(.*?\)', '', cleaned).strip()
                    
                    if cleaned and len(cleaned) > 1 and len(cleaned) < 35 and "시간" not in cleaned and "상태" not in cleaned:
                        current_league = cleaned
                    continue

                # [필터] 핵심 주요 리그 포함 여부 확인
                is_major = any(ml in current_league for ml in MAJOR_LEAGUES)
                if not is_major:
                    continue

                # 경기 데이터 행 감지
                time_str = ""
                for td in tds:
                    t_text = td.get_text(strip=True)
                    if re.match(r"^\d{2}:\d{2}$", t_text):
                        time_str = t_text
                        break
                
                if time_str and len(tds) >= 4:
                    cell_texts = [td.get_text(strip=True) for td in tds if td.get_text(strip=True) != ""]
                    
                    try:
                        time_idx = -1
                        for idx_val, val in enumerate(cell_texts):
                            if re.match(r"^\d{2}:\d{2}$", val):
                                time_idx = idx_val
                                break
                        
                        if time_idx != -1 and len(cell_texts) > time_idx:
                            next_val = cell_texts[time_idx + 1] if len(cell_texts) > time_idx + 1 else ""
                            
                            # 종료/진행중/연기/취소 경기 필터링
                            if next_val in ["종료", "진행중", "하프타임", "전반전", "후반전"]:
                                continue
                            if "연기" in text_content or "취소" in text_content or "연기" in next_val or "취소" in next_val:
                                continue

                            has_status = 1 if next_val in ["대기"] else 0
                            home_idx = time_idx + 1 + has_status
                            score_idx = home_idx + 1
                            away_idx = score_idx + 1
                            
                            if len(cell_texts) > away_idx:
                                home_raw = cell_texts[home_idx]
                                score_str = cell_texts[score_idx] if "-" in cell_texts[score_idx] else "-"
                                away_raw = cell_texts[away_idx]

                                home_team = re.sub(r"\[.*?\]", "", home_raw).strip()
                                away_team = re.sub(r"\[.*?\]", "", away_raw).strip()

                                if home_team and away_team and home_team != away_team:
                                    match_entry = {
                                        "id": len(matches_for_day) + 1,
                                        "league": current_league,
                                        "time": time_str,
                                        "status": "진행예정",
                                        "home": home_team,
                                        "away": away_team,
                                        "home_team": home_team,
                                        "away_team": away_team,
                                        "tournament": current_league,
                                        "score": score_str,
                                        "home_recent_stats": "4전/3승1무/0패",
                                        "away_recent_stats": "4전/2승1무/1패",
                                        "match_name": f"[{current_league}] {home_team} vs {away_team} ({time_str})"
                                    }
                                    if match_entry not in matches_for_day:
                                        matches_for_day.append(match_entry)
                    except Exception:
                        continue
            
            daily_matches[date_key] = matches_for_day

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()

    kst_time_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    output_data = {
        "last_updated": kst_time_str,
        "daily_matches": daily_matches
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print("주황색 박스 날짜 인식 및 data.json 갱신 완료!")

if __name__ == "__main__":
    update_json_file()
