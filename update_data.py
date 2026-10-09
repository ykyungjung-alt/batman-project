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

def update_json_file():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    options.add_argument("--lang=ko_KR")
    
    driver = webdriver.Chrome(options=options)
    try:
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "Asia/Seoul"})
    except Exception as e:
        print(f"⚠️ 타임존 에뮬레이션 설정 경고: {e}")

    kst = ZoneInfo("Asia/Seoul")
    today_kst = datetime.now(kst)
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    
    daily_matches = {}

    try:
        print(f"[시작] 브라우저 타임존 KST 동기화 완료 후 크롤링 시작")
        driver.get(BASE_URL)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        date_tab_map = {}
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for a in all_links:
            text = a.text.strip()
            if re.match(r"^(월|화|수|목|금|토|일)\s*\d{1,2}$", text):
                clean_label = re.sub(r"\s+", "", text)
                href = a.get_attribute("href")
                if href:
                    date_tab_map[clean_label] = href

        target_dates = []
        for offset in range(4):
            dt = today_kst + timedelta(days=offset)
            day_short = weekdays[dt.weekday()]
            day_num = dt.strftime("%d").lstrip("0")
            label_pattern = f"{day_short}{day_num}"
            target_dates.append((offset, dt, label_pattern))

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
                    target_url = f"{BASE_URL}?f=sc{offset}"
            
            driver.get(target_url)
            try:
                WebDriverWait(driver, 15).until(lambda d: re.search(r"\d{2}:\d{2}", d.page_source))
            except Exception:
                pass
                
            soup = BeautifulSoup(driver.page_source, "html.parser")
            current_league = ""
            matches_for_day = []
            rows = soup.find_all("tr")
            
            for row in rows:
                tds = row.find_all("td")
                text_content = row.get_text(strip=True)
                if not text_content:
                    continue
                
                if not re.search(r"\d{2}:\d{2}", text_content):
                    cleaned = re.sub(r"^[^\w\s]+", "", text_content).replace("+", "").strip()
                    cleaned = re.sub(r"경기수\s*\(.*?\)", "", cleaned).strip()
                    if 1 < len(cleaned) < 35 and "시간" not in cleaned and "상태" not in cleaned:
                        current_league = cleaned
                    continue
                
                is_major = any(ml in current_league for ml in MAJOR_LEAGUES)
                if not is_major:
                    continue
                
                # Match ID (match_code) 추출 로직
                m_id = None
                row_id = row.get("id", "")
                m_match = re.search(r'tr1_(\d+)', row_id)
                if m_match:
                    m_id = m_match.group(1)
                else:
                    onclick_attr = row.get("onclick", "")
                    if not onclick_attr:
                        td_click = row.find("td", onclick=True)
                        if td_click:
                            onclick_attr = td_click.get("onclick", "")
                    sub_match = re.search(r'analysis\((\d+)', onclick_attr)
                    if sub_match:
                        m_id = sub_match.group(1)
                
                if not m_id:
                    a_tag = row.find("a", href=True)
                    if a_tag:
                        href_val = a_tag.get("href", "")
                        href_match = re.search(r'data-(\d+)', href_val)
                        if href_match:
                            m_id = href_match.group(1)

                time_str = None
                for td in tds:
                    m = re.search(r"(\d{2}:\d{2})", td.get_text(strip=True))
                    if m:
                        time_str = m.group(1)
                        break
                        
                if not time_str:
                    continue
                
                cell_texts = [td.get_text(strip=True) for td in tds if td.get_text(strip=True)]
                try:
                    time_idx = next(i for i, v in enumerate(cell_texts) if time_str in v)
                except StopIteration:
                    continue
                    
                next_val = cell_texts[time_idx + 1] if len(cell_texts) > time_idx + 1 else ""
                if next_val in ["종료", "진행중", "하프타임", "전반전", "후반전"]:
                    continue
                if any(k in text_content or k in next_val for k in ["연기", "취소"]):
                    continue
                    
                has_status = 1 if next_val == "대기" else 0
                home_idx = time_idx + 1 + has_status
                score_idx = home_idx + 1
                away_idx = score_idx + 1
                
                if len(cell_texts) <= away_idx:
                    continue
                    
                home_team = re.sub(r"\[.*?\]", "", cell_texts[home_idx]).strip()
                away_team = re.sub(r"\[.*?\]", "", cell_texts[away_idx]).strip()
                score_str = cell_texts[score_idx] if "-" in cell_texts[score_idx] else "-"
                
                if home_team and away_team and home_team != away_team:
                    entry = {
                        "id": len(matches_for_day) + 1,
                        "match_code": m_id if m_id else "",  # 👈 매칭 기준이 될 고유 ID 탑재
                        "league": current_league,
                        "time": time_str,
                        "home": home_team,
                        "away": away_team,
                        "score": score_str
                    }
                    if entry not in matches_for_day:
                        matches_for_day.append(entry)
                        
            daily_matches[date_key] = matches_for_day
            print(f"  ✅ {date_key} | {len(matches_for_day)}개 경기 수집 완료")
            
    except Exception as e:
        print(f"❌ 크롤링 중 오류: {e}")
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
