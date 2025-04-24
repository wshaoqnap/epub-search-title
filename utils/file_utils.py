import os
import re
import logging
from flask import Response
from io import StringIO
import csv
from openpyxl import Workbook
import tempfile
from config import CACHE_HTML_DIR, DEFAULT_NOTES_DIR

def error_html(msg: str, status: int = 500) -> Response:
    """
    統一錯誤回傳格式，回傳含錯誤訊息的 HTML
    """
    html = f'<div class="error">錯誤：{msg}</div>'
    return Response(html, status=status, mimetype='text/html')

def read_table_html(code: str) -> Response:
    """
    讀取 cache/<code>.html 中的 <table> 片段
    """
    target = code.lower() + '.html'
    html_dir = CACHE_HTML_DIR

    if not html_dir.is_dir():
        logging.warning(f"cache 目錄不存在：{html_dir}")
        return error_html("查無快取目錄，請稍後再試", status=404)

    found = next((f for f in os.listdir(html_dir) if f.lower() == target), None)
    if not found:
        logging.info(f"查無對應檔案：{target}")
        return error_html("查無結果檔案", status=404)

    path = html_dir / found
    try:
        content = path.read_text(encoding='utf-8')
        logging.debug(f"讀取 {found} 大小 {len(content)} bytes")
        m = re.search(r'(?is)<table.*?</table>', content)
        if m:
            return Response(m.group(0), mimetype='text/html')
        else:
            logging.error("HTML 缺少 <table> 片段")
            return error_html("結果格式異常", status=500)
    except Exception as e:
        logging.error(f"讀取 HTML 失敗：{e}")
        return error_html("伺服器異常，請稍後再試", status=500)

def read_default_note(word: str) -> str:
    """
    讀取預設備註 <word>.txt
    """
    path = DEFAULT_NOTES_DIR / f"{word}.txt"
    if not path.exists():
        logging.info(f"找不到預設備註：{path}")
        return ''
    try:
        content = path.read_text(encoding='utf-8')
        logging.debug(f"讀取預設備註檔：{path}")
        return content
    except Exception as e:
        logging.error(f"讀預設備註失敗：{e}")
        return ''

def make_csv_response(options: list) -> Response:
    """
    將 options list 轉成 CSV 回應
    """
    try:
        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(['選項'])
        for o in options:
            writer.writerow([o])
        data = si.getvalue()
        si.close()
        return Response(
            '\ufeff' + data,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment;filename=books.csv'}
        )
    except Exception as e:
        logging.error(f"CSV 產生失敗：{e}")
        return error_html("無法產生 CSV", status=500)

def make_xlsx_response(options: list) -> Response:
    """
    將 options list 轉成 XLSX 回應
    """
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = '清單'
        ws.append(['選項'])
        for o in options:
            ws.append([o])
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        wb.save(tmp.name)
        tmp.seek(0)
        data = tmp.read()
        return Response(
            data,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment;filename=books.xlsx'}
        )
    except Exception as e:
        logging.error(f"XLSX 產生失敗：{e}")
        return error_html("無法產生 XLSX", status=500)
