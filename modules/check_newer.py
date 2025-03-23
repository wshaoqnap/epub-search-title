import os
import json
import hashlib
import logging

def get_file_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def check_newer(target_path, last_check_file, logger=None):
    """
    檢查目標路徑中的檔案是否有更新。
    回傳一個包含已更新檔案的列表。
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.info(f"Checking the target_path = {target_path}")
    
    # 確認目標是檔案或目錄
    if os.path.isfile(target_path):
        files_to_check = [target_path]
    else:
        files_to_check = [os.path.join(root, file) for root, _, files in os.walk(target_path) for file in files]
    logger.info(f"Total files to check: {len(files_to_check)}")

    # 讀取上次檢查的結果
    if os.path.exists(last_check_file):
        with open(last_check_file, "r", encoding="utf-8") as f:
            last_check_dict = json.load(f)
    else:
        last_check_dict = {}

    # 檢查檔案是否有更新
    changed_files = []
    for file_path in files_to_check:
        logger.info(f"checking the file: {file_path}")
        file_stat = os.stat(file_path)
        file_md5 = get_file_md5(file_path)
        file_meta = {
            'mtime': file_stat.st_mtime,
            'md5': file_md5,
            'size': file_stat.st_size
        }
        if file_path in last_check_dict:
            if file_stat.st_mtime != last_check_dict[file_path]['mtime'] or \
                    file_md5 != last_check_dict[file_path]['md5']:
                changed_files.append(file_path)
                last_check_dict[file_path] = file_meta
                logger.info(f"File changed: {file_path}")
            else:
                logger.info(f"File not changed: {file_path}")
        else:
            changed_files.append(file_path)
            last_check_dict[file_path] = file_meta
            logger.info(f"New file detected: {file_path}")

    # 將最新的 metadata 寫入 last_check_file
    with open(last_check_file, "w", encoding="utf-8") as f:
        json.dump(last_check_dict, f, indent=4, ensure_ascii=False)
    return files_to_check, changed_files


