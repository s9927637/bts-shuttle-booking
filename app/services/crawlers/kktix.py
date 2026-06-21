"""
KKTixCrawler — 使用 Playwright 抓取 KKTIX 演唱會活動。

目標頁面：
    https://kktix.com/events?event_tag_ids_in=1  (演唱會 tag)

DOM 結構（已驗證 2026-06）：
    ul.events > li.type-view
        a.cover[href]                  ← 活動連結
            figure > figcaption
                .event-title h2        ← 活動名稱
                div.ft > span.date     ← 日期（2026/6/17(三)）
                div.ft > .category     ← 類型（演唱會、演出、其他…）
"""
from __future__ import annotations

from app.services.crawlers.playwright_base import PlaywrightBaseCrawler
from app.services.concert_normalizer import normalize, parse_date, extract_city
from app.services.location_parser import parse_city
from app.services.artist_parser import parse_artist

_KKTIX_URL = "https://kktix.com/events?event_tag_ids_in=1"
_BASE_URL   = "https://kktix.com"

# 接受的活動類型（過濾掉完全無關的）
_ALLOW_CATEGORIES = {"演唱會", "演出", "音樂"}


class KKTixCrawler(PlaywrightBaseCrawler):

    source_name  = "kktix"
    _target_url  = _KKTIX_URL
    _timeout_ms  = 30_000
    _wait_ms     = 10_000

    # ── fetch() — 覆寫：使用 DOM 選取器直接解析，無需回傳 HTML ──────────────

    def fetch(self) -> list[dict]:
        """
        導航至 KKTIX 演唱會篩選頁，等待 li.type-view 出現，
        直接從 DOM 取出活動資料，回傳原始 dict 列表。
        格式：[{"title", "date_text", "venue", "category", "source_url", "ticket_sale_date"}]
        """
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        raw_items: list[dict] = []

        with sync_playwright() as pw:
            browser, ctx = self._make_browser_context(pw)
            page = ctx.new_page()
            page.set_default_timeout(self._timeout_ms)

            self._log("INFO", f"[KKTIX] 前往：{_KKTIX_URL}")
            try:
                page.goto(_KKTIX_URL, wait_until="domcontentloaded", timeout=self._timeout_ms)
            except PWTimeout:
                self._log("ERROR", "[KKTIX] 頁面載入超時")
                browser.close()
                return []

            # 等待活動列表 JS 渲染完成
            try:
                page.wait_for_selector("ul.events li.type-view", timeout=self._wait_ms)
            except PWTimeout:
                self._log("WARNING", "[KKTIX] 等待 li.type-view 超時，嘗試繼續解析")

            # 從 DOM 直接取出所有活動
            items = page.query_selector_all("ul.events li.type-view")
            self._log("INFO", f"[KKTIX] 找到 {len(items)} 個活動項目")

            for li in items:
                try:
                    raw = self._extract_item(li)
                    if raw:
                        raw_items.append(raw)
                except Exception as exc:
                    self._log("WARNING", f"[KKTIX] 單筆解析失敗：{exc}")

            browser.close()

        self._log("INFO", f"[KKTIX] fetch 完成，共 {len(raw_items)} 筆原始資料")
        return raw_items

    def _extract_item(self, li) -> dict | None:
        """從單一 li.type-view 元素提取活動資訊。"""
        # 連結
        cover = li.query_selector("a.cover")
        if not cover:
            return None

        href = cover.get_attribute("href") or ""
        if not href:
            return None
        if not href.startswith("http"):
            href = _BASE_URL + href

        # 類型過濾
        cat_el   = li.query_selector(".category")
        category = cat_el.inner_text().strip() if cat_el else ""
        if category and not any(kw in category for kw in _ALLOW_CATEGORIES):
            return None

        # 標題
        title_el = li.query_selector(".event-title h2")
        title    = title_el.inner_text().strip() if title_el else ""
        if not title:
            title_el = li.query_selector(".event-title")
            title    = title_el.inner_text().strip() if title_el else ""
        if not title:
            return None

        # 日期文字（格式：2026/6/17(三)）
        date_el   = li.query_selector("span.date")
        date_text = date_el.inner_text().strip() if date_el else ""

        # 售票狀態（可能含售票時間）
        sale_el   = li.query_selector(".fake-btn, .sale-date, .ticket-status")
        sale_text = sale_el.inner_text().strip() if sale_el else ""

        return {
            "title":             title,
            "date_text":         date_text,
            "venue":             "",
            "category":          category,
            "source_url":        href,
            "ticket_sale_date":  sale_text,
        }

    # ── parse() — 標準化原始資料 ──────────────────────────────────────────────

    def parse(self, raw: list[dict]) -> list[dict]:
        """
        將 fetch() 回傳的原始 dict 標準化為 concert dict。

        fetch() 的格式（DOM 直接擷取）：
            {"title", "date_text", "venue", "category", "source_url", "ticket_sale_date"}

        標準化後格式：
            {"artist", "name", "concert_date", "city", "venue", "source_url", "status"}
        """
        result: list[dict] = []
        seen:   set[str]   = set()

        for item in raw:
            try:
                title      = item.get("title", "")
                date_text  = item.get("date_text", "")
                venue      = item.get("venue", "")
                source_url = item.get("source_url", "")

                artist        = parse_artist(title)
                concert_date  = parse_date(date_text)
                # 先從場館文字取城市，找不到時從標題中尋找
                city          = parse_city(venue) or extract_city(venue) or parse_city(title)

                record = {
                    "artist":       artist,
                    "name":         title,
                    "concert_date": concert_date,
                    "city":         city or "待確認",
                    "venue":        venue or "待確認",
                    "source_url":   source_url,
                    "source_type":  "KKTIX",
                    "status":       "active",
                }

                # 去重（藝人 + 日期 + 名稱）
                key = f"{artist}|{concert_date}|{title}"
                if key in seen:
                    continue
                seen.add(key)

                result.append(record)

            except Exception as exc:
                self._log("WARNING", f"[KKTIX] parse 略過一筆：{exc}")

        self._log("INFO", f"[KKTIX] parse 完成，{len(result)} 筆有效資料")
        return result
