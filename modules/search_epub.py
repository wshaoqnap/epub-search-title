import os
import json
import logging
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import pickle  # 新增：用於序列化快取結果


# 模組與專案目錄設定
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR)
# 磁碟層級快取解析後的 EPUB documents
CACHE_DIR = os.path.join(MODULE_DIR, ".cache_epub")
os.makedirs(CACHE_DIR, exist_ok=True)


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


def search_with_wildcard_in_documents(documents, keyword, logger=None):
    """
    在已解析的文檔中，以包含萬用字元 '*' 的關鍵字進行搜尋，並依指定邏輯生成非重疊、長度受控的 snippet。

    流程：
    1. 建立正則模式，'*' 代表一個中文字。
    2. 每頁：
       a. 清理文字。
       b. 找出所有 matches。
       c. Stage1 - 逐 match 產生初始 snippet：
          - snippet 長度為 default_len (30)
          - 如不含 keyword，延伸至 match.end()+default_len。
       d. Stage2 - 去重 (dedupe)，移除相同或被包含片段。
       e. Stage3 - 非重疊 (non-overlap) 保留順序，跳過前端重疊片段。
    3. 回傳總命中數、每頁命中數與最終 snippets。
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # 1. 編譯 regex pattern
    pattern_str = re.escape(keyword).replace(r'\*', r'[\u4e00-\u9fff]')
    pattern = re.compile(pattern_str)
    raw_keyword = keyword.replace('*', '')
    kw_len = len(raw_keyword)
    default_len = 30

    result = {"total": 0, "pages": {}, "sentences": {}}

    # 2. 逐頁處理
    for page, text in documents.items():
        # a. 清理文字
        clean_text = re.sub(r'[\n\t\r]', '', text)
        clean_text = re.sub(r'\s+', '', clean_text)
        text_len = len(clean_text)
        logger.info(f"Processing page {page}, text length {text_len}")

        # b. 找 matches
        matches = list(pattern.finditer(clean_text))
        match_count = len(matches)
        logger.info(f"Found {match_count} matches on page {page}")
        if match_count == 0:
            continue
        result["total"] += match_count
        result["pages"][page] = match_count

        # c. Stage1: 產生 all_snippets
        all_snippets = []
        for idx, m in enumerate(matches):
            m_start, m_end = m.start(), m.end()
            # 初始 snippet
            start = m_start
            end = min(start + default_len, text_len)
            snippet = clean_text[start:end]
            logger.debug(f"Match {idx}: initial snippet '{snippet}' (len={len(snippet)})")
            # 如 snippet 不含完整 keyword，再延伸
            if not pattern.search(snippet):
                ext_end = min(m_end + default_len, text_len)
                snippet = clean_text[start:ext_end]
                logger.debug(f"Match {idx}: extended snippet '{snippet}' (len={len(snippet)})")
            all_snippets.append((m_start, snippet))

        # d. Stage2: dedupe
        unique_snippets = []
        for start, sn in all_snippets:
            if not any(sn == ex or sn in ex or ex in sn for ex in unique_snippets):
                unique_snippets.append(sn)
            else:
                logger.debug(f"Dedup removing snippet: '{sn}'")

        # e. Stage3: non-overlap
        final_snippets = []
        last_end = 0
        for sn in unique_snippets:
            idx = clean_text.find(sn, last_end)
            if idx == -1:
                logger.warning(f"Snippet not found for non-overlap: '{sn}'")
                continue
            sn_end = idx + len(sn)
            if idx >= last_end:
                final_snippets.append(sn)
                logger.debug(f"Accepted snippet at {idx}-{sn_end}: '{sn}'")
                last_end = sn_end
            else:
                logger.debug(f"Skipped overlapping snippet at {idx}-{sn_end}: '{sn}'")

        result["sentences"][page] = final_snippets

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
    # return search_with_wildcard_in_documents(epub_path, documents, keyword, logger)
    return search_with_wildcard_in_documents(documents, keyword, logger)


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
        logger.debug(f"Searching keyword in '{epub_path}'")    
        ret = search_wildcard_one_epub(epub_path, keyword, logger)
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

