# 1. 페이지 내 모든 span.current.on 요소를 리스트로 수집
current_on_elements = soup.select("span.current.on")

active_text = "1"
for el in current_on_elements:
    # 2. 리스트를 순회하며 round 속성이 있거나 텍스트가 숫자인 항목 추출 ("League" 자동 필터링)
    round_attr = el.get("round", "").strip()
    text_val = el.text.strip()
    
    if round_attr.isdigit():
        active_text = round_attr
        break
    elif text_val.isdigit():
        active_text = text_val
        break

# 최종 안전장치
if not active_text.isdigit():
    active_text = "1"
