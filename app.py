# 2025-0328_1905
# 調整組裝 book_list 的邏輯, 不再限定 values 為 list 且長度 >=2, 以便顯示更多選項, 更新 UPDATE_DATE

import json
import os
import re  # 用於提取表格內容
import logging
from flask import Flask, render_template_string, Response, send_file
import csv
from io import StringIO
from openpyxl import Workbook
import tempfile

UPDATE_DATE = '2025/04/04'  # 更新日期

MY_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_HTML_DIR = os.path.join(MY_SCRIPT_DIR, 'cache')
BOOKS_JSON_PATH = os.path.join(MY_SCRIPT_DIR, 'titles', 'titles.json')

app = Flask(__name__)

# 設定 DEBUG 等級，方便除錯
logging.basicConfig(level=logging.DEBUG)

try:
    with open(BOOKS_JSON_PATH, 'r', encoding='utf-8') as f:
        books_data = json.load(f)
    app.logger.info(f"成功讀取 titles.json: {BOOKS_JSON_PATH}")
except Exception as e:
    app.logger.error(f"讀取 titles.json 發生錯誤: {e}")
    books_data = {}

book_list = {}
for docx, inner in books_data.items():
    app.logger.info(f"處理檔案: {docx}")
    for code, values in inner.items():
        # 原本只處理 (list, len>=2)，現在改為所有都加入
        if isinstance(values, list):
            if len(values) >= 2:
                # 取第二個元素作標題
                book_list[code] = values[1]
            elif len(values) == 1:
                # 只有一個元素，直接作標題
                book_list[code] = values[0]
            else:
                book_list[code] = "(無標題)"
        else:
            book_list[code] = str(values)

formatted_books = []
for code, title in sorted(book_list.items()):
    # 格式化選項，例如 "(code) title"
    formatted_books.append(f"({code}) {title}")

app.logger.info(f"總共 {len(formatted_books)} 個選項")

@app.route("/get_result/<code>")
def get_result(code):
    app.logger.debug(f"進入 get_result, code={code}")
    target = code.lower() + ".html"
    html_dir = CACHE_HTML_DIR

    if not os.path.isdir(html_dir):
        app.logger.debug(f"cache 目錄不存在: {html_dir}")
        return f"<p>找不到 cache 目錄: {html_dir}</p>"

    found_file = None
    for file in os.listdir(html_dir):
        if file.lower() == target:
            found_file = file
            break

    if not found_file:
        app.logger.debug(f"找不到對應檔案: {target} (在 {html_dir} 內)")
        return f"<p>找不到結果檔案: {target}</p>"

    fullpath = os.path.join(html_dir, found_file)
    try:
        with open(fullpath, "r", encoding="utf-8") as f:
            content = f.read()
        app.logger.debug(f"成功讀取 {found_file}, 檔案大小 {len(content)} bytes")
        # 修改：只提取 <table>…</table> 內容，作為嵌入片段
        match = re.search(r'(?is)<table.*?</table>', content)
        if match:
            content = match.group(0)
        return content
    except Exception as e:
        app.logger.error(f"讀檔案失敗: {e}")
        return f"<p>讀檔案失敗: {e}</p>"

@app.route("/download_csv")
def download_csv():
    app.logger.debug("download_csv() - 準備匯出 CSV")
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Code", "Title"])
    for entry in formatted_books:
        writer.writerow([entry])
    output = si.getvalue()
    si.close()
    return Response(
        '\ufeff' + output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=books.csv"}
    )

