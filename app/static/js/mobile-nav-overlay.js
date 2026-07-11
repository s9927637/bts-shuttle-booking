/* Floating Glass Navigation — 共用控制邏輯：開/關動畫、ESC 關閉、點背景（卡片外）關閉、
   Body 禁止 Scroll、Focus Trap。取代先前的 Full Screen Overlay。 */
(function () {
  function init() {
    var toggle = document.querySelector('.mnav-toggle');
    var overlay = document.querySelector('.mnav-overlay');
    var card = document.querySelector('.mnav-glass-card');
    if (!toggle || !overlay) return;

    var lastFocused = null;

    function focusableEls() {
      return Array.prototype.slice.call(
        overlay.querySelectorAll('a[href], button:not([disabled])')
      );
    }

    function onKeydown(e) {
      if (e.key === 'Escape') {
        close();
        return;
      }
      if (e.key === 'Tab') {
        var els = focusableEls();
        if (!els.length) return;
        var first = els[0];
        var last  = els[els.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    function open() {
      lastFocused = document.activeElement;
      overlay.classList.add('is-open');
      overlay.setAttribute('aria-hidden', 'false');
      toggle.setAttribute('aria-expanded', 'true');
      document.body.classList.add('mnav-lock');
      var els = focusableEls();
      if (els.length) els[0].focus();
      document.addEventListener('keydown', onKeydown);
    }

    function close() {
      overlay.classList.remove('is-open');
      overlay.setAttribute('aria-hidden', 'true');
      toggle.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('mnav-lock');
      document.removeEventListener('keydown', onKeydown);
      if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus();
    }

    toggle.addEventListener('click', function () {
      if (overlay.classList.contains('is-open')) close();
      else open();
    });

    // 點卡片外（Hero／空白處）關閉；點卡片內（含空白區域）不關閉，連結照常導頁
    overlay.addEventListener('click', function (e) {
      if (card && card.contains(e.target)) return;
      close();
    });

    window.__mnavClose = close;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
