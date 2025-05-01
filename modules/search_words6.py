import os
import json
import logging
import re
from search_epub import search_one_epub


def search_words6_in_epub(words6_result, epub_path, logger=None, ignore_cache=False):
    """計算 words6_result 中的所有關鍵字, 在單一 epub 出現的總次數"""
    for main_key, main_val in words6_result.items():
        # main_val 是一個 dict: {
        #   "id": "...", 
        #   "異體字": [...], 
        #   "音譯詞": [...], 
        #   "同義詞/近義詞(意譯)": [...], 
        #   "複合詞": [...], 
        #   "相關詞": [...] }
        # 主 key 本身也需要 "found" 欄位來表示搜尋結果 (非id的字串統計結果)
        # 對 main_key 這個字串進行搜尋 
        # (若 main_key 本身並不是 words6_result 的 key-value 中要計算的字串可視情況而定，
        #  題目指示所有字串都要計算，包含主 key)
        # 先計算 main_key 自身的出現狀況
        if main_key != "id":  # "id" 不需計算
            found_result = search_one_epub(epub_path, main_key, logger=logger, ignore_cache=ignore_cache)
            # 新增 "found" 欄位於該主key的dict中
            main_val["found"] = found_result
        else:
            # 如果 main_key 剛好是 "id", 那表示是整個大 dict 的 key，
            # 按題目描述，"id"不算字串搜尋對象，在此為安全起見判斷一下，
            # 實務上 main_key 是 群首名相，不會是"id"。
            pass

        # 處理 "異體字", "音譯詞", "同義詞/近義詞(意譯)", "複合詞", "相關詞"
        for category_key in ["異體字", "音譯詞", "同義詞/近義詞(意譯)", "複合詞", "相關詞"]:
            # 這些欄位是 list
            if category_key in main_val:
                category_list = main_val[category_key]
                # 將原本的 list 轉成一個 dict，以字串為 key，搜尋結果為 value
                # 因為最後的結構中，需類似:
                # "異體字": [
                #   "毗那夜迦": { "total":..., "pages": {...} },
                #   ...
                # ]
                # 原本為 list, 轉回 dict 儲存不便, 題中範例並未特別要求保留為 list 或 dict, 但看範例像是:
                # "異體字": [
                #     "毗那夜迦": {...},
                #     "毘那耶迦": {...}
                # ]
                # 這不是標準的 list 格式，而是 list 裡放著 "字串": {...} 的形式，
                # 其實這在 JSON 中並非有效結構（JSON的array裡不能直接有key:value的命名欄位），
                # 題目範例中似乎是想表達一個 dictionary，但用 json 表示時行為像object，需要修改一下理解。

                # 題中範例結構實際上像這樣：
                # "異體字": {
                #     "毗那夜迦": {"total":..., "pages": {...}},
                #     "毘那耶迦": {"total":..., "pages": {...}}
                # }
                # 這才是有效的JSON結構。

                # 因此，我們應將原來的 list 改為 dict 來儲存結果。
                # 先建立一個新的 dict
                new_dict_for_category = {}
                for search_word in category_list:
                    # 對每個字串搜尋
                    found_result = search_one_epub(epub_path, search_word, logger=logger, ignore_cache=ignore_cache)
                    new_dict_for_category[search_word] = found_result
                # 將 category_key 的值替換為這個 dict
                main_val[category_key] = new_dict_for_category
    return words6_result

