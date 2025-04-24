// utils.js
// 各種共用功能函式模組化匯出

/**
 * 向後端 /get_result 取得查詢結果，並更新畫面
 * @param {string} code 查詢代碼，如 "T0850"
 */
export function fetchResult(code) {
  fetch(`/get_result/${code.toLowerCase()}`)
    .then(resp => {
      if (!resp.ok) throw new Error(`HTTP error ${resp.status}`);
      return resp.text();
    })
    .then(html => {
      document.getElementById('resultContainer').innerHTML = html;
      adjustStickyHeaders();
    })
    .catch(err => {
      console.error('fetchResult error:', err);
      document.getElementById('resultContainer').textContent = '取得結果失敗';
    });
}

/**
 * 固定表頭：動態調整 thead th 的 top 屬性
 */
export function adjustStickyHeaders() {
  const leftPanel = document.getElementById('leftPanel');
  const rows = [
    leftPanel.querySelectorAll('table thead tr:nth-child(1) th'),
    leftPanel.querySelectorAll('table thead tr:nth-child(2) th'),
    leftPanel.querySelectorAll('table thead tr:nth-child(3) th'),
  ];
  let offset = 0;
  rows.forEach((ths, idx) => {
    if (ths.length) {
      const h = ths[0].getBoundingClientRect().height;
      ths.forEach(th => th.style.top = `${offset}px`);
      offset += h;
    }
  });
}

/**
 * 上半部文字放大／縮小
 * @param {number} factor 縮放倍率
 */
export function adjustFontSize(factor) {
  const uc = document.getElementById('upperContent');
  if (!uc) return;
  uc.querySelectorAll('*').forEach(el => {
    const size = parseFloat(getComputedStyle(el).fontSize);
    el.style.fontSize = `${size * factor}px`;
  });
}

/**
 * 顯示／隱藏側邊欄
 */
export function toggleRightPanel() {
  const right = document.getElementById('rightPanel');
  const divider = document.getElementById('divider');
  const left = document.getElementById('leftPanel');
  const btn = document.getElementById('toggleSidebarBtn');
  if (right.style.display === 'none' || !right.style.display) {
    right.style.display = 'flex';
    divider.style.display = 'block';
    left.style.width = `${100 - window.lastRightWidthPercent}%`;
    right.style.width = `${window.lastRightWidthPercent}%`;
    btn.textContent = '隱藏側邊欄';
  } else {
    divider.style.display = 'none';
    window.lastRightWidthPercent = parseFloat(right.style.width) || window.lastRightWidthPercent;
    right.style.display = 'none';
    left.style.width = '100%';
    btn.textContent = '顯示側邊欄';
  }
  adjustStickyHeaders();
}

/**
 * 初始化可拖曳分隔線（左右 & 上下）
 */
export function initResizableDividers() {
  const divider = document.getElementById('divider');
  const leftPanel = document.getElementById('leftPanel');
  const rightPanel = document.getElementById('rightPanel');
  const container = document.getElementById('mainContainer');

  // 左右分隔線
  let isResizing = false;
  divider.addEventListener('mousedown', e => { e.preventDefault(); isResizing = true; });
  document.addEventListener('mousemove', e => {
    if (!isResizing) return;
    const rect = container.getBoundingClientRect();
    let pct = (e.clientX - rect.left) / rect.width * 100;
    pct = Math.max(20, Math.min(100, pct));
    leftPanel.style.width = `${pct}%`;
    if (rightPanel.style.display !== 'none') {
      const rpct = 100 - pct;
      rightPanel.style.width = `${rpct}%`;
      window.lastRightWidthPercent = rpct;
    }
    adjustStickyHeaders();
  });
  document.addEventListener('mouseup', () => { isResizing = false; });

  // 上下分隔線
  const hDivider = document.getElementById('horizontalDivider');
  const upper = document.getElementById('upperRightPanel');
  const lower = document.getElementById('lowerRightPanel');
  let isResizingHoriz = false;
  hDivider.addEventListener('mousedown', () => { isResizingHoriz = true; });
  document.addEventListener('mousemove', e => {
    if (!isResizingHoriz) return;
    const rectR = rightPanel.getBoundingClientRect();
    let offsetY = e.clientY - rectR.top;
    const min = 30, max = rectR.height - min - hDivider.offsetHeight;
    offsetY = Math.max(min, Math.min(max, offsetY));
    upper.style.height = `${offsetY}px`;
    lower.style.height = `${rectR.height - offsetY - hDivider.offsetHeight}px`;
    adjustStickyHeaders();
  });
  document.addEventListener('mouseup', () => { isResizingHoriz = false; });
}

/**
 * 以 XLSX library 下載表格為檔案
 */
export function downloadXLSX() {
  const tbl = document.querySelector('#resultContainer table');
  if (!tbl) { alert('找不到搜尋結果表格！'); return; }
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.table_to_sheet(tbl);
  XLSX.utils.book_append_sheet(wb, ws, '查詢結果');
  XLSX.writeFile(wb, 'result.xlsx');
}

/**
 * 下載 CSV
 */
export function downloadCSV() {
  window.location.href = '/download_csv';
}
