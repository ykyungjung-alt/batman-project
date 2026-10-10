h2h_data = {"home_summary": {}, "away_summary": {}, "matches": []}
                try:
                    h2h_div = detail_soup.find("div", id="dv_head_to_head")
                    if h2h_div:
                        # 맞대결 요약 (승무패 및 경기당 득점)
                        vote_divs = h2h_div.find_all("div", class_="vote")
                        for v in vote_divs:
                            ext_els = v.find_all("div", class_=["ext", "win-f", "draw-f", "lose-f"])
                            if len(ext_els) >= 3:
                                left_val = ext_els[0].get_text(strip=True)
                                label = ext_els[1].get_text(strip=True)
                                right_val = ext_els[2].get_text(strip=True)
                                
                                if "승" in label or "%" in left_val or "무승부" in label:
                                    h2h_data["home_summary"]["record_summary"] = left_val
                                    h2h_data["away_summary"]["record_summary"] = right_val
                                elif "경기당 득점" in label:
                                    h2h_data["home_summary"]["goals_per_game"] = left_val
                                    h2h_data["away_summary"]["goals_per_game"] = right_val

                        # 맞대결 상세 경기 목록
                        h_table = h2h_div.find_next("table")
                        if h_table:
                            for h_row in h_table.find_all("tr"):
                                cols = [c.get_text(strip=True) for c in h_row.find_all(["th", "td"]) if c.get_text(strip=True)]
                                if len(cols) >= 3 and not any("득점" in c for c in cols):
                                    h2h_data["matches"].append({"row_data": cols})
                    if len(h2h_data["matches"]) > 10:
                        h2h_data["matches"] = h2h_data["matches"][:10]
                except Exception as e:
                    print(f"  - 맞대결 파싱 예외: {e}")
