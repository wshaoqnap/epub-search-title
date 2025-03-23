import os
import json
import logging
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re


def sanitize_filename(keyword):
    return keyword.replace("*", "～")


def load_epub(epub_path, logger=None):
    """
    讀取並解析 EPUB 檔案。
    回傳一個包含所有文檔內容的字典。
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    if not os.path.exists(epub_path):
        logger.error(f"File not found: {epub_path}")
        return None  # 若檔案不存在，直接回傳 None

    # 读取 EPUB 文件
    book = epub.read_epub(epub_path)
    logger.debug(f"Reading EPUB file: {epub_path}")

    # 遍历书中的所有文档
    documents = {}
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # 使用 BeautifulSoup 解析文档内容
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            # 获取文档的页码（如果有）
            page_number = item.get_name()
            # 跳過 TOC 頁面 (目次)
            if page_number.lower() == "toc.xhtml":
                continue
            # 保存文档内容
            documents[page_number] = soup.get_text()
    return documents


def search_with_wildcard_in_documents(documents, keyword, logger=None):
    """
    keyword 中允許包含*符號, 一個*代表一個任意中文字, 兩個*代表任意兩個中文字, 
    例如: "金剛*經", 表示四個字, 前兩個字是"金剛", 第四個字是"經", 第三個字是任意中文字(不包括空格和標點符號),
    例如: "金剛**經", 表示五個字, 前兩個字是"金剛", 第五個字是"經", 第三和第四是任意中文字(不包括空格和標點符號),
    在已解析的文檔中搜尋關鍵字。回傳一個 dict，包含以下資訊：
    - total: 總共找到幾次   
    - pages: 包含每一頁找到幾次
    - sentences: 包含每一頁找到的句子
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # 將 keyword 中的 * 替換為正則表達式
    search_word = re.escape(keyword).replace(r'\*', r'[\u4e00-\u9fff]')
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
        matches = re.finditer(search_word, text)
        count = sum(1 for _ in matches)
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


def search_one_epub(epub_path, keyword, logger=None):
    """
    用關鍵字 keyword 去一個 epub 檔案 (epub_path) 中找尋包含此關鍵字的句子。
    回傳一個 dict，包含以下資訊：
    - total: 總共找到幾次   
    - pages: 包含每一頁找到幾次
    - sentences: 包含每一頁找到的句子
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    documents = load_epub(epub_path, logger)
    if documents is None:
        return {
            "total": 0,
            "pages": {},
            "sentences": {}
        }
    return search_in_documents(documents, keyword, logger)


def search_wildcard_one_epub(epub_path, keyword, logger=None):
    """
    用關鍵字 keyword 去一個 epub 檔案 (epub_path) 中找尋包含此關鍵字的句子。
    回傳一個 dict，包含以下資訊：
    - total: 總共找到幾次   
    - pages: 包含每一頁找到幾次
    - sentences: 包含每一頁找到的句子
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    documents = load_epub(epub_path, logger)
    if documents is None:
        return {
            "total": 0,
            "pages": {},
            "sentences": {}
        }
    return search_with_wildcard_in_documents(documents, keyword, logger)


def search_multiple_epubs(epub_paths, keyword, logger=None):
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
        results[base_name]  = search_one_epub(epub_path, keyword, logger)
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

