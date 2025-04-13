"""
本程式修改內容：
1. 頁面首次載入或重新整理時，強制將右側區域隱藏，並將切換按鈕文字設為「顯示側邊欄」。
2. 當切換右側側邊欄時，依據變動後的寬度重新計算左側表格固定前三列的 top 值。
3. 當下拉選單選定後，左側顯示表格內容，並在使用者以滑鼠左鍵點擊表格內（非表頭且非純數字）的儲存格時，
   右側區域自動顯示。右側區域分為上下兩個部分，由水平分隔線分隔：
      - 上半部 (upperRightPanel)：顯示預設備註 (.txt) 檔內容，但最上方先顯示左側點選的字詞（暗紅色粗體），
        其下方以細體黑字呈現 .txt 內容。
      - 下半部 (lowerRightPanel)：亦顯示點選的字詞（暗紅色粗體）。
4. 拖曳分隔線時，左側寬度改變會重新計算固定表頭；右側水平分隔線可上下移動以調整上下區域高度。
5. fetchResult 函式加入 response.ok 檢查，提供更明確錯誤訊息。
6. 全域監聽 ESC 鍵，按下 ESC 鍵時會呼叫 clearInput() 清除左側表格內容與下拉選單內容。
7. 調整右側預設上下高度比例為2:1 (上半部 66.67%, 下半部 33.33%)，並將分隔線高度調整為 2pt。
"""

import json
import os
import re  # 用於提取表格內容
import logging
from flask import Flask, render_template_string, Response, send_file
import csv
from io import StringIO
from openpyxl import Workbook
import tempfile

UPDATE_DATE = '2025/04/13'  # 更新日期

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
for docx in books_data:
    app.logger.info(f"處理檔案: {docx}")
    for code, values in books_data[docx].items():
        if isinstance(values, list):
            if len(values) >= 2:
                book_list[code] = values[1]
            elif len(values) == 1:
                book_list[code] = values[0]
            else:
                book_list[code] = "(無標題)"
        else:
            book_list[code] = str(values)

formatted_books = []
for code, title in sorted(book_list.items()):
    formatted_books.append(f"({code}) {title}")

app.logger.info(f"總共 {len(formatted_books)} 個選項")

# 新增：預設備註資料夾變數
DEFAULT_NOTES_DIR = os.path.join(MY_SCRIPT_DIR, 'default_notes')

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

# 新增：取得預設備註檔內容的路由
@app.route("/get_default_note/<word>")
def get_default_note(word):
    """
    透過傳入的字詞 (word) 組合預設備註檔案路徑，讀取並回傳 .txt 檔案內容。
    """
    note_path = os.path.join(DEFAULT_NOTES_DIR, f"{word}.txt")
    if not os.path.exists(note_path):
        app.logger.debug(f"找不到預設備註檔：{note_path}")
        return ""
    try:
        with open(note_path, "r", encoding="utf-8") as f:
            note_content = f.read()
        app.logger.debug(f"成功讀取預設備註檔：{note_path}")
        return note_content
    except Exception as e:
        app.logger.error(f"讀取預設備註檔失敗：{e}")
        return ""

