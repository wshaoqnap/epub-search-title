import { filterOptions, populateDropdown } from './search.js';
import {
  fetchResult,
  adjustFontSize,
  toggleRightPanel,
  initResizableDividers,
  downloadXLSX
} from './utils.js';

// 取下拉選單資料
typeof window !== 'undefined' && (() => {
  const raw = document.getElementById('options-data').textContent.trim();
  const options = JSON.parse(raw || '[]');

  window.lastRightWidthPercent = 33.333;
  let hasClickedCell = false;
  let lastWordSelected = null;

  // 按鍵監聽：Esc 清除，Home/End 滾動
  window.addEventListener('keydown', e => {
    const left = document.getElementById('leftPanel');
    const tableExists = left && left.querySelector('table');
    if (e.key === 'Escape') {
      document.getElementById('searchInput').value = '';
      document.getElementById('dropdown').style.display = 'none';
      document.getElementById('resultContainer').innerHTML = '';
      removeFloatingButtons();
    } else if (e.key === 'Home' && tableExists) {
      left.scrollTop = 0;
      e.preventDefault();
    } else if (e.key === 'End' && tableExists) {
      left.scrollTop = left.scrollHeight;
      e.preventDefault();
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    // 移除舊有按鈕
    document.querySelectorAll('.scroll-btn').forEach(btn => btn.remove());
    document.querySelectorAll('.floating-btn').forEach(btn => btn.remove());

    const si = document.getElementById('searchInput');
    const dd = document.getElementById('dropdown');
    const clearBtn = document.getElementById('clearBtn');
    const left = document.getElementById('leftPanel');
    const right = document.getElementById('rightPanel');
    const divider = document.getElementById('divider');
    const upperContent = document.getElementById('upperContent');
    const container = document.getElementById('mainContainer');
    container.style.position = 'relative';

    // 初始隱藏側欄
    right.style.display = 'none';
    divider.style.display = 'none';
    left.style.width = '100%';

    // Autocomplete 鍵盤導航
    let currentFocus = -1;
    function addActive(items) {
      removeActive(items);
      if (currentFocus >= items.length) currentFocus = 0;
      if (currentFocus < 0) currentFocus = items.length - 1;
      items[currentFocus].classList.add('autocomplete-active');
      items[currentFocus].scrollIntoView({ block: 'nearest' });
    }
    function removeActive(items) {
      Array.from(items).forEach(item => item.classList.remove('autocomplete-active'));
    }
    si.addEventListener('keydown', e => {
      const items = dd.getElementsByTagName('div');
      if (!items.length) return;
      if (e.key === 'ArrowDown') { currentFocus++; addActive(items); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { currentFocus--; addActive(items); e.preventDefault(); }
      else if (e.key === 'Enter') { e.preventDefault(); if (currentFocus > -1) items[currentFocus].click(); }
    });

    // 搜尋輸入 & 切換下拉
    si.addEventListener('input', () => filterOptions(options));
    document.getElementById('toggleDropdown').addEventListener('click', () => {
      if (dd.style.display === 'block') dd.style.display = 'none';
      else {
        if (!si.value.trim()) populateDropdown(options);
        else filterOptions(options);
        si.focus();
      }
    });

    // 清除
    clearBtn.addEventListener('click', () => {
      si.value = '';
      dd.style.display = 'none';
      document.getElementById('resultContainer').innerHTML = '';
      removeFloatingButtons();
    });

    // 側欄按鈕
    document.getElementById('toggleSidebarBtn').addEventListener('click', () => {
      toggleRightPanel(); positionFloatingButtons();
    });
    document.getElementById('downloadXLSXButton').addEventListener('click', downloadXLSX);
    document.getElementById('increaseFontBtn').addEventListener('click', () => adjustFontSize(1.1));
    document.getElementById('decreaseFontBtn').addEventListener('click', () => adjustFontSize(0.9));
    document.getElementById('copyUpperBtn').addEventListener('click', () => navigator.clipboard.writeText(upperContent.innerText));

    // 可拖曳分隔線
    initResizableDividers();

    // 監聽結果區變動，自動加入浮動按鈕
    const resultContainer = document.getElementById('resultContainer');
    new MutationObserver(() => { removeFloatingButtons(); addFloatingButtons(); })
      .observe(resultContainer, { childList: true, subtree: true });

    function addFloatingButtons() {
      const table = left.querySelector('table');
      if (!table) return;
      const leftRect = left.getBoundingClientRect();
      const margin = 12;
      const btnSize = 32;
      const gap = 4; // 約 3pt
      const leftPos = leftRect.left + leftRect.width - btnSize - margin;

      // End 按鈕
      const down = createBtn('▼', '回到底部', () => { left.scrollTop = left.scrollHeight; });
      Object.assign(down.style, {
        position: 'fixed',
        top: `${leftRect.top + leftRect.height - btnSize - margin}px`,
        left: `${leftPos}px`
      });
      container.appendChild(down);

      // Home 按鈕（在 End 上方 3pt）
      const up = createBtn('▲', '回到頂部', () => { left.scrollTop = 0; });
      Object.assign(up.style, {
        position: 'fixed',
        top: `${leftRect.top + leftRect.height - btnSize - margin - btnSize - gap}px`,
        left: `${leftPos}px`
      });
      container.appendChild(up);
    }

    function createBtn(text, title, onClick) {
      const btn = document.createElement('div');
      btn.className = 'floating-btn';
      btn.innerText = text;
      btn.title = title;
      Object.assign(btn.style, {
        width: '32px', height: '32px',
        background: 'rgba(255,255,255,0.7)',
        border: '1px solid #ccc',
        borderRadius: '50%',
        cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
      });
      btn.addEventListener('click', onClick);
      return btn;
    }

    function removeFloatingButtons() {
      document.querySelectorAll('.floating-btn').forEach(b => b.remove());
    }
    function positionFloatingButtons() { removeFloatingButtons(); addFloatingButtons(); }

    // 表格點擊事件
    left.addEventListener('click', e => {
      const cell = e.target.closest('td');
      if (!cell || cell.closest('thead')) return;
      const word = cell.innerText.trim();
      if (!word || !isNaN(Number(word))) return;

      if (!hasClickedCell) {
        toggleRightPanel(); divider.style.display = 'block'; hasClickedCell = true; positionFloatingButtons();
      } else if (word === lastWordSelected) {
        toggleRightPanel(); divider.style.display = right.style.display === 'none' ? 'none' : 'block'; positionFloatingButtons();
      } else if (right.style.display === 'none') {
        toggleRightPanel(); divider.style.display = 'block'; positionFloatingButtons();
      }
      lastWordSelected = word;

      // 讀取 default_notes
      fetch(`/static/default_notes/${encodeURIComponent(word)}.txt`)
        .then(r => r.ok ? r.text() : Promise.reject())
        .then(text => {
          upperContent.innerHTML = `<div style="color:darkred;font-weight:bold;">${word}</div><div>${text}</div>`;
        })
        .catch(() => {
          upperContent.innerHTML = `<div style="color:darkred;font-weight:bold;">${word}</div>`;
        });

      // 若格式 (Txxxx)
      const match = word.match(/\((T\d+)\)/i);
      if (match) fetchResult(match[1]);
    });
  });
})();
