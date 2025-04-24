import json
import logging
from config import BOOKS_JSON_PATH


def load_books_data():
    """
    讀取 titles.json，回傳扁平化後的 code->title dict
    """
    try:
        with open(BOOKS_JSON_PATH, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        logging.debug(f"成功讀取 {BOOKS_JSON_PATH}")
    except Exception as e:
        logging.error(f"讀取 titles.json 失敗: {e}")
        return {}

    book_list = {}
    for docx, items in raw.items():
        for code, values in items.items():
            if isinstance(values, list):
                if len(values) >= 2:
                    book_list[code] = values[1]
                elif len(values) == 1:
                    book_list[code] = values[0]
                else:
                    book_list[code] = '(無標題)'
            else:
                book_list[code] = str(values)
    logging.info(f"載入 {len(book_list)} 本經文選項")
    return book_list


def format_options(book_list: dict) -> list:
    """
    將 code->title dict 轉為 (code) title list
    """
    formatted = [f"({c}) {t}" for c, t in sorted(book_list.items())]
    return formatted
