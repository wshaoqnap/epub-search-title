# config.py
import os
from pathlib import Path

# 專案根目錄
BASE_DIR = Path(__file__).parent

# 更新日期
UPDATE_DATE = '2025/04/13'

# Cache HTML 目錄
CACHE_HTML_DIR = BASE_DIR / 'cache'

# 經文 JSON 路徑
BOOKS_JSON_PATH = BASE_DIR / 'titles' / 'titles.json'

# 預設備註檔目錄
DEFAULT_NOTES_DIR = BASE_DIR / 'default_notes'
