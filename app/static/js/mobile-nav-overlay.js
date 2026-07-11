/* Mobile Navigation V3（Premium Edition）— Full Screen Overlay Navigation
   共用控制邏輯：開/關動畫、ESC 關閉、點背景關閉、Body 禁止 Scroll、Focus Trap。 */
(function () {
  function init() {
    var toggle   = document.querySelector('.mnav-toggle');
    var overlay  = document.querySelector('.mnav-overlay');
    var closeBtn = document.querySelector('.mnav-close');
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
    if (closeBtn) closeBtn.addEventListener('click', close);

    // 點背景關閉：overlay 本身、或 Header／Menu 的空白容器區域（非連結/按鈕本身）
    overlay.addEventListener('click', function (e) {
      if (e.target.closest('a, button')) return;
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
