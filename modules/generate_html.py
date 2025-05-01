# 2025-0328_1720
# 1) 改註解日期格式為 YYYY-MMDD_hhmm
# 2) summary_row 底色改為極淺藍 (#F0FAFF)

import json
import logging
import os

# 創建 logger
logger = logging.getLogger(f'{__file__}')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def generate_total_html(total_list, html_output_path):
    """ 依照 total_list 產生 HTML 表格，並寫入 html_output_path。 """
    # 建立 logger
    logger = logging.getLogger(__name__)
    logger.info(f"開始產生總表 HTML：{html_output_path}")

    # --- 在標題前加入「排名」欄 ---
    top_header_row_1 = [
        "排名",
        "經文名",
        "名相總個數", "名相總筆數",
        "群首詞個數", "群首詞筆數",
        "異體字個數", "異體字筆數",
        "音譯詞個數", "音譯詞筆數",
        "同義詞個數", "同義詞筆數",
        "複合詞個數", "複合詞筆數",
        "相關詞個數", "相關詞筆數"
    ]
    # 產生第一列 HTML（特殊背景）
    row1_html_cells = []
    for i, col in enumerate(top_header_row_1):
        bg_color = "#1E4477" if i % 2 == 0 else "#B58500"
        cell_html = (
            f'<th style="border:1pt solid #000; color:#FFF; font-weight:bold; background-color:{bg_color};">{col}</th>'
        )
        row1_html_cells.append(cell_html)
    row1_html = "<tr>" + "".join(row1_html_cells) + "</tr>"

    # 產生資料列 HTML
    row_html_list = []
    for idx, row in enumerate(total_list, start=1):
        # 排名欄位
        rank_cell = f"<td>{idx}</td>"
        # 原有資料欄位
        data_cells = "".join(f"<td>{cell}</td>" for cell in row)
        # 組合成一行
        row_html_list.append(f"<tr>{rank_cell}{data_cells}</tr>")

    # 組合完整 HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>佛經詞表彙整</title>
<style>
    table {{ border-collapse: collapse; width: 100%; }}
    thead {{ position: sticky; top: 0; z-index: 999; }}
    tbody td {{
        border: 1px solid #000;
        padding: 4px;
        text-align: center;
        background-color: #ffffff;
    }}
    /* 固定第一欄並禁用排序點擊 */
    th:first-child, td:first-child {{
        position: sticky;
        left: 0;
        background-color: #ffffff;
        z-index: 10;
    }}
    th:first-child {{
        pointer-events: none;
    }}
</style>
</head>
<body>
<table>
    <thead>
        {row1_html}
    </thead>
    <tbody>
        {''.join(row_html_list)}
    </tbody>
