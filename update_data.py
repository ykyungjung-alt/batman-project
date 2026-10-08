from datetime import datetime, timezone, timedelta
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = "https://www.scoreman123.com/football/fixture"

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
def convert_to_kst(time_str, base_date, source_offset_hours=-3):
    """
    사이트 시각을 KST로 변환
    - 브라질(UTC-3): source_offset_hours=-3
    - 유럽(UTC+0): source_offset_hours=0
    - KST = UTC+9
    """
    try:
        h, m = map(int, time_str.split(":"))
        # 사이트 시각 → UTC → KST
        source_dt = base_date.replace(hour=h, minute=m, second=0, microsecond=0)
        utc_dt = source_dt - timedelta(hours=source_offset_hours)
        kst_dt = utc_dt + timedelta(hours=9)
        return kst_dt.strftime("%H:%M")
    except Exception:
        return time_str
        
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
    
    day_steps = [
        (0, ""),         # 오늘
        (1, "sc1"),      # 내일
        (2, "sc2"),      # 모레
        (3, "sc3"),      # 글피
    ]
    
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    daily_matches = {}
    
    try:
        for offset, param in day_steps:
            target_url = f"{BASE_URL}?f={param}" if param else BASE_URL
            driver.get(target_url)
            driver.implicitly_wait(4)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            target_date = today_kst + timedelta(days=offset)
            w_str = weekdays[target_date.weekday()]
            m_str = target_date.strftime("%m")
            d_str = target_date.strftime("%d")
            
            date_key = f"{m_str}-{d_str} ({w_str})"
            if offset == 0:
                date_key += " [오늘]"

            print(f"수집 중 (파라미터: {param or '기본(오늘)'} -> {date_key}): {target_url}")
            
            current_league = ""
            matches_for_day = []

            rows = soup.find_all("tr")
            for row in rows:
                tds = row.find_all("td")
                text_content = row.get_text(strip=True)

                if not text_content:
                    continue

                if not re.search(r"\d{2}:\d{2}", text_content):
                    cleaned = re.sub(r'^[^\w\s]+\s*', '', text_content).replace("+", "").strip()
                    cleaned = re.sub(r'경기수\s*\(.*?\)', '', cleaned).strip()
                    
                    if cleaned and len(cleaned) > 1 and len(cleaned) < 35 and "시간" not in cleaned and "상태" not in cleaned:
                        current_league = cleaned
                    continue

                is_major = any(ml in current_league for ml in MAJOR_LEAGUES)
                if not is_major:
                    continue

                # [수정] 어떤 객체 변환도 거치지 않고 오직 텍스트 그대로 시간 추출
                time_str = ""
                if len(tds) >= 2:
                    raw_time = tds[1].get_text(strip=True)
                    match_t = re.search(r"(\d{2}:\d{2})", raw_time)
                    if match_t:
                        time_str = match_t.group(1)
                
                if not time_str:
                    for td in tds:
                        t_text = td.get_text(strip=True)
                        match_t = re.search(r"(\d{2}:\d{2})", t_text)
                        if match_t:
                            time_str = match_t.group(1)
                            break
                
                if time_str and len(tds) >= 4:
                    cell_texts = [td.get_text(strip=True) for td in tds if td.get_text(strip=True) != ""]
                    
                    try:
                        time_idx = -1
                        for idx_val, val in enumerate(cell_texts):
                            if time_str in val:
                                time_idx = idx_val
                                break
                        
                        if time_idx != -1 and len(cell_texts) > time_idx:
                            next_val = cell_texts[time_idx + 1] if len(cell_texts) > time_idx + 1 else ""
                            
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
        print(f"크롤링 중 에러 발생: {e}")
    finally:
        driver.quit()

    kst_time_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    output_data = {
        "last_updated": kst_time_str,
        "daily_matches": daily_matches
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print("데이터 갱신 완료!")

if __name__ == "__main__":
    update_json_file()
