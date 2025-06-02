import os
import json
import logging
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import pickle  # 新增：用於序列化快取結果
from typing import Dict, List, Any

# 嘗試匯入第三方 regex，失敗則 fallback to built-in re
try:
    import regex as re_mod
    HAS_REGEX = True
except ImportError:
    import re as re_mod
    HAS_REGEX = False


# 模組與專案目錄設定
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR)
# 磁碟層級快取解析後的 EPUB documents
CACHE_DIR = os.path.join(MODULE_DIR, ".cache_epub")
os.makedirs(CACHE_DIR, exist_ok=True)


# 建立 console logger
MY_SCRIPT_NAME = os.path.basename(__file__)
logger = logging.getLogger(MY_SCRIPT_NAME)
# logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.INFO)
logger.setLevel(logging.WARNING)
handler = logging.StreamHandler()
# 設定 Formatter：包含檔案名稱、行號、函式名稱，以及僅顯示 log level 首字母
formatter = logging.Formatter(
    '[%(asctime)s] <%(filename)s:%(lineno)d> (%(funcName)s) [%(levelname).1s] %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def sanitize_filename(keyword):
    return keyword.replace("*", "～")


def load_epub(epub_path, logger=None, ignore_cache=False):
    """
    讀取並解析 EPUB 檔案，並利用磁碟快取避免重複解析。
    回傳一個包含所有文檔內容的字典。
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    if not os.path.exists(epub_path):
        logger.error(f"File not found: {epub_path}")
        return None  # 若檔案不存在，直接回傳 None

    # 1. 計算快取檔路徑：使用 epub 檔名當作唯一 ID
    epub_id = os.path.splitext(os.path.basename(epub_path))[0]
    cache_path = os.path.join(CACHE_DIR, f"{epub_id}.pkl")
    # 2. 若快取存在且比原 epub 更新，就直接讀取快取 
    if ignore_cache == False and os.path.exists(cache_path):
        if os.path.exists(cache_path) and os.path.getmtime(cache_path) >= os.path.getmtime(epub_path):
            logger.debug(f"從快取載入 EPUB：{epub_path}")
            with open(cache_path, "rb") as cf:
                return pickle.load(cf)

    # 3. 快取不存在或已過期，重新解析 EPUB
    logger.debug(f"解析 EPUB 並更新快取：{epub_path}")
    book = epub.read_epub(epub_path)

    # 遍歷書中所有文件，抽出純文字
    documents = {}
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            page_number = item.get_name()
            if page_number.lower() == "toc.xhtml":
                continue
            # 去除 HTML 標籤後的純文字
            documents[page_number] = soup.get_text()

    # 4. 解析完成後，將結果寫入快取
    try:
        with open(cache_path, "wb") as cf:
            pickle.dump(documents, cf)
        logger.info(f"已更新快取檔：{cache_path}")
    except Exception as e:
        logger.error(f"快取寫入失敗：{e}")

    return documents


# 再次優化後的 search_with_wildcard_in_documents 函式
def search_with_wildcard_in_documents(
    documents: Dict[str, str], keyword: str, default_len: int = 60, logger=None
) -> Dict[str, any]:
    """
    支援萬用字元的全文搜尋，並依照 match 逐一擷取不重疊 snippet，
    確保每個 snippet 至少長度 default_len，完全包含關鍵字，
    並回傳包含 total, pages, sentences 的結果結構。
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # 編譯 pattern： '*' 萬用字元對應任一中文字
    # pattern = re.compile(re.escape(keyword).replace(r"\*", r"[一-鿿]"))
    escaped = re_mod.escape(keyword)
    if HAS_REGEX:
        # 用 \p{Han} 匹配所有漢字
        wildcard_pattern = escaped.replace(r"\*", r"\p{Han}")
        pattern = re_mod.compile(wildcard_pattern, flags=re_mod.UNICODE)
    else:
        # 內建 re 無法 \p{Han}，改為手動列出常用與擴充A~F範圍
        bracket = (
            r"[\u3400-\u4DBF\u4E00-\u9FFF"
            r"\U00020000-\U0002A6DF"
            r"\U0002A700-\U0002B73F"
            r"\U0002B740-\U0002B81F"
            r"\U0002B820-\U0002CEAF"
            r"\U0002CEB0-\U0002EBEF]"
        )
        wildcard_pattern = escaped.replace(r"\*", bracket)
        pattern = re_mod.compile(wildcard_pattern)

    raw_keyword = keyword.replace("*", "")
    kw_len = len(raw_keyword)
    result: Dict[str, Any] = {"total": 0, "pages": {}, "sentences": {}}

    for page, text in documents.items():
        # 清理
        clean_text = re_mod.sub(r"[\n\t\r]", "", text)
        clean_text = re_mod.sub(r"\s+", "", clean_text)
        text_len = len(clean_text)

        # 找到所有 match
        matches = list(pattern.finditer(clean_text))
        if not matches:
            continue

        # 統計次數
        match_count = len(matches)
        result["total"] += match_count
        result["pages"][page] = match_count

        # 不重疊 snippet 擷取
        snippets: List[str] = []
        next_search_pos = 0

        for m in matches:
            # 跳過已在先前 snippet 中的 match
            if m.start() < next_search_pos:
                continue

            # 詳細 log
            logger.debug(f"search_with_wildcard: page={page}, match_start={m.start()}")

            # 計算置中起點與結尾
            center = m.start() + kw_len // 2
            half_len = default_len // 2
            start = max(center - half_len, next_search_pos)
            end = start + default_len
            if end > text_len:
                end = text_len
                start = max(text_len - default_len, next_search_pos)

            # 偵測並補足被截斷的關鍵字尾部
            snippet = clean_text[start:end]
            for i in range(1, kw_len):
                if snippet.endswith(raw_keyword[:i]) and end + (kw_len - i) <= text_len:
                    end += (kw_len - i)
                    snippet = clean_text[start:end]
                    break

            # Log 片段資訊
            logger.debug(
                f"snippet range: start={start}, end={end}, preview={snippet[:30]}…"
            )

            snippets.append(snippet)
            next_search_pos = end

        result["sentences"][page] = snippets

    return result



def search_in_documents(documents, keyword, logger=None):
    """
    在已解析的文檔中搜尋關鍵字。回傳一個 dict，包含以下資訊：
    - total: 總共找到幾次   
    - pages: 包含每一頁找到幾次
    - sentences: 包含每一頁找到的句子
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    search_word = keyword.lower()
    logger.debug(f"Search keyword: {search_word}")
    result = {
        "total": 0,
        "pages": {},
        "sentences": {}
    }

    # 遍历所有文档内容
    for page_number, text in documents.items():
        # 先將 text 中的特殊字元 (ex: \n, \t) 去除, 並將所有空格替換為空字串
        text = re.sub(r'[\n\t\r]', '', text)
        text = re.sub(r'\s+', '', text).strip()
        # 统计关键字在当前文档中出现的次数
        count = text.count(search_word)
        if count > 0:
            # 更新结果字典
            result["total"] += count
            result["pages"][page_number] = count
            # 提取所有包含關鍵字的一段文字, 這段文字總長度是 60+關鍵字長度, 且關鍵字在中間, 兩邊各 30 個字元
            # 需注意的是, 這段文字可能會跨行, 也可能包含多個相同關鍵字, 但是都需要分別列出
            keyword_sentences = [] # 用來存放包含關鍵字的句子
            for match in re.finditer(search_word, text):
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                keyword_sentences.append(text[start:end])
            result["sentences"][page_number] = keyword_sentences
            logger.debug(f"Found {count} instances on page {page_number}")
    return result


def search_one_epub(epub_path, keyword, logger=None, ignore_cache=False):
    """
    用關鍵字 keyword 去一個 epub 檔案 (epub_path) 中找尋包含此關鍵字的句子。
    回傳一個 dict，包含以下資訊：
    - total: 總共找到幾次   
    - pages: 包含每一頁找到幾次
    - sentences: 包含每一頁找到的句子
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    documents = load_epub(epub_path, logger=logger, ignore_cache=ignore_cache)
    if documents is None:
        return {
            "total": 0,
            "pages": {},
            "sentences": {}
        }
    return search_in_documents(documents, keyword, logger)


def search_wildcard_one_epub(epub_path, keyword, logger=None, ignore_cache=False):
    """
    用關鍵字 keyword 去一個 epub 檔案 (epub_path) 中找尋包含此關鍵字的句子。
    回傳一個 dict，包含以下資訊：
    - total: 總共找到幾次   
    - pages: 包含每一頁找到幾次
    - sentences: 包含每一頁找到的句子
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    documents = load_epub(epub_path, logger=logger, ignore_cache=ignore_cache)
    if documents is None:
        return {
            "total": 0,
            "pages": {},
            "sentences": {}
        }
    # --> for debugging
    # logger.warning(f"Searching '{keyword}' in '{epub_path}'")
    # if 'T1251' in epub_path:
        # --> 將 documents 轉成 json 格式, 並寫入到 "D:\cbeta_v3\output\cache_by_words_test\T1251.json" 檔案中
        # with open("D:\\cbeta_v3\\output\\cache_by_words_test\\T1251.json", "w", encoding="utf-8") as f:
        #     json.dump(documents, f, ensure_ascii=False, indent=4)
        # logger.warning(f"wrote the document to 'D:\\cbeta_v3\\output\\cache_by_words_test\\T1251.json'")
    return search_with_wildcard_in_documents(documents, keyword, logger=logger)


def search_multiple_epubs(epub_paths, keyword, logger=None, ignore_cache=False):
    """
    用一個關鍵字去多個 epub 檔案 (epub_paths) 中找尋包含這些關鍵字的句子。
    回傳一個 dict，包含每個關鍵字在每個檔案代號中的搜尋結果, 例如:
    {
        "T0853": {
            "total": 1,
            "pages": {
                "juans/002.xhtml": 1
            },
            "sentences": {
                "juans/002.xhtml": [
                    "..."
                ]
            }
        },
        "T0866": {
            "total": 1,
            "pages": {
                "juans/001.xhtml": 1
            },
            "sentences": {
                "juans/001.xhtml": [
                    "..."
                ]
            }
        },

    """
    if logger is None:
        logger = logging.getLogger(__name__)

    results = {}
    for epub_path in epub_paths:
        # 提取檔名並去掉副檔名
        base_name = os.path.splitext(os.path.basename(epub_path))[0]
        logger.debug(f"Searching keyword in '{epub_path}'")        
        results[base_name]  = search_one_epub(epub_path, keyword, logger, ignore_cache)
    return results


def search_wildcard_multiple_epubs(epub_paths, keyword, logger=None):
    """
    用一個關鍵字去多個 epub 檔案 (epub_paths) 中找尋包含這些關鍵字的句子。
    回傳一個 dict，包含每個關鍵字在每個檔案代號中的搜尋結果, 例如:
    {
        "T0853": {
            "total": 1,
            "pages": {
                "juans/002.xhtml": 1
            },
            "sentences": {
                "juans/002.xhtml": [
                    "..."
                ]
            }
        },
        "T0866": {
            "total": 1,
            "pages": {
                "juans/001.xhtml": 1
            },
            "sentences": {
                "juans/001.xhtml": [
                    "..."
                ]
            }
        },

    """
    if logger is None:
        logger = logging.getLogger(__name__)

    results = {}
    for epub_path in epub_paths:
        # 提取檔名並去掉副檔名
        base_name = os.path.splitext(os.path.basename(epub_path))[0]
        # logger.warning(f"Searching '{keyword}' in '{epub_path}'")    
        ret = search_wildcard_one_epub(epub_path, keyword, logger=logger, ignore_cache=False)
        if ret["total"] > 0:
            results[base_name] = ret
    return results


def search_multiple_epubs_stat(epub_paths, keyword, logger=None):
    """
    呼叫 search_multiple_epubs(), 並將結果統計成一個 dict, 包含以下資訊:
    - found_epubs: 總共在幾個 epub 檔案中出現
    - found_juans: 總共在幾卷經文中出現
    - total: 總共出現幾次 (所有 epub 累計)
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    results = search_multiple_epubs(epub_paths, keyword, logger)

    # 統計結果
    results['_stat_'] = {
        "found_epubs": 0,
        "found_juans": 0,
        "total": 0
    }
    for epub_id in results:
        if epub_id == '_stat_':
            continue
        if results[epub_id]["total"] > 0:
            results['_stat_']["found_epubs"] += 1
            if results[epub_id].get("pages") and len(results[epub_id]["pages"]) > 0:
                results['_stat_']["found_juans"] += len(results[epub_id]["pages"])
            results['_stat_']["total"] += results[epub_id]["total"]
   
    return results


def search_wildcard_multiple_epubs_stat(epub_paths, keyword, logger=None):
    """
    呼叫 search_multiple_epubs(), 並將結果統計成一個 dict, 包含以下資訊:
    - found_epubs: 總共在幾個 epub 檔案中出現
    - found_juans: 總共在幾卷經文中出現
    - total: 總共出現幾次 (所有 epub 累計)
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    results = search_wildcard_multiple_epubs(epub_paths, keyword, logger)

    # 統計結果
    results['_stat_'] = {
        "found_epubs": 0,
        "found_juans": 0,
        "total": 0
    }
    for epub_id in results:
        if epub_id == '_stat_':
            continue
        if results[epub_id]["total"] > 0:
            results['_stat_']["found_epubs"] += 1
            if results[epub_id].get("pages") and len(results[epub_id]["pages"]) > 0:
                results['_stat_']["found_juans"] += len(results[epub_id]["pages"])
            results['_stat_']["total"] += results[epub_id]["total"]
   
    return results

