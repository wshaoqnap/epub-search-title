# 2025-0331_1030
# 新增 debug log: 1) 印出 formatted_books 觀察下拉式選單內容, 2) /get_result/<code> 內也加 debug log, 以排查未出現對應 html 的問題

import json
import os
import logging
from flask import Flask, render_template_string, Response, send_file
import csv
from io import StringIO
from openpyxl import Workbook
import tempfile

UPDATE_DATE = '2025/03/31'  # 更新日期

MY_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_HTML_DIR = os.path.join(MY_SCRIPT_DIR, 'cache')
BOOKS_JSON_PATH = os.path.join(MY_SCRIPT_DIR, 'titles', 'titles.json')

app = Flask(__name__)

# 設定為 DEBUG 等級，確保能看到 debug log
logging.basicConfig(level=logging.DEBUG)

# -------------------------------------------------------------
# 模擬讀取 JSON -> 組裝 formatted_books
# (實際可改成讀取 titles.json，或依原專案需求)
# -------------------------------------------------------------
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
        if isinstance(values, list) and len(values) >= 2:
            book_list[code] = values[1]

formatted_books = []
for code, title in sorted(book_list.items()):
    formatted_books.append(f"({code}) {title}")
app.logger.info(f"總共 {len(formatted_books)} 個選項")


# Flask routings 
@app.route("/get_result/<code>")
def get_result(code):
    """
    依照 code 到 cache 目錄抓取對應 .html
    """
    app.logger.debug(f"進入 get_result, code={code}")
    target = code.lower() + ".html"  # 檔名規定: 全小寫 + .html
    html_dir = CACHE_HTML_DIR

    # 檢查 cache 目錄是否存在
    if not os.path.isdir(html_dir):
        app.logger.debug(f"cache 目錄不存在: {html_dir}")
        return f"<p>找不到 cache 目錄: {html_dir}</p>"

    # 搜尋有無對應檔案
    found_file = None
    for file in os.listdir(html_dir):
        if file.lower() == target:
            found_file = file
            break

    if not found_file:
        app.logger.debug(f"找不到對應檔案: {target} (在 {html_dir} 內)")
        return f"<p>找不到結果檔案: {target}</p>"

    # 讀出檔案內容
    fullpath = os.path.join(html_dir, found_file)
    try:
        with open(fullpath, "r", encoding="utf-8") as f:
            content = f.read()
        app.logger.debug(f"成功讀取 {found_file}, 檔案大小 {len(content)} bytes")
        return content
    except Exception as e:
        app.logger.error(f"讀檔案失敗: {e}")
        return f"<p>讀檔案失敗: {e}</p>"


# 以下是簡易示範的下載 CSV 與 XLSX 路由，如不需可刪
@app.route("/download_csv")
def download_csv():
    app.logger.debug("download_csv() - 準備匯出 CSV")
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Code", "Title"])
    for entry in formatted_books:
        # 例如 entry="(T0001) 大般若經"
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

    # 假設把 formatted_books 寫進去
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



