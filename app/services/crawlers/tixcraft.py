"""
TixCraftCrawler — 使用 Playwright 抓取 TixCraft 演唱會活動。

目標頁面：
  https://tixcraft.com/activity/category/C   (演唱會分類)

抓取欄位：
  活動名稱、活動日期、活動地點、活動網址
"""
import re

from app.services.crawlers.base import BaseCrawler
from app.services.concert_normalizer import normalize

_BASE_URL   = "https://tixcraft.com"
_LIST_URL   = "https://tixcraft.com/activity/category/C"
_PAGE_LIMIT = 3


class TixCraftCrawler(BaseCrawler):

    source_name = "tixcraft"

    # ── fetch() ──────────────────────────────────────────────────────────────

    def fetch(self) -> list[dict]:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        raw_items: list[dict] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="zh-TW",
            )
            page = ctx.new_page()
            page.set_default_timeout(30_000)

            for page_no in range(1, _PAGE_LIMIT + 1):
                # TixCraft 分頁：page_no=1 → 不加 param，page_no>1 → ?p=N
                url = _LIST_URL if page_no == 1 else f"{_LIST_URL}?p={page_no}"
                self._log("INFO", f"[TixCraft] 載入頁面 {page_no}：{url}")

                try:
                    page.goto(url, wait_until="domcontentloaded")
                    try:
                        page.wait_for_selector(
                            "a[href*='/activity/detail/'], table tbody tr, "
                            ".card, [class*='activity'], ul.list-item li",
                            timeout=15_000,
                        )
                    except PWTimeout:
                        self._log("WARNING", f"[TixCraft] page {page_no} 等待超時，嘗試直接解析")

                    items = self._parse_page(page)
                    if not items:
                        self._log("INFO", f"[TixCraft] page {page_no} 無資料，停止翻頁")
                        break
                    raw_items.extend(items)
                    self._log("INFO", f"[TixCraft] page {page_no} 取得 {len(items)} 筆")

                except PWTimeout:
                    self._log("ERROR", f"[TixCraft] page {page_no} 頁面載入超時")
                    break
                except Exception as exc:
                    self._log("ERROR", f"[TixCraft] page {page_no} 錯誤：{exc}")
                    break

            browser.close()

        self._log("INFO", f"[TixCraft] fetch 完成，共 {len(raw_items)} 筆")
        return raw_items

    # ── _parse_page() ─────────────────────────────────────────────────────────

    def _parse_page(self, page) -> list[dict]:
        items: list[dict] = []

        # 策略 1：TixCraft 使用 table 列表
        try:
            rows = page.query_selector_all("table tbody tr")
            if rows:
                for row in rows:
                    item = self._extract_from_table_row(row)
                    if item:
                        items.append(item)
                if items:
                    return items
        except Exception:
            pass

        # 策略 2：卡片式列表
        card_selectors = [
            "a[href*='/activity/detail/']",
            ".col-activity a",
            "[class*='activity-item'] a",
            "ul.list-unstyled li a",
        ]
        for sel in card_selectors:
            try:
                els = page.query_selector_all(sel)
                if els:
                    seen: set[str] = set()
                    for el in els[:40]:
                        try:
                            href = el.get_attribute("href") or ""
                            if href in seen:
                                continue
                            seen.add(href)
                            item = self._extract_from_card(el)
                            if item:
                                items.append(item)
                        except Exception:
                            continue
                    if items:
                        return items
            except Exception:
                continue

        # 策略 3：抓所有 activity/detail 連結
        try:
            all_links = page.query_selector_all("a[href*='activity']")
            seen_hrefs: set[str] = set()
            for el in all_links[:60]:
                try:
                    href = el.get_attribute("href") or ""
                    if "detail" not in href:
                        continue
                    if href in seen_hrefs:
                        continue
                    seen_hrefs.add(href)
                    item = self._extract_from_card(el)
                    if item and item.get("title"):
                        items.append(item)
                except Exception:
                    continue
        except Exception:
            pass

        return items

    def _extract_from_table_row(self, row) -> dict | None:
        try:
            cells = row.query_selector_all("td")
            if len(cells) < 2:
                return None
            # TixCraft table 欄位：活動名稱, 日期, 場地
            link_el = cells[0].query_selector("a")
            title = (cells[0].inner_text() or "").strip()
            href  = ""
            if link_el:
                href  = link_el.get_attribute("href") or ""
                title = (link_el.inner_text() or title).strip()
            if not href.startswith("http"):
                href = _BASE_URL + href

            date_text  = (cells[1].inner_text() or "").strip() if len(cells) > 1 else ""
            venue_text = (cells[2].inner_text() or "").strip() if len(cells) > 2 else ""

            if not title or len(title) < 2:
                return None

            return {
                "title":      title,
                "date_text":  date_text,
                "venue":      venue_text,
                "source_url": href,
            }
        except Exception:
            return None

    def _extract_from_card(self, el) -> dict | None:
        try:
            href = el.get_attribute("href") or ""
            if not href.startswith("http"):
                href = _BASE_URL + href

            all_text = (el.inner_text() or "").strip()
            lines = [l.strip() for l in all_text.splitlines() if l.strip()]
            if not lines:
                return None

            title = lines[0]
            date_text  = ""
            venue_text = ""
            for line in lines[1:]:
                if re.search(r"\d{4}[/\-年]|\d{1,2}[/月]\d{1,2}", line):
                    if not date_text:
                        date_text = line
                elif not venue_text:
                    venue_text = line

            if not title or len(title) < 2:
                return None

            return {
                "title":      title,
                "date_text":  date_text,
                "venue":      venue_text,
                "source_url": href,
            }
        except Exception:
            return None

    # ── parse() ──────────────────────────────────────────────────────────────

    def parse(self, raw: list[dict]) -> list[dict]:
        result = []
        seen: set[str] = set()
        for item in raw:
            try:
                normalized = normalize(item)
                if not normalized:
                    continue
                key = f"{normalized['name']}|{normalized['concert_date']}"
                if key in seen:
                    continue
                seen.add(key)
                result.append(normalized)
            except Exception as exc:
                self._log("WARNING", f"[TixCraft] parse 略過一筆：{exc}")
        return result