</table>
</body>
</html>"""

    # 確保輸出目錄存在
    html_dir = os.path.dirname(html_output_path)
    if not os.path.exists(html_dir):
        os.makedirs(html_dir)

    # 寫出 HTML
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"完成產生總表 HTML：{html_output_path}")
    print(f"已產生 {html_output_path}")


def generate_one_html(json_path, html_output_path, key_list):
    """
    讀取指定的 JSON 檔案，根據傳入的 key_list（中文字詞 list），
    產生 HTML 表格（遇到 key_list 中的字詞以藍色顯示，否則以黑色顯示），
    然後寫入 html_output_path。
    return:
        aggregator = []
            aggregator.append(len(global_total_words))
            aggregator.append(global_total_sum)
            aggregator.append(global_main_term_count)
            aggregator.append(global_main_term_sum)
            for json_key, title in categories:
                aggregator.append(len(global_category_data[json_key]["words"]))
                aggregator.append(global_category_data[json_key]["sum"])
            
            top_header_row_1 = [
                "名相總個數", "名相總筆數",
                "群首詞個數", "群首詞筆數",
                "異體字個數", "異體字筆數",
                "音譯詞個數", "音譯詞筆數",
                "同義詞個數", "同義詞筆數",
                "複合詞個數", "複合詞筆數",
                "相關詞個數", "相關詞筆數"
            ]    
    """

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 定義各分類對應的 JSON 鍵與輸出欄位標題（順序決定輸出順序）
    categories = [
        ("異體字", "異體字"),
        ("音譯詞", "音譯詞"),
        ("同義詞/近義詞(意譯)", "同義詞"),
        ("複合詞", "複合詞"),
        ("相關詞", "相關詞")
    ]
    
    # 用來存放最終要輸出的所有「資料列」，每筆為 tuple (row_list, is_summary_row)
    group_rows = []
    
    # 初始化全局統計資料：用於去重計算跨所有主題的統計
    global_total_words = set()         # 全局所有字詞（包含群首詞與各分類）
    global_total_sum = 0               # 全局筆數總和
    global_main_term_count = 0         # 群首詞個數
    global_main_term_sum = 0           # 群首詞筆數總和
    global_category_data = {json_key: {"words": set(), "sum": 0} for json_key, title in categories}
    
    # 依據 JSON 中每個主詞依 id 排序（假設 id 為數字型字串）
    sorted_terms = sorted(data.items(), key=lambda kv: int(kv[1].get("id", "0")))
    
    # 處理每個群首詞 (main_term)
    for main_term, info in sorted_terms:
        # 群首詞本身 found.total
        try:
            main_total = int(info.get("found", {}).get("total", 0))
        except:
            main_total = 0
        
        # 收集各分類中 total 不為 0 的詞
        cat_lists = {}
        max_rows = 0
        for json_key, title in categories:
            lst = []
            for word, entry in info.get(json_key, {}).items():
                try:
                    cnt = int(entry.get("total", 0))
                except:
                    cnt = 0
                if cnt != 0:
                    lst.append((word, cnt))
            cat_lists[json_key] = lst
            if len(lst) > max_rows:
                max_rows = len(lst)
        
        # 若沒有任何分類資料，至少保證會有 1 行 (只顯示群首詞自己)
        if max_rows == 0:
            max_rows = 1
        
        # ------------------ 更新全局統計資料 ------------------
        # 更新群首詞統計
        if main_total != 0:
            global_main_term_count += 1
            global_main_term_sum += main_total
            if main_term not in global_total_words:
                global_total_words.add(main_term)
                global_total_sum += main_total
        
        # 更新各分類全局統計
        for json_key, title in categories:
            for word, cnt in cat_lists[json_key]:
                if word not in global_total_words:
                    global_total_words.add(word)
                    global_total_sum += cnt
                if word not in global_category_data[json_key]["words"]:
                    global_category_data[json_key]["words"].add(word)
                    global_category_data[json_key]["sum"] += cnt
        # -------------------------------------------------------
        
        # 計算該群首詞的「名相總個數」和「名相總筆數」
        count_nonzero = 0
        sum_total = 0
        if main_total != 0:
            count_nonzero += 1
            sum_total += main_total
        
        # 使用 set 避免重複計算相同的字詞 (僅針對此群)
        seen_words = set()
        for json_key, _ in categories:
            for word, cnt in cat_lists[json_key]:
                if word not in seen_words:
                    seen_words.add(word)
                    count_nonzero += 1
                    sum_total += cnt
        
        # 若全部都是 0，則跳過該群
        if count_nonzero == 0:
            continue
        
        # 產生詳細列
        group_detail_rows = []
        for i in range(max_rows):
            if i == 0:
                # 第一行帶入群首詞自己的資訊
                row = [
                    str(count_nonzero),
                    str(sum_total),
                    main_term,          # 群首詞
                    str(main_total)
                ]
            else:
                row = ["", "", "", ""]
            
            for json_key, title in categories:
                lst = cat_lists[json_key]
                if i < len(lst):
                    word, cnt = lst[i]
                    row.extend([word, str(cnt)])
                else:
                    row.extend(["", ""])
            
            group_detail_rows.append((row, False))
        
        group_rows.extend(group_detail_rows)
        
        # 產生統計行 (summary row)
        summary_row = []
        summary_row.append(str(count_nonzero))
        summary_row.append(str(sum_total))
        group_main_count = "1" if main_total > 0 else ""
        summary_row.append(group_main_count)  # 群首詞個數
        # print(f"[DEBUG] 群 '{main_term}' 的 main_total 為 {main_total}，設定群首詞個數為 {group_main_count}")
        summary_row.append(str(main_total))
       
        seen_category_words = set()
        for json_key, title in categories:
            items = cat_lists[json_key]
            unique_count = 0
            unique_sum = 0
            for word, cnt in items:
                if word not in seen_category_words:
                    seen_category_words.add(word)
                    unique_count += 1
                    unique_sum += cnt
            summary_row.append(str(unique_count))
            summary_row.append(str(unique_sum))
       
        group_rows.append((summary_row, True))
    
    # 產生全局 Aggregator
    aggregator = []
    aggregator.append(len(global_total_words))
    aggregator.append(global_total_sum)
    aggregator.append(global_main_term_count)
    aggregator.append(global_main_term_sum)
    for json_key, title in categories:
        aggregator.append(len(global_category_data[json_key]["words"]))
        aggregator.append(global_category_data[json_key]["sum"])
    
    top_header_row_1 = [
        "名相總個數", "名相總筆數",
        "群首詞個數", "群首詞筆數",
        "異體字個數", "異體字筆數",
        "音譯詞個數", "音譯詞筆數",
        "同義詞個數", "同義詞筆數",
        "複合詞個數", "複合詞筆數",
        "相關詞個數", "相關詞筆數"
    ]
    
    top_header_row_2 = []
    for val in aggregator:
        top_header_row_2.append(str(val) if val != 0 else "")
    
    headers = [
        "名相總個數", "名相總筆數",
        "群首詞", "群首詞筆數",
        "異體字", "異體字筆數",
        "音譯詞", "音譯詞筆數",
        "同義詞", "同義詞筆數",
        "複合詞", "複合詞筆數",
        "相關詞", "相關詞筆數"
    ]
    
    # 產生第一列 HTML（特殊背景）
    row1_html_cells = []
    for i, col in enumerate(top_header_row_1):
        if i % 2 == 0:
            bg_color = "#1E4477"
        else:
            bg_color = "#B58500"
        cell_html = f'<th style="border:1pt solid #000; color:#FFF; font-weight:bold; background-color:{bg_color};">{col}</th>'
        row1_html_cells.append(cell_html)
    row1_html = "<tr>" + "".join(row1_html_cells) + "</tr>"
    
    # 第二列 HTML
    row2_html_cells = []
    for val in top_header_row_2:
        cell_html = f'<th style="border:1pt solid #000; color:black; font-weight:bold; background-color:#FFF;">{val}</th>'
        row2_html_cells.append(cell_html)
    row2_html = "<tr>" + "".join(row2_html_cells) + "</tr>"
    
    # 第三列 HTML
    row3_html_cells = []
    for h in headers:
        cell_html = f'<th style="border:1pt solid #000; color:black; font-weight:bold; background-color:#D9D9D9;">{h}</th>'
        row3_html_cells.append(cell_html)
    row3_html = "<tr>" + "".join(row3_html_cells) + "</tr>"
    
    # 逐行產生資料 HTML
    row_html_list = []
    # 定義需要檢查字詞顏色的欄位索引：群首詞以及各分類字詞欄 (0-based index: 2,4,6,8,10,12)
    word_col_indices = {2, 4, 6, 8, 10, 12}
    for row, is_summary in group_rows:
        for i in range(len(row)):
            if row[i].strip() == "0":
                row[i] = ""
        
        # 非 summary row，根據 key_list 調整特定欄位字詞顏色
        if not is_summary:
            new_cells = []
            for i, cell in enumerate(row):
                cell_content = cell.strip()
                # 判斷是否為要檢查的字詞欄位且非空
                if i in word_col_indices and cell_content:
                    if cell_content in key_list:
                        if i == 2:
                            new_cells.append(f'<span style="font-weight: bold; color: blue;">{cell_content}</span>')
                        else:
                            new_cells.append(f'<span style="color: blue;">{cell_content}</span>')
                    else:
                        if i == 2:
                            new_cells.append(f'<span style="font-weight: bold; color: black;">{cell_content}</span>')
                        else:
                            new_cells.append(f'<span style="color: black;">{cell_content}</span>')
                else:
                    new_cells.append(cell_content)
            row_cells = new_cells
        else:
            row_cells = row
        
        if is_summary:
            row_html = (
                "<tr style='font-weight: bold;'>"
                + "".join(f"<td style='background-color: #F0FAFF;'>{cell}</td>" for cell in row_cells)
                + "</tr>"
            )
        else:
            row_html = "<tr>" + "".join(f"<td>{cell}</td>" for cell in row_cells) + "</tr>"
        
        row_html_list.append(row_html)
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>佛經詞表彙整</title>
<style>
  table {{
    border-collapse: collapse;
    width: 100%;
  }}
  thead {{
    position: sticky;
    top: 0;
    z-index: 999;
  }}
  tbody td {{
    border: 1px solid #000;
    padding: 4px;
    text-align: center;
    background-color: #ffffff;
  }}
</style>
</head>
<body>
<table>
  <thead>
    {row1_html}
    {row2_html}
    {row3_html}
  </thead>
  <tbody>
    {''.join(row_html_list)}
  </tbody>
</table>
</body>
</html>
"""
    html_dir = os.path.dirname(html_output_path)
    if not os.path.exists(html_dir):
        os.makedirs(html_dir)
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"已產生 {html_output_path}")
    # return aggregator, group_rows
    return aggregator


# ------------------- 測試呼叫範例 -------------------
if __name__ == "__main__":
    # 測試時請自行修正路徑
    json_path = r"D:\cbeta_v3\output\cache_title_json\T0848.json"
    html_path = r"D:\cbeta_v3\output\test_title_html\T0848.html"
    # 測試時額外傳入一個 key_list，例：['一字金輪佛頂', '其他字詞']
    test_key_list = ['一字金輪佛頂', '其他字詞']
    generate_one_html(json_path, html_path, test_key_list)
    print(f"已產生 {html_path}，請用瀏覽器開啟查看。")
