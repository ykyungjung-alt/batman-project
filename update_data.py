from datetime import datetime
import json
import os

def generate_dummy_data():
    # 나중에 이 부분에 외부 데이터를 가져오는 로직을 채워넣으면 됩니다.
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data = {
        "last_updated": current_time,
        "matches": [
            {"id": 1, "home": "팀 A", "away": "팀 B", "status": "대기 중"},
            {"id": 2, "home": "팀 C", "away": "팀 D", "status": "대기 중"}
        ]
    }
    
    # 레포지토리 루트의 data.json에 저장
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Data updated at {current_time}")

if __name__ == "__main__":
    generate_dummy_data()
