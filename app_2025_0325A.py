from flask import Flask, render_template_string, Response, send_file
import json
import os
import logging
import csv
from io import StringIO
from openpyxl import Workbook
import tempfile

UPDATE_DATE = '2025/03/23'
MY_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_HTML_DIR = os.path.join(MY_SCRIPT_DIR, 'cache')
BOOKS_JSON_PATH = os.path.join(MY_SCRIPT_DIR, 'titles', 'titles.json')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

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

@app.route("/download_csv")
def download_csv():
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Code", "Title"])
    for code, title in sorted(book_list.items()):
        writer.writerow([code, title])
    output = si.getvalue()
    si.close()
    app.logger.info("下載 CSV 檔案")
    return Response(
        '\ufeff' + output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=books.csv"}
    )

@app.route("/download_xlsx")
def download_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.title = "經文名冊"
    ws.append(["Code", "Title"])
    for code, title in sorted(book_list.items()):
        ws.append([code, title])

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(tmp.name)
    tmp.seek(0)

    app.logger.info("下載 XLSX 檔案")
    return send_file(
        tmp.name,
        as_attachment=True,
        download_name="books.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/get_result/<code>")
def get_result(code):
    html_dir = CACHE_HTML_DIR
    target = code.lower() + ".html"
    for file in os.listdir(html_dir):
        if file.lower() == target:
            filename = os.path.join(html_dir, file)
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            app.logger.info(f"成功讀取 {filename}")
            return content
    app.logger.error(f"找不到檔案 {target}")
    return f"<p>找不到結果檔案: {target}</p>"


