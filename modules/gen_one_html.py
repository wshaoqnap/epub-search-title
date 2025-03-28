import json


def generate_one_html(json_path, html_output_path):
    """
    讀取指定的 JSON 檔案，產生 HTML 表格，並將固定區域（上面三列：第一列、第二列、第三列）與捲動區域（第四列以後）分開，
    同時保留所有固定區域的黑色格線，以及使上下兩塊區域的欄位寬度一致。
    """
    # 讀取 JSON 檔案
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 定義各分類對應的 JSON 鍵與輸出欄位標題（順序決定輸出順序）
    categories = [
        ("異體字", "異體字"),
        ("同義詞/近義詞(意譯)", "同義詞"),
        ("複合詞", "複合詞"),
        ("相關詞", "相關詞"),
        ("音譯詞", "音譯詞")
    ]
    
    # 用來存放所有群首詞的資料列，格式：(row, is_summary)
    group_rows = []
    
    # 依據 JSON 中每個主詞依 id 排序（假設 id 為數字型字串）
    sorted_terms = sorted(data.items(), key=lambda kv: int(kv[1].get("id", "0")))
    
    # 處理每一個群首詞
    for main_term, info in sorted_terms:
        try:
            main_total = int(info.get("found", {}).get("total", 0))
        except:
            main_total = 0
        
        # 針對每個分類，取得 (字詞, 筆數) 的 list（只加入 total 不為 0 的項目）
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
        if max_rows == 0:
            max_rows = 1
        
        # 計算統計：包括群首詞本身及各分類中非零項目
        count_nonzero = 0
        sum_total = 0
        if main_total != 0:
            count_nonzero += 1
            sum_total += main_total
        for json_key, _ in categories:
            for word, cnt in cat_lists[json_key]:
                count_nonzero += 1
                sum_total += cnt
        if count_nonzero == 0:
            continue
        
        # 產生詳細資料列，第一行顯示前四欄，其他行前四欄空白
        group_detail_rows = []
        for i in range(max_rows):
            if i == 0:
                row = [str(count_nonzero), str(sum_total), main_term, str(main_total)]
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
    
        # 新增統計行 (summary row)
        summary_row = [str(count_nonzero), str(sum_total), "1", str(main_total)]
        for json_key, title in categories:
            items = cat_lists[json_key]
            cat_count = len(items)
            cat_sum = sum(cnt for word, cnt in items)
            summary_row.extend([str(cat_count), str(cat_sum)])
        group_rows.append((summary_row, True))
    
    # -------------------------------
    # 定義固定區域與捲動區域共用的 colgroup
    # 這裡有14個欄位，每欄寬度均設定為 (100/14)% ≈ 7.14%
    colgroup_html = "<colgroup>" + "".join(f'<col style="width:{100/14:.2f}%;">' for _ in range(14)) + "</colgroup>"
    
    # 固定區域：包含第一列、第二列、第三列 (固定表頭)
    # 第一列：固定文字 (A1~N1)
    extra_header1 = [
        "名相總個數", "名相總筆數", "群首詞個數", "群首詞筆數",
        "異體字個數", "異體字筆數", "同義詞個數", "同義詞筆數",
        "複合詞個數", "複合詞筆數", "相關詞個數", "相關詞筆數",
        "音譯詞個數", "音譯詞筆數"
    ]
    extra_header1_cells = ""
    for idx, h in enumerate(extra_header1):
        if idx % 2 == 0:
            extra_header1_cells += f'<th style="font-weight: bold; color: white; background-color: #00008B; border:1px solid black; height:40px;">{h}</th>'
        else:
            extra_header1_cells += f'<th style="font-weight: bold; color: white; background-color: #B8860B; border:1px solid black; height:40px;">{h}</th>'
    fixed_row1 = f"<tr>{extra_header1_cells}</tr>"
    
    # 第二列：所有群首詞 summary_row 的加總，背景白色，並在下邊框使用粗黑線
    total_summary = [0] * 14
    for row, is_summary in group_rows:
        if is_summary:
            for i, cell in enumerate(row):
                try:
                    total_summary[i] += int(cell)
                except:
                    pass
    extra_header2 = [str(x) for x in total_summary]
    extra_header2_cells = "".join(f'<th style="border:1px solid black; background-color:white; height:40px;">{h}</th>' for h in extra_header2)
    fixed_row2 = f"<tr style='border-bottom:4px solid black;'>{extra_header2_cells}</tr>"
    
    # 第三列：原有表頭，背景為淺灰 (#f0f0f0)
    headers = [
        "名相總個數", "名相總筆數", "群首詞", "群首詞筆數",
        "異體字", "異體字筆數", "同義詞", "同義詞筆數",
        "複合詞", "複合詞筆數", "相關詞", "相關詞筆數",
        "音譯詞", "音譯詞筆數"
    ]
    header_cells = "".join(f'<th style="border:1px solid black; background-color:#f0f0f0; height:40px;">{h}</th>' for h in headers)
    fixed_row3 = f"<tr>{header_cells}</tr>"
    
    fixed_header_table = f"""
    <table style="table-layout: fixed; border-collapse: collapse; width: 100%;">
      {colgroup_html}
      <thead>
        {fixed_row1}
        {fixed_row2}
        {fixed_row3}
      </thead>
    </table>
    """
    
    # 捲動區域：包含所有資料列，使用相同 colgroup 與 table-layout: fixed
    row_html_list = []
    for row, is_summary in group_rows:
        try:
            new_row = [("" if cell.strip() == "0" else cell) for cell in row]
            if not is_summary and new_row[2].strip():
                new_row[2] = f'<span style="font-weight: bold; color: blue;">{new_row[2]}</span>'
            if is_summary:
                row_html = '<tr style="font-weight: bold; background-color: #F0F8FF;">' + "".join(f"<td style='border:1px solid black; height:40px;'>{cell}</td>" for cell in new_row) + "</tr>"
            else:
                row_html = "<tr>" + "".join(f"<td style='border:1px solid black; height:40px;'>{cell}</td>" for cell in new_row) + "</tr>"
            row_html_list.append(row_html)
        except Exception as e:
            print(f"處理資料列時發生錯誤: {e}")
            continue
    data_table = f"""
    <table style="table-layout: fixed; border-collapse: collapse; width: 100%;">
      {colgroup_html}
      <tbody>
        {''.join(row_html_list)}
      </tbody>
    </table>
    """
    
    # 最終 HTML：固定區域與捲動區域分開
    html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>佛經詞表彙整</title>
<style>
  body {{
    margin: 0;
    padding: 0;
  }}
  .fixed-header {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background-color: white;
    z-index: 100;
  }}
  .scrollable-body {{
    margin-top: 120px; /* 固定區域高度 */
    overflow-y: auto;
    height: calc(100vh - 120px);
  }}
  table {{
    width: 100%;
  }}
</style>
</head>
<body>
  <div class="fixed-header">
    {fixed_header_table}
  </div>
  <div class="scrollable-body">
    {data_table}
  </div>
</body>
</html>
"""
    
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"已產生 {html_output_path}")