# 前端模板：包含左右版面切割、拖曳分隔線、右側隱藏/顯示切換、右側水平分隔線（可拖曳調整上下區域）及固定表頭更新功能
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
      gap: 8px;
    }
    /* 右側隱藏/顯示按鈕 */
    #toggleSidebarBtn {
      cursor: pointer;
      padding: 4px 8px;
      border: none;
      background-color: #ddd;
      border-radius: 4px;
    }
    /* 主容器與左右面板 */
    #mainContainer {
      display: flex;
      height: calc(100vh - 150px);
      border-top: 1px solid #ccc;
    }
    #leftPanel, #rightPanel {
      overflow: auto;
      padding: 10px;
    }
    #leftPanel {
      width: 75%;
      padding-top: 0;
    }
    /* 右側面板以 flex 垂直排列子元件 */
    #rightPanel {
      width: 25%;
      display: none;
      flex-direction: column;
      height: 100%;
    }
    /* 右側上半部（顯示 .txt 內容，並在最上方也顯示選取字詞） */
    #upperRightPanel {
      height: 66.67%;
      overflow: auto;
      border-bottom: 1px solid #ccc;
    }
    /* 右側水平分隔線 (改為 4pt) */
    #horizontalDivider {
      height: 4pt;
      background-color: #333;
      cursor: row-resize;
    }
    /* 右側下半部（顯示選取字詞，暗紅色粗體） */
    #lowerRightPanel {
      height: 33.33%;
      overflow: auto;
    }
    /* 左側結果區 */
    #resultContainer {
      margin-top: 0;
      padding-top: 0;
    }
    /* 分隔線（左右） */
    #divider {
      width: 5px;
      background-color: #333;
      cursor: col-resize;
    }
    /* 表格 */
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
    // 全域監聽 ESC 鍵：按下 ESC 清除左側表格與下拉選單內容
    window.addEventListener("keydown", function(e) {
      if(e.key === "Escape" || e.keyCode === 27) {
        console.log("Debug: ESC 鍵按下，清除內容");
        clearInput();
      }
    });

    var options = {{ options|tojson }};
    var currentFocus = -1;
    var prevInput = "";
    var lastRightWidthPercent = 25; // 初始右側區域寬度記錄 (25%)

    
    document.addEventListener("DOMContentLoaded", function(){
      // 強制隱藏右側區域，並將左側設為 100%、按鈕文字設為「顯示側邊欄」
      document.getElementById("rightPanel").style.display = "none";
      document.getElementById("leftPanel").style.width = "100%";
      document.getElementById("toggleSidebarBtn").textContent = "顯示側邊欄";

      console.log("Debug: options from server:", options);
      var searchInput = document.getElementById("searchInput");
      var dropdown = document.getElementById("dropdown");

      searchInput.addEventListener("keydown", function(e){
        var items = dropdown.getElementsByTagName("div");
        if(e.keyCode === 40){ 
          currentFocus++;
          addActive(items);
          e.preventDefault();
        } else if(e.keyCode === 38){ 
          currentFocus--;
          addActive(items);
          e.preventDefault();
        } else if(e.keyCode === 13){
          e.preventDefault();
          if(currentFocus > -1 && items.length > 0){
            console.log("Debug: Enter on item:", items[currentFocus].textContent);
            items[currentFocus].click();
          }
        } else if(e.keyCode === 27){
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

      // 初次載入時調整左側表格固定表頭
      adjustStickyHeaders();

      // 拖曳左右分隔線功能
      const divider = document.getElementById('divider');
      const leftPanel = document.getElementById('leftPanel');
      const rightPanel = document.getElementById('rightPanel');
      const mainContainer = document.getElementById('mainContainer');
      let isResizing = false;

      divider.addEventListener('mousedown', function(e) {
        isResizing = true;
        console.log("Debug: 開始拖曳分隔線，初始位置：" + e.clientX);
      });

      document.addEventListener('mousemove', function(e) {
        if (!isResizing) return;
        let containerOffsetLeft = mainContainer.getBoundingClientRect().left;
        let pointerRelativeXpos = e.clientX - containerOffsetLeft;
        let containerWidth = mainContainer.getBoundingClientRect().width;
        let leftWidthPercent = (pointerRelativeXpos / containerWidth) * 100;
        if (leftWidthPercent < 20) leftWidthPercent = 20;
        if (leftWidthPercent > 100) leftWidthPercent = 100;
        leftPanel.style.width = leftWidthPercent + '%';
        if(rightPanel.style.display !== "none") {
          let newRightWidthPercent = 100 - leftWidthPercent;
          rightPanel.style.width = newRightWidthPercent + '%';
          lastRightWidthPercent = newRightWidthPercent;
        } else {
          rightPanel.style.width = "0%";
        }
        console.log("Debug: 拖曳中，左側寬度：" + leftWidthPercent.toFixed(2) + "%");
        adjustStickyHeaders();
      });

      document.addEventListener('mouseup', function(e) {
        if (isResizing) {
          console.log("Debug: 結束拖曳分隔線");
        }
        isResizing = false;
      });

      // 右側水平分隔線拖曳功能
      const horizontalDivider = document.getElementById('horizontalDivider');
      const upperRightPanel = document.getElementById('upperRightPanel');
      const lowerRightPanel = document.getElementById('lowerRightPanel');
      let isResizingRight = false;

      horizontalDivider.addEventListener('mousedown', function(e) {
        isResizingRight = true;
        console.log("Debug: 開始拖曳右側水平分隔線，初始位置：" + e.clientY);
      });

      document.addEventListener('mousemove', function(e) {
        if (!isResizingRight) return;
        let rightPanelRect = document.getElementById('rightPanel').getBoundingClientRect();
        let offsetY = e.clientY - rightPanelRect.top;
        const minHeight = 20;
        const maxHeight = rightPanelRect.height - 20 - horizontalDivider.offsetHeight;
        if (offsetY < minHeight) offsetY = minHeight;
        if (offsetY > maxHeight) offsetY = maxHeight;
        upperRightPanel.style.height = offsetY + "px";
        lowerRightPanel.style.height = (rightPanelRect.height - offsetY - horizontalDivider.offsetHeight) + "px";
        console.log("Debug: 右側水平分隔線移動, 上區高度：" + offsetY + "px");
      });

      document.addEventListener('mouseup', function(e) {
        if (isResizingRight) {
          console.log("Debug: 結束拖曳右側水平分隔線");
        }
        isResizingRight = false;
      });

      // 點擊左側表格儲存格時，顯示右側區域並更新右側上下區域內容
      document.getElementById("resultContainer").addEventListener("click", function(e){
        var td = e.target.closest("td");
        if(!td) return;
        if(td.closest("thead")) return;
        var text = td.innerText.trim();
        if(text === "" || !isNaN(Number(text))) return;
        var rightPanel = document.getElementById("rightPanel");
        var leftPanel = document.getElementById("leftPanel");
        if(rightPanel.style.display === "none" || rightPanel.style.display === ""){
             rightPanel.style.display = "flex";
             leftPanel.style.width = (100 - lastRightWidthPercent) + '%';
             rightPanel.style.width = lastRightWidthPercent + '%';
             document.getElementById("toggleSidebarBtn").textContent = "隱藏側邊欄";
             adjustStickyHeaders();
        }
        var computedStyle = window.getComputedStyle(td);
        var fontSize = computedStyle.fontSize;
        var upperPanel = document.getElementById("upperRightPanel");
        var lowerPanel = document.getElementById("lowerRightPanel");
        // 下半部依然顯示選取字詞（暗紅色粗體）
        lowerPanel.innerHTML = '<div style="color: darkred; font-weight: bold; font-size: ' + fontSize + ';">' + text + '</div>';
        
        // 透過 fetch 讀取預設備註內容，將上半部更新為：先顯示選取字詞，再顯示 .txt 檔案內容（細體黑字）
        fetch("/get_default_note/" + encodeURIComponent(text))
          .then(function(resp) {
              if (!resp.ok) {
                  throw new Error("HTTP error " + resp.status);
              }
              return resp.text();
          })
          .then(function(noteContent) {
              upperPanel.innerHTML = 
                  '<div style="color: darkred; font-weight: bold; font-size: ' + fontSize + ';">' + text + '</div>' +
                  '<div style="color: black; font-weight: normal; font-size: ' + fontSize + ';">' + noteContent + '</div>';
          })
          .catch(function(err){
              console.error("讀取預設備註失敗:", err);
              upperPanel.innerHTML = '<div style="color: darkred; font-weight: bold; font-size: ' + fontSize + ';">' + text + '</div>';
          });
      });
    });

    // 右側隱藏/顯示切換功能
    function toggleRightPanel(){
      var rightPanel = document.getElementById("rightPanel");
      var divider = document.getElementById("divider");
      var leftPanel = document.getElementById("leftPanel");
      var btn = document.getElementById("toggleSidebarBtn");
      if(rightPanel.style.display === "none" || rightPanel.style.display === ""){
           rightPanel.style.display = "flex";
           divider.style.display = "block";
           leftPanel.style.width = (100 - lastRightWidthPercent) + '%';
           rightPanel.style.width = lastRightWidthPercent + '%';
           btn.textContent = "隱藏側邊欄";
           adjustStickyHeaders();
      } else {
           lastRightWidthPercent = parseFloat(rightPanel.style.width) || lastRightWidthPercent;
           rightPanel.style.display = "none";
           divider.style.display = "none";
           leftPanel.style.width = "100%";
           btn.textContent = "顯示側邊欄";
           adjustStickyHeaders();
      }
    }

    // 下拉選單相關函式
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

    // fetchResult 改進：加入 response.ok 檢查
    function fetchResult(code){
      console.log("Debug: fetchResult code=", code);
      fetch("/get_result/" + code.toLowerCase())
        .then(function(resp){
          if (!resp.ok) {
            throw new Error("HTTP error " + resp.status);
          }
          return resp.text();
        })
        .then(function(data){
          console.log("Debug: /get_result response:", data);
          document.getElementById("resultContainer").innerHTML = data;
          adjustStickyHeaders();
        })
        .catch(function(err){
          console.error("Debug: fetch error:", err);
          document.getElementById("resultContainer").innerHTML = "取得結果失敗: " + err;
        });
    }

    // 固定表頭：僅針對左側面板內表格，根據最新寬度重新計算 top 值
    function adjustStickyHeaders(){
      var leftPanel = document.getElementById("leftPanel");
      var baseOffset = 0;
      var row1Ths = leftPanel.querySelectorAll("table thead tr:nth-child(1) th");
      var row2Ths = leftPanel.querySelectorAll("table thead tr:nth-child(2) th");
      var row3Ths = leftPanel.querySelectorAll("table thead tr:nth-child(3) th");
      if (row1Ths.length > 0) {
        var row1Height = row1Ths[0].getBoundingClientRect().height;
        row1Ths.forEach(function(th) {
          th.style.top = baseOffset + "px";
        });
        if (row2Ths.length > 0) {
          var row2Height = row2Ths[0].getBoundingClientRect().height;
          row2Ths.forEach(function(th) {
            th.style.top = (baseOffset + row1Height) + "px";
          });
          if (row3Ths.length > 0) {
            row3Ths.forEach(function(th) {
              th.style.top = (baseOffset + row1Height + row2Height) + "px";
            });
          }
        }
      }
    }
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
        <button id="toggleSidebarBtn" onclick="toggleRightPanel()">顯示側邊欄</button>
        <button onclick="clearInput()">清除</button>
        <button id="downloadXLSXButton" onclick="downloadXLSX()">下載 XLSX 檔案</button>
        <button style="display:none" onclick="alert('下載 CSV...')">下載 CSV 檔</button>
      </div>
    </div>
  </div>
  <!-- 主容器：左右兩側版面 -->
  <div id="mainContainer">
    <div id="leftPanel">
      <div id="resultContainer"></div>
    </div>
    <div id="divider"></div>
    <!-- 右側區域：分為上下兩部分 -->
    <div id="rightPanel">
      <div id="upperRightPanel">
        <!-- 預設備註內容及選取字詞（上半部）將顯示在此 -->
      </div>
      <div id="horizontalDivider"></div>
      <div id="lowerRightPanel">
        <!-- 選取的字詞（暗紅色粗體，下半部）將顯示在此 -->
      </div>
    </div>
  </div>
</body>
</html>
'''

@app.route("/")
def index():
    app.logger.debug(f"index() - 傳給前端的 options 長度: {len(formatted_books)}")
    return render_template_string(template, options=formatted_books, update_date=UPDATE_DATE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