template = '''
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>經文名相查詢資料庫</title>
    <script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
    <style>
        h1 {
            font-size: 36px; font-size: calc(36px - 4pt);
            font-weight: bold;
            font-family: "黑體", sans-serif;
            color: black;
        }
        .input-group {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        .input-group label {
            font-size: 27px; font-size: calc(27px - 2pt);
            margin-right: 10px;
        }
        .dropdown-container {
            position: relative;
            flex: 1;
            display: flex;
            align-items: center;
        }
        #searchInput {
            width: 100%;
            font-size: 24px; font-size: calc(24px - 2pt);
            padding: 8px;
            box-sizing: border-box;
        }
        #toggleDropdown {
            cursor: pointer;
            font-size: 24px; font-size: calc(24px - 2pt);
            padding: 8px;
            user-select: none;
        }
        #dropdown {
            position: absolute;
            top: 110%;
            left: 0;
            right: 0;
            background-color: white;
            border: 1px solid #ccc;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        }
        #dropdown div {
            padding: 8px;
            cursor: pointer;
            font-size: 24px; font-size: calc(24px - 2pt);
        }
        #dropdown div:hover, #dropdown div.autocomplete-active {
            background-color: lightyellow;
        }
        .button-group {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        .button-group button {
            font-size: 24px; font-size: calc(24px - 2pt);
            padding: 8px 12px;
        }
        #resultContainer {
            margin-top: 20px;
        }
    </style>
    <script>
        var options = {{ options|tojson }};
        var currentFocus = -1;
        var prevInput = "";

        document.addEventListener("DOMContentLoaded", function() {
            var searchInput = document.getElementById("searchInput");
            searchInput.addEventListener("keydown", function(e) {
                var dropdown = document.getElementById("dropdown");
                var items = dropdown.getElementsByTagName("div");
                if (e.keyCode == 40) {
                    currentFocus++;
                    addActive(items);
                    e.preventDefault();
                } else if (e.keyCode == 38) {
                    currentFocus--;
                    addActive(items);
                    e.preventDefault();
                } else if (e.keyCode == 13) {
                    e.preventDefault();
                    if (currentFocus > -1 && items.length > 0) {
                        items[currentFocus].click();
                    }
                } else if (e.keyCode == 27) {
                    e.preventDefault();
                    clearInput();
                }
            });
            document.getElementById("toggleDropdown").addEventListener("click", function() {
                var dropdown = document.getElementById("dropdown");
                if (dropdown.style.display === "block") {
                    dropdown.style.display = "none";
                } else {
                    if (document.getElementById("searchInput").value.trim() === "") {
                        populateDropdown(options);
                    } else {
                        filterOptions();
                    }
                }
            });
        });

        function populateDropdown(optionList) {
            var dropdown = document.getElementById("dropdown");
            dropdown.innerHTML = "";
            var items = [];
            optionList.forEach(function(option) {
                var div = document.createElement("div");
                div.textContent = option;
                div.onclick = function() {
                    document.getElementById("searchInput").value = option;
                    dropdown.style.display = "none";
                    var codeMatch = option.match(/\((.*?)\)/);
                    if (codeMatch && codeMatch[1]) {
                        fetchResult(codeMatch[1]);
                    }
                };
                dropdown.appendChild(div);
                items.push(div);
            });
            dropdown.style.display = "block";
            if (items.length > 0) {
                currentFocus = 0;
                addActive(items, false);
            }
        }

        function filterOptions() {
            var input = document.getElementById("searchInput");
            var currentVal = input.value;
            var filter = currentVal.toLowerCase();
            var dropdown = document.getElementById("dropdown");
            if (currentVal !== prevInput) {
                currentFocus = -1;
                prevInput = currentVal;
            }
            dropdown.innerHTML = "";
            if (filter.trim() === "") {
                populateDropdown(options);
                return;
            }
            var matched = options.filter(function(option) {
                return option.toLowerCase().indexOf(filter) > -1;
            });
            if (matched.length > 0) {
                populateDropdown(matched);
            } else {
                dropdown.style.display = "none";
            }
        }

        function addActive(x, updateInput = true) {
            if (!x) return false;
            removeActive(x);
            if (currentFocus >= x.length) currentFocus = 0;
            if (currentFocus < 0) currentFocus = x.length - 1;
            x[currentFocus].classList.add("autocomplete-active");
            if (updateInput) {
                document.getElementById("searchInput").value = x[currentFocus].textContent;
            }
            x[currentFocus].scrollIntoView({ block: "nearest" });
        }

        function removeActive(x) {
            for (var i = 0; i < x.length; i++) {
                x[i].classList.remove("autocomplete-active");
            }
        }

        function fetchResult(code) {
            fetch("/get_result/" + code.toLowerCase())
            .then(function(response) { return response.text(); })
            .then(function(data) {
                document.getElementById("resultContainer").innerHTML = data;
            })
            .catch(function(error) {
                document.getElementById("resultContainer").innerHTML = "取得結果失敗: " + error;
            });
        }

        function clearInput() {
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

        document.addEventListener("click", function(e) {
            var dropdown = document.getElementById("dropdown");
            var container = document.getElementById("dropdownContainer");
            if (!container.contains(e.target)) {
                dropdown.style.display = "none";
            }
        });
    </script>
</head>
<body>
    <div style="font-size: smaller;"><h1>經文名相查詢 <span style="color: gray; font-size: 14px; font-size: calc(14px - 2pt);">(更新日期: {{ update_date }})</span></h1></div>
    <div class="input-group" id="dropdownContainer">
        <label for="searchInput">輸入經名</label>
        <div class="dropdown-container">
            <input type="text" id="searchInput" oninput="filterOptions()" placeholder="請輸入關鍵字...">
            <span id="toggleDropdown">&#9660;</span>
            <div id="dropdown"></div>
        </div>
    </div>
    <div class="button-group">
        <button id="clearButton" onclick="clearInput()">清除</button>
        <button id="downloadCSVButton" onclick="downloadCSV()">下載 CSV 檔</button>
        <button id="downloadXLSXButton" onclick="downloadXLSX()">下載 XLSX 檔案</button>
    </div>
    <hr>
    <div id="resultContainer"></div>
</body>
</html>
'''

@app.route("/")
def index():
    app.logger.info("進入首頁")
    return render_template_string(template, options=formatted_books, update_date=UPDATE_DATE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
