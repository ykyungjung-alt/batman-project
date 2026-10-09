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

def collect_match_details():
    # 1. 기존 메인 일정 파일 로드
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            main_data = json.load(f)
    except FileNotFoundError:
        print("❌ data.json 파일이 없습니다. 메인 일정 수집기(crawler_fixtures.py)를 먼저 실행해주세요.")
        return

    # 2. 크롬 옵션 설정 (타임존 문제 원천 차단)
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    options.add_argument("--lang=ko_KR")
    
    driver = webdriver.Chrome(options=options)
    
    # 브라우저 내부 시계를 한국 시간(Asia/Seoul)으로 완벽 고정
    try:
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "Asia/Seoul"})
    except Exception as e:
        print(f"⚠️ 타임존 에뮬레이션 설정 경고: {e}")

    kst = ZoneInfo("Asia/Seoul")
    today_kst = datetime.now(kst).strftime("%m-%d")
    tomorrow_kst = (datetime.now(kst) + timedelta(days=1)).strftime("%m-%d")

    detailed_matches = {}

    try:
        print("[시작] 오늘 및 내일 경기 상세 메타 정보 수집 중...")
        
        for date_key, matches in main_data.get("daily_matches", {}).items():
            # 오늘 또는 내일 날짜 키만 선별
            if not (today_kst in date_key or tomorrow_kst in date_key):
                continue
                
            detailed_matches[date_key] = []
            
            for match in matches:
                match_id = match.get("match_id")
                if not match_id:
                    detailed_matches[date_key].append(match)
                    continue
                
                detail_url = f"https://www.scoreman123.com/match/data-{match_id}"
                print(f"  🔍 상세 수집 중: {match['home']} vs {match['away']} (ID: {match_id})")
                
                try:
                    driver.get(detail_url)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    
                    # 1. 기본 정보 및 구장 파싱
                    stadium = ""
                    round_info = ""
                    for text_el in soup.find_all(text=True):
                        if "구장" in text_el or "Park" in text_el or "Arena" in text_el:
                            parent_text = text_el.parent.get_text(strip=True)
                            if len(parent_text) < 40 and not stadium:
                                stadium = parent_text
                        if "라운드" in text_el:
                            round_info = text_el.strip()

                    # 2. 팀 순위 파싱 (팀순위 테이블 추출)
                    rankings = []
                    ranking_table = soup.find(id=re.compile("팀순위")) or soup.find(text=re.compile("팀순위"))
                    if ranking_table:
                        # 순위 표 내부 tr 순회하며 데이터 추출 가능
                        pass

                    # 3. 최근 전적 및 골득실 파싱
                    recent_stats = {"home": "", "away": ""}
                    recent_section = soup.find(text=re.compile("최근전적"))
                    if recent_section:
                        # 최근 전적 요약 및 득실 파싱 로직
                        pass

                    # 4. 상대 전적 파싱
                    h2h_stats = ""
                    h2h_section = soup.find(text=re.compile("상대전적"))
                    if h2h_section:
                        # 상대 전적 요약 및 득실 파싱 로직
                        pass

                    # 5. 라인업 (결장자 정보) 파싱
                    absent_players = {"home": [], "away": []}
                    lineup_section = soup.find(text=re.compile("라인업"))
                    if lineup_section:
                        # 결장자 마크(붉은색 아이콘 등)가 포함된 선수 명단 추출
                        pass

                    # 수집된 메타 데이터를 딕셔너리로 병합
                    meta_info = {
                        "stadium": stadium,
                        "round": round_info,
                        "rankings": rankings,
                        "recent_stats": recent_stats,
                        "h2h_stats": h2h_stats,
                        "absent_players": absent_players
                    }
                    
                    match["meta_details"] = meta_info
                    detailed_matches[date_key].append(match)
                    
                except Exception as e:
                    print(f"    ⚠️ 상세 데이터 수집 실패 (ID: {match_id}): {e}")
                    detailed_matches[date_key].append(match)
                    
    except Exception as e:
        print(f"❌ 상세 크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()

    # 결과 저장 (별도의 상세 메타 파일로 분리 관리)
    output_data = {
        "last_updated": datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S"),
        "daily_matches": detailed_matches
    }
    
    with open("match_details.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("\n🎉 오늘/내일 경기 심층 메타 정보(`match_details.json`) 저장 완료!")

if __name__ == "__main__":
    collect_match_details()