# -------------------------------------------------------------
# 首頁模板
# -------------------------------------------------------------
template = '''
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>經文名相查詢資料庫 - Debug Log示範</title>
    <script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
    <style>
      /* 簡化樣式，只展示核心部分 */
      h1 { font-size: 24px; font-weight: bold; }
      .update-date { color: gray; font-size: 14px; }
      .input-group { display: flex; margin-bottom: 1rem; }
      .dropdown-container { position: relative; flex: 1; }
      #searchInput { width: 70%; }
      #dropdown {
        position: absolute; top: 110%; left: 0; right: 0; width:100%;
        background-color: white; border:1px solid #ccc; max-height:150px;
        overflow-y:auto; display:none; z-index:999;
      }
      #dropdown div { padding: 4px; cursor:pointer; }
      #dropdown div:hover { background-color:lightyellow; }
      .button-group { margin-bottom: 1rem; }
      #resultContainer { margin-top: 1rem; }
    </style>
    <script>
      var options = {{ options|tojson }};

      var currentFocus = -1;
      var prevInput = "";

      document.addEventListener("DOMContentLoaded", function(){
        var searchInput = document.getElementById("searchInput");
        var dropdown = document.getElementById("dropdown");

        // 在 console 看看 options 內容是否跟後端預期相符
        console.log("Debug: options from server:", options);

        searchInput.addEventListener("keydown", function(e){
          var items = dropdown.getElementsByTagName("div");
          if(e.keyCode===40){ // down
            currentFocus++;
            addActive(items);
            e.preventDefault();
          } else if(e.keyCode===38){ // up
            currentFocus--;
            addActive(items);
            e.preventDefault();
          } else if(e.keyCode===13){ // enter
            e.preventDefault();
            if(currentFocus > -1 && items.length>0){
              console.log("Debug: You pressed Enter on item: ", items[currentFocus].textContent);
              items[currentFocus].click();
            }
          } else if(e.keyCode===27){ // esc
            e.preventDefault();
            clearInput();
          }
        });

        // 下拉按鈕
        document.getElementById("toggleDropdown").addEventListener("click", function(){
          if(dropdown.style.display==="block"){
            dropdown.style.display="none";
          }else{
            if(searchInput.value.trim()===""){
              populateDropdown(options);
            } else {
              filterOptions();
            }
          }
        });
      });

      function populateDropdown(optionList){
        var dropdown = document.getElementById("dropdown");
        dropdown.innerHTML="";
        var items=[];
        optionList.forEach(function(opt){
          var div = document.createElement("div");
          div.textContent = opt;
          div.onclick = function(){
            console.log("Debug: Clicked option text:", opt);
            document.getElementById("searchInput").value = opt;
            dropdown.style.display="none";
            // 解析 code
            var codeMatch = opt.match(/\\((.*?)\\)/);
            console.log("Debug: codeMatch result:", codeMatch);
            if(codeMatch && codeMatch[1]){
              fetchResult(codeMatch[1]);
            }
          };
          dropdown.appendChild(div);
          items.push(div);
        });
        dropdown.style.display="block";
        if(items.length>0){
          currentFocus=0;
          addActive(items,false);
        }
      }

      function filterOptions(){
        var input = document.getElementById("searchInput");
        var dropdown = document.getElementById("dropdown");
        var currentVal = input.value;
        if(currentVal!==prevInput){
          currentFocus=-1; 
          prevInput=currentVal;
        }
        dropdown.innerHTML="";

        if(currentVal.trim()===""){
          populateDropdown(options);
          return;
        }
        var matched = options.filter(function(opt){
          return opt.toLowerCase().indexOf(currentVal.toLowerCase())>-1;
        });
        if(matched.length>0){
          populateDropdown(matched);
        } else {
          dropdown.style.display="none";
        }
      }

      function addActive(x, updateInput=true){
        if(!x)return false;
        removeActive(x);
        if(currentFocus>=x.length) currentFocus=0;
        if(currentFocus<0) currentFocus=x.length-1;
        x[currentFocus].classList.add("autocomplete-active");
        if(updateInput){
          document.getElementById("searchInput").value = x[currentFocus].textContent;
        }
        x[currentFocus].scrollIntoView({block:"nearest"});
      }
      function removeActive(x){
        for(var i=0;i<x.length;i++){
          x[i].classList.remove("autocomplete-active");
        }
      }
      function clearInput(){
        document.getElementById("searchInput").value="";
        document.getElementById("dropdown").style.display="none";
        document.getElementById("resultContainer").innerHTML="";
      }

      // 呼叫後端 /get_result/<code> 取得對應 .html
      function fetchResult(code){
        console.log("Debug: fetchResult code=", code);
        fetch("/get_result/"+ code.toLowerCase())
          .then(function(resp){ return resp.text(); })
          .then(function(data){
            console.log("Debug: /get_result response data:", data);
            document.getElementById("resultContainer").innerHTML=data;
          })
          .catch(function(err){
            console.error("Debug: fetch error:",err);
            document.getElementById("resultContainer").innerHTML="取得結果失敗: "+ err;
          });
      }
    </script>
</head>
<body>
  <h1>經文名相查詢 <span class="update-date">(更新日期: {{ update_date }})</span></h1>
  <div class="input-group">
    <label>輸入經名</label>
    <div class="dropdown-container">
      <input type="text" id="searchInput" oninput="filterOptions()" placeholder="請輸入關鍵字...">
      <span id="toggleDropdown">&#9660;</span>
      <div id="dropdown"></div>
    </div>
  </div>
  <div class="button-group">
    <button onclick="clearInput()">清除</button>
    <button onclick="alert('下載 XLSX...')">下載 XLSX 檔案</button>
    <button style="display:none" onclick="alert('下載 CSV...')">下載 CSV 檔</button>
  </div>
  <hr>
  <div id="resultContainer"></div>
</body>
</html>
'''

@app.route("/")
def index():
    """
    首頁：將後端的 formatted_books 以 options 傳給前端，
    用來顯示下拉式選單。
    """
    # 在此也印出 debug log, 看 formatted_books 實際內容
    app.logger.debug(f"index() - 傳給前端的 options: {formatted_books}")
    return render_template_string(template, options=formatted_books, update_date=UPDATE_DATE)


if __name__ == "__main__":
    app.run(debug=True)
