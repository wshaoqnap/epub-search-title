from flask import Blueprint, render_template, current_app
# from config import UPDATE_DATE
from utils.data_utils import load_books_data, format_options
from utils.file_utils import (
    read_table_html,
    read_default_note,
    make_csv_response,
    make_xlsx_response,
    error_html
)

bp = Blueprint('main', __name__)

# 載入並格式化選項
books = load_books_data()
options = format_options(books)

@bp.route('/')
def index():
    current_app.logger.info(f"載入首頁，選項數量：{len(options)}")
    if not options:
        return error_html("目前沒有可查詢項目", status=200)
    # 改用 render_template 讀取 templates/index.html
    return render_template('base.html', options=options, update_date="")

@bp.route('/get_result/<code>')
def get_result(code):
    current_app.logger.info(f"查詢 code：{code}")
    return read_table_html(code)

@bp.route('/download_csv')
def download_csv():
    current_app.logger.info("開始 CSV 下載")
    return make_csv_response(options)

@bp.route('/download_xlsx')
def download_xlsx():
    current_app.logger.info("開始 XLSX 下載")
    return make_xlsx_response(options)

@bp.route('/get_default_note/<word>')
def get_note(word):
    current_app.logger.info(f"讀取預設筆記：{word}")
    try:
        return read_default_note(word)
    except Exception as e:
        current_app.logger.error(f"讀筆記失敗：{e}")
        return error_html("無法讀取筆記", status=500)
