"""
PlaywrightBaseCrawler

繼承自 BaseCrawler，封裝 Playwright Browser 的啟動、頁面開啟、HTML 取得與關閉。
子類別只需實作 parse(raw) 與 _target_url，不需直接操作 Playwright API。

使用方式：
    class MyCrawler(PlaywrightBaseCrawler):
        source_name = "my_source"
        _target_url = "https://example.com"

        def parse(self, raw: list[dict]) -> list[dict]:
            ...

fetch() 預設行為：
    - 啟動 headless Chromium
    - 導航至 _target_url（可在子類別覆寫為多頁）
    - 等待 <body> 載入完成
    - 回傳 [{"url": url, "html": html_content}]
    子類別可覆寫 fetch() 實作多頁邏輯，或透過 _fetch_page() 取得單頁 HTML。
"""
from abc import abstractmethod
from typing import Optional

from app.services.crawlers.base import BaseCrawler

_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_DEFAULT_TIMEOUT_MS = 30_000
_DEFAULT_WAIT_MS    = 5_000


class PlaywrightBaseCrawler(BaseCrawler):
    """
    Playwright-backed 爬蟲基底類別。

    子類別必須實作：
      parse(raw) → list[dict]

    子類別可覆寫：
      _target_url   : str      — 預設抓取網址
      _page_limit   : int      — 最多翻頁數（預設 1）
      fetch()                  — 完全自訂抓取邏輯
    """

    _target_url:  str = "https://example.com"
    _page_limit:  int = 1
    _user_agent:  str = _DEFAULT_UA
    _timeout_ms:  int = _DEFAULT_TIMEOUT_MS
    _wait_ms:     int = _DEFAULT_WAIT_MS

    # ── Playwright 工具方法（供子類別或自訂 fetch 使用）────────────────────

    def _make_browser_context(self, playwright):
        """建立 Browser + BrowserContext，回傳 (browser, context)。"""
        browser = playwright.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=self._user_agent,
            locale="zh-TW",
            extra_http_headers={"Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"},
        )
        return browser, ctx

    def _fetch_page(self, page, url: str) -> Optional[str]:
        """
        導航至 url，等待 body 出現，回傳完整 HTML。
        失敗回傳 None。
        """
        from playwright.sync_api import TimeoutError as PWTimeout
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
            try:
                page.wait_for_selector("body", timeout=self._wait_ms)
            except PWTimeout:
                pass  # body 超時仍嘗試取 HTML
            return page.content()
        except PWTimeout:
            self._log("ERROR", f"[PW] 頁面載入超時：{url}")
            return None
        except Exception as exc:
            self._log("ERROR", f"[PW] 頁面載入失敗：{url} — {exc}")
            return None

    # ── 預設 fetch()（子類別可覆寫） ──────────────────────────────────────

    def fetch(self) -> list[dict]:
        """
        預設行為：抓取 _target_url 的 HTML。
        回傳 [{"url": url, "html": html}]。
        子類別可完全覆寫此方法實作多頁 / 動態翻頁邏輯。
        """
        from playwright.sync_api import sync_playwright

        results: list[dict] = []

        with sync_playwright() as pw:
            browser, ctx = self._make_browser_context(pw)
            page = ctx.new_page()
            page.set_default_timeout(self._timeout_ms)

            self._log("INFO", f"[PW] 啟動 Chromium，目標：{self._target_url}")
            html = self._fetch_page(page, self._target_url)

            if html:
                results.append({"url": self._target_url, "html": html})
                self._log("INFO", f"[PW] 取得 HTML {len(html)} bytes")
            else:
                self._log("WARNING", "[PW] 未取得任何 HTML")

            browser.close()

        return results

    # ── 子類別必須實作 ────────────────────────────────────────────────────

    @abstractmethod
    def parse(self, raw: list[dict]) -> list[dict]:
        """
        將 fetch() 回傳的 [{"url":..., "html":...}] 解析為標準 concert dict 列表。
        每筆必須包含：artist, name, concert_date(可 None), city, venue, source_url
        """
