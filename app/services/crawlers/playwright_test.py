"""
PlaywrightTestCrawler

目的：驗證 Playwright → Crawler → Concert Import 整條 pipeline 可正常執行。

目標網址：https://example.com（IANA 官方測試頁，穩定不會消失）

此 crawler 不抓任何真實演唱會資料，而是：
1. 用 Playwright 取得 example.com HTML
2. 解析出頁面標題（"Example Domain"）
3. 轉為一筆假 Concert 資料，寫入 concerts 資料表
4. 以此驗證整條 pipeline（Playwright → parse → save → DB）正常運作

不是 production 爬蟲，不要用於正式演唱會資料匯入。
"""
from datetime import date

from app.services.crawlers.playwright_base import PlaywrightBaseCrawler


class PlaywrightTestCrawler(PlaywrightBaseCrawler):

    source_name  = "playwright_test"
    _target_url  = "https://example.com"

    # ── parse() ──────────────────────────────────────────────────────────────

    def parse(self, raw: list[dict]) -> list[dict]:
        """
        從 example.com HTML 解析出頁面標題，
        轉為一筆測試用 Concert 資料。
        """
        import re
        results: list[dict] = []

        for item in raw:
            html = item.get("html", "")
            url  = item.get("url", "")

            if not html:
                self._log("WARNING", "[TEST] 取得空 HTML，跳過")
                continue

            # 從 <title> 或 <h1> 取頁面標題
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            h1_match    = re.search(r"<h1[^>]*>([^<]+)</h1>",    html, re.IGNORECASE)

            page_title = (
                (title_match.group(1).strip() if title_match else None)
                or (h1_match.group(1).strip() if h1_match else None)
                or "Playwright Test Page"
            )

            # 取 HTML 大小作為驗證指標
            html_size = len(html)
            self._log("INFO", f"[TEST] 頁面標題：{page_title}，HTML 大小：{html_size} bytes")

            # 組成一筆測試用 Concert
            results.append({
                "artist":       "Playwright Test",
                "name":         f"[TEST] {page_title}",
                "concert_date": date(2099, 12, 31),   # 明顯的測試日期，不影響正式資料
                "city":         None,
                "venue":        "example.com",
                "source_url":   url,
                "status":       "評估中",
            })

        return results
