from datetime import datetime, timedelta
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from zoneinfo import ZoneInfo

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

# 제외할 리그 (브라질 등 시차 문제 및 불필요한 리그)
EXCLUDE_LEAGUES = [
    "세리에 A 베타노"
]

def update_json_file():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    kst = ZoneInfo("Asia/Seoul")
    today_kst = datetime.now(kst)
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    
    daily_matches = {}

    try:
        print(f"[시작] 현재 KST 기준일: {today_kst.strftime('%Y-%m-%d %H:%M:%S')}")
        driver.get(BASE_URL)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # 1단계: 사이트 상단 날짜 탭 동적 수집 (예: 금 09, 토 10 등)
        date_tab_map = {}
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for tab in all_links:
            label = tab.text.strip()
            href = tab.get_attribute("href") or ""
            # 요일 + 날짜 숫자 패턴 매칭
            match = re.search(r"(월|화|수|목|금|토|일)\s*(\d{1,2})", label)
            if match and ("f=" in href or "fixture" in href):
                w_char, d_num = match.groups()
                key = f"{w_char}{int(d_num)}"  # 숫자의 앞자리 0 제거 대응
                date_tab_map[key] = href
                print(f"탭 발견: {key} → {href}")

        # 오늘부터 4일간 날짜 및 키 생성 (대시보드 날짜 키 밀림 방지)
        target_dates = []
        for offset in range(4):
            dt = today_kst + timedelta(days=offset)
            day_short = weekdays[dt.weekday()]
            day_num = dt.day  # 정수로 변환하여 공백/0 제거 맞춤
            label_pattern = f"{day_short}{day_num}"
            target_dates.append((offset, dt, label_pattern))

        # 2단계: 각 날짜별 페이지 순회
        for offset, target_dt, label_pattern in target_dates:
            m_str = target_dt.strftime("%m")
            d_str = target_dt.strftime("%d")
            w_str = weekdays[target_dt.weekday()]
            date_key = f"{m_str}-{d_str} ({w_str})"
            if offset == 0:
                date_key += " [오늘]"
                
            target_url = BASE_URL
            if offset > 0:
                matched_url = date_tab_map.get(label_pattern)
                if matched_url:
                    target_url = matched_url
                else:
                    # 탭을 못 찾을 경우 기본 파라미터 폴백 (sc1, sc2, sc3)
                    target_url = f"{BASE_URL}?f=sc{offset}"
                    print(f"⚠️ '{label_pattern}' 탭 매핑 실패로 폴백 URL 사용: {target_url}")
            
            print(f"\n수집 중: {date_key} | {target_url}")
            driver.get(target_url)
            
            try:
                WebDriverWait(driver, 15).until(lambda d: re.search(r"\d{2}:\d{2}", d.page_source))
            except Exception:
                print(f"  ⏳ 데이터 로드 지연 또는 경기 없음")
                
            soup = BeautifulSoup(driver.page_source, "html.parser")
            current_league = ""
            matches_for_day = []
            rows = soup.find_all("tr")
            
            for row in rows:
                tds = row.find_all("td")
                text_content = row.get_text(strip=True)
                if not text_content:
                    continue
                
                # 리그명 행 추출
                if not re.search(r"\d{2}:\d{2}", text_content):
                    cleaned = re.sub(r'^[^\w\s]+\s*', '', text_content).replace("+", "").strip()
                    cleaned = re.sub(r'경기수\s*\(.*?\)', '', cleaned).strip()
                    if cleaned and len(cleaned) > 1 and len(cleaned) < 35 and "시간" not in cleaned and "상태" not in cleaned:
                        current_league = cleaned
                    continue
                
                # 주요 리그 필터링 & 제외 리그(브라질 등) 필터링 차단
                is_major = any(ml in current_league for ml in MAJOR_LEAGUES)
                is_excluded = any(el in current_league for el in EXCLUDE_LEAGUES)
                if not is_major or is_excluded:
                    continue
                
                # 시간 추출 (사이트 원본 시간 그대로 사용)
                time_str = ""
                for td in tds:
                    match_t = re.search(r"(\d{2}:\d{2})", td.get_text(strip=True))
                    if match_t:
                        time_str = match_t.group(1)
                        break
                        
                if not time_str:
                    continue
                
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
                                entry = {
                                    "id": len(matches_for_day) + 1,
                                    "league": current_league,
                                    "time": time_str,          # 사이트 원본 시간 그대로 반영
                                    "original_time": time_str,
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
                                if entry not in matches_for_day:
                                    matches_for_day.append(entry)
                except Exception:
                    continue
                    
            daily_matches[date_key] = matches_for_day
            print(f"  ✅ {date_key} | {len(matches_for_day)}개 경기 수집 완료")
            
    except Exception as e:
        print(f"❌ 크롤링 중 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        
    output_data = {
        "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
        "daily_matches": daily_matches
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("\n🎉 data.json 갱신 완료!")

if __name__ == "__main__":
    update_json_file()