@app.route("/download_xlsx")
def download_xlsx():
    app.logger.debug("download_xlsx() - 準備匯出 XLSX")
    wb = Workbook()
    ws = wb.active
    ws.title = "清單"
    ws.append(["CodeAndTitle"])
    for entry in formatted_books:
        ws.append([entry])

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(tmp.name)
    tmp.seek(0)
    return send_file(
        tmp.name,
        as_attachment=True,
        download_name="books.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# 修改：將表格 sticky header 所需的 CSS 與 JavaScript 移到主頁模板中
template = '''
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>經文名相查詢資料庫 - Debug Log示範</title>
  <script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
  <style>
    body { margin: 0; padding: 0; }
    .fixed-header {
      position: sticky;
      top: 0;
      background-color: #fff;
      z-index: 1000;
      padding: 1rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    h1 { font-size: 24px; font-weight: bold; margin: 0; }
    .update-date { color: gray; font-size: 14px; }
    .top-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 1rem;
    }
    .input-group {
      display: flex;
      align-items: center;
    }
    .dropdown-container { 
      position: relative; 
      width: 50vw;
    }
    .input-wrapper {
      display: flex;
      align-items: center;
    }
    #searchInput {
      flex: 1;
      font-size: 16px;
      padding: 2px;
      box-sizing: border-box;
    }
    #toggleDropdown {
      padding: 2px 8px;
      cursor: pointer;
    }
    #dropdown {
      position: absolute; 
      top: 110%; 
      left: 0;
      width: 100%;
      background-color: white; 
      border: 1px solid #ccc; 
      max-height: 150px;
      overflow-y: auto; 
      display: none; 
      z-index: 999;
    }
    #dropdown div { padding: 4px; cursor: pointer; }
    #dropdown div:hover { background-color: lightyellow; }
    #dropdown div.autocomplete-active {
      background-color: lightyellow;
    }
    .button-group { 
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }
    /* 結果區域無額外間隔 */
    #resultContainer {
      margin-top: 0;
      padding-top: 0;
    }
    /* 表格樣式：將表頭設為 sticky，由 JavaScript 動態調整 top 值 */
    table {
      border-collapse: collapse;
      width: 100%;
    }
    thead th {
      position: sticky;
      background: inherit;
    }
    tbody td {
      border: 1px solid #000;
      padding: 4px;
      text-align: center;
      background-color: #ffffff;
    }
  </style>
  <script>
    // 原有的下拉選單與匯出功能程式碼保持不變
    var options = {{ options|tojson }};
    var currentFocus = -1;
    var prevInput = "";

    document.addEventListener("DOMContentLoaded", function(){
      console.log("Debug: options from server:", options);
      var searchInput = document.getElementById("searchInput");
      var dropdown = document.getElementById("dropdown");

      searchInput.addEventListener("keydown", function(e){
        var items = dropdown.getElementsByTagName("div");
        if(e.keyCode===40){ 
          currentFocus++;
          addActive(items);
          e.preventDefault();
        } else if(e.keyCode===38){ 
          currentFocus--;
          addActive(items);
          e.preventDefault();
        } else if(e.keyCode===13){
          e.preventDefault();
          if(currentFocus > -1 && items.length > 0){
            console.log("Debug: Enter on item:", items[currentFocus].textContent);
            items[currentFocus].click();
          }
        } else if(e.keyCode===27){
          e.preventDefault();
          clearInput();
        }
      });

      document.getElementById("toggleDropdown").addEventListener("click", function(){
        if(dropdown.style.display === "block"){
          dropdown.style.display = "none";
        } else {
          if(searchInput.value.trim() === ""){
            populateDropdown(options);
          } else {
            filterOptions();
          }
        }
      });

      // 每次載入後、以及畫面調整時，自動調整表格表頭的 sticky top 值
      adjustStickyHeaders();
    });

    // 下拉選單相關函式保持不變
    function populateDropdown(optionList){
      var dropdown = document.getElementById("dropdown");
      dropdown.innerHTML = "";
      var items = [];
      optionList.forEach(function(opt){
        var div = document.createElement("div");
        div.textContent = opt;
        div.onclick = function(){
          console.log("Debug: Clicked option:", opt);
          document.getElementById("searchInput").value = opt;
          dropdown.style.display = "none";
          var codeMatch = opt.match(/\\((.*?)\\)/);
          if(codeMatch && codeMatch[1]){
            fetchResult(codeMatch[1]);
          }
        };
        dropdown.appendChild(div);
        items.push(div);
      });
      dropdown.style.display = "block";
      if(items.length > 0){
        currentFocus = 0;
        addActive(items, false);
      }
    }

    function filterOptions(){
      var input = document.getElementById("searchInput");
      var currentVal = input.value;
      var dropdown = document.getElementById("dropdown");
      if(currentVal !== prevInput){
        currentFocus = -1; 
        prevInput = currentVal;
      }
      dropdown.innerHTML = "";
      if(currentVal.trim() === ""){
        populateDropdown(options);
        return;
      }
      var matched = options.filter(function(opt){
        return opt.toLowerCase().indexOf(currentVal.toLowerCase()) > -1;
      });
      if(matched.length > 0){
        populateDropdown(matched);
      } else {
        dropdown.style.display = "none";
      }
    }

    function addActive(x, updateInput = true){
      if(!x) return false;
      removeActive(x);
      if(currentFocus >= x.length) currentFocus = 0;
      if(currentFocus < 0) currentFocus = x.length - 1;
      x[currentFocus].classList.add("autocomplete-active");
      if(updateInput){
        document.getElementById("searchInput").value = x[currentFocus].textContent;
      }
      x[currentFocus].scrollIntoView({block:"nearest"});
    }
    function removeActive(x){
      for(var i = 0; i < x.length; i++){
        x[i].classList.remove("autocomplete-active");
      }
    }
    function clearInput(){
      document.getElementById("searchInput").value = "";
      document.getElementById("dropdown").style.display = "none";
      document.getElementById("resultContainer").innerHTML = "";
    }

    function downloadCSV() {
      window.location.href = "/download_csv";
    }

    function downloadXLSX() {
      var container = document.getElementById("resultContainer");
      var table = container.querySelector("table");
      if (!table) {
        alert("找不到搜尋結果表格！");
        return;
      }
      var wb = XLSX.utils.book_new();
      var ws = XLSX.utils.table_to_sheet(table);
      XLSX.utils.book_append_sheet(wb, ws, "查詢結果");
      XLSX.writeFile(wb, "result.xlsx");
    }      

    function fetchResult(code){
      console.log("Debug: fetchResult code=", code);
      fetch("/get_result/" + code.toLowerCase())
        .then(function(resp){ return resp.text(); })
        .then(function(data){
          console.log("Debug: /get_result response:", data);
          document.getElementById("resultContainer").innerHTML = data;
          // 每次載入結果後也調整表頭 sticky top 值
          adjustStickyHeaders();
        })
        .catch(function(err){
          console.error("Debug: fetch error:", err);
          document.getElementById("resultContainer").innerHTML = "取得結果失敗: " + err;
        });
    }

    // 新增：根據上方固定區域高度動態調整表格前三列的 sticky top 值
    function adjustStickyHeaders(){
      // 取得上方固定區域高度；若不存在則預設 0
      var fixedHeader = document.querySelector(".fixed-header");
      var fixedHeight = fixedHeader ? fixedHeader.getBoundingClientRect().height : 0;
      
      // 取得表格前三列的 th 集合
      var row1Ths = document.querySelectorAll("thead tr:nth-child(1) th");
      var row2Ths = document.querySelectorAll("thead tr:nth-child(2) th");
      var row3Ths = document.querySelectorAll("thead tr:nth-child(3) th");
      
      if (row1Ths.length > 0) {
        var row1Height = row1Ths[0].getBoundingClientRect().height;
        row1Ths.forEach(function(th) {
          th.style.top = fixedHeight + "px";
        });
        if (row2Ths.length > 0) {
          var row2Height = row2Ths[0].getBoundingClientRect().height;
          row2Ths.forEach(function(th) {
            th.style.top = (fixedHeight + row1Height) + "px";
          });
          if (row3Ths.length > 0) {
            row3Ths.forEach(function(th) {
              th.style.top = (fixedHeight + row1Height + row2Height) + "px";
            });
          }
        }
      }
    }

    window.addEventListener("load", adjustStickyHeaders);
    window.addEventListener("resize", adjustStickyHeaders);
  </script>
</head>
<body>
  <div class="fixed-header">
    <h1>經文名相查詢 <span class="update-date">(更新日期: {{ update_date }})</span></h1>
    <div class="top-bar">
      <div class="input-group">
        <label>輸入經名：</label>
        <div class="dropdown-container">
          <div class="input-wrapper">
            <input type="text" id="searchInput" oninput="filterOptions()" placeholder="請輸入關鍵字...">
            <span id="toggleDropdown">&#9660;</span>
          </div>
          <div id="dropdown"></div>
        </div>
      </div>
      <div class="button-group">
        <button onclick="clearInput()">清除</button>
        <button id="downloadXLSXButton" onclick="downloadXLSX()">下載 XLSX 檔案</button>
        <button style="display:none" onclick="alert('下載 CSV...')">下載 CSV 檔</button>
      </div>
    </div>
  </div>
  <!-- 移除 <hr>，結果區僅由 #resultContainer 控制間隔 -->
  <div id="resultContainer"></div>
</body>
</html>
'''

@app.route("/")
def index():
    app.logger.debug(f"index() - 傳給前端的 options 長度: {len(formatted_books)}")
    return render_template_string(template, options=formatted_books, update_date=UPDATE_DATE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
