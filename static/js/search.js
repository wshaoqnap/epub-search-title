// search.js
import { fetchResult } from './utils.js';

let currentFocus = -1;
let prevInput = '';

/**
 * filterOptions: 根據輸入文字過濾下拉選單
 */
export function filterOptions(options) {
  const input = document.getElementById('searchInput');
  const dropdown = document.getElementById('dropdown');
  const value = input.value.trim().toLowerCase();

  // 輸入改變時重設 focus
  if (value !== prevInput) {
    currentFocus = -1;
    prevInput = value;
  }

  dropdown.innerHTML = '';
  if (!value) {
    // 輸入為空時顯示完整列表
    populateDropdown(options);
    return;
  }

  // 篩選匹配項
  const matched = options.filter(opt =>
    opt.toLowerCase().includes(value)
  );

  if (matched.length) {
    populateDropdown(matched);
  } else {
    dropdown.style.display = 'none';
  }
}

/**
 * populateDropdown: 建立下拉項目並綁定點擊
 */
export function populateDropdown(list) {
  const dropdown = document.getElementById('dropdown');
  dropdown.innerHTML = '';

  list.forEach(opt => {
    const div = document.createElement('div');
    div.textContent = opt;
    div.onclick = () => {
      const input = document.getElementById('searchInput');
      input.value = opt;
      dropdown.style.display = 'none';

      // 取出 code 並呼叫 fetchResult
      const match = opt.match(/\(([A-Za-z0-9_]+)\)/);
      if (match) fetchResult(match[1]);
    };
    dropdown.appendChild(div);
  });

  dropdown.style.display = list.length ? 'block' : 'none';
}
