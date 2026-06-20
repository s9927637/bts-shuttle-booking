"""
KKTixCrawler — 使用 Playwright 抓取 KKTIX 演唱會活動。

目標頁面：
  https://kktix.com/events?category=concert

抓取欄位：
  活動名稱、活動日期、活動地點、活動網址、售票日期
"""
import re
from datetime import date

from app.services.crawlers.base import BaseCrawler
from app.services.concert_normalizer import normalize, parse_date, extract_city

_BASE_URL   = "https://kktix.com"
_LIST_URL   = "https://kktix.com/events?category=concert"
_PAGE_LIMIT = 3   # 最多抓前 N 頁


class KKTixCrawler(BaseCrawler):

    source_name = "kktix"

    # ── fetch() ──────────────────────────────────────────────────────────────

    def fetch(self) -> list[dict]:
        """用 Playwright 抓取 KKTIX 演唱會列表，回傳原始 dict 列表。"""
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
                url = f"{_LIST_URL}&page={page_no}"
                self._log("INFO", f"[KKTIX] 載入頁面 {page_no}：{url}")
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    # 等待活動卡片出現（KKTIX 用動態渲染）
                    try:
                        page.wait_for_selector(
                            "a[href*='/events/'], .events-list-item, .event-card, "
                            "[class*='event'][class*='card'], [class*='EventCard'], "
                            "article",
                            timeout=15_000,
                        )
                    except PWTimeout:
                        self._log("WARNING", f"[KKTIX] page {page_no} 等待超時，嘗試直接解析")

                    items = self._parse_page(page, url)
                    if not items:
                        self._log("INFO", f"[KKTIX] page {page_no} 無資料，停止翻頁")
                        break
                    raw_items.extend(items)
                    self._log("INFO", f"[KKTIX] page {page_no} 取得 {len(items)} 筆")

                except PWTimeout:
                    self._log("ERROR", f"[KKTIX] page {page_no} 頁面載入超時")
                    break
                except Exception as exc:
                    self._log("ERROR", f"[KKTIX] page {page_no} 錯誤：{exc}")
                    break

            browser.close()

        self._log("INFO", f"[KKTIX] fetch 完成，共 {len(raw_items)} 筆")
        return raw_items

    # ── _parse_page() ─────────────────────────────────────────────────────────

    def _parse_page(self, page, current_url: str) -> list[dict]:
        """從當前 Playwright page 物件解析所有活動卡片。"""
        items: list[dict] = []

        # 策略 1：嘗試結構化選取（KKTIX 多個版本使用不同 class）
        selectors = [
            "a.event-list-item",
            "a[class*='EventCard']",
            "li[class*='event'] a",
            "div[class*='event-card'] a",
            "article a[href*='/events/']",
            "a[href*='/events/'][href*='kktix']",
        ]

        links_found = []
        for sel in selectors:
            try:
                els = page.query_selector_all(sel)
                if els:
                    links_found = els
                    break
            except Exception:
                continue

        if links_found:
            for el in links_found[:30]:
                try:
                    item = self._extract_from_element(el)
                    if item:
                        items.append(item)
                except Exception:
                    continue
            return items

        # 策略 2：抓所有指向 /events/ 的 <a>，過濾演唱會
        try:
            all_links = page.query_selector_all("a[href*='/events/']")
            seen_hrefs: set[str] = set()
            for el in all_links[:60]:
                try:
                    href = el.get_attribute("href") or ""
                    if href in seen_hrefs:
                        continue
                    seen_hrefs.add(href)
                    item = self._extract_from_element(el)
                    if item and item.get("title"):
                        items.append(item)
                except Exception:
                    continue
        except Exception as exc:
            self._log("WARNING", f"[KKTIX] 策略 2 解析失敗：{exc}")

        return items

    def _extract_from_element(self, el) -> dict | None:
        """從單一 DOM 元素中提取活動資訊。"""
        try:
            href = el.get_attribute("href") or ""
            if not href:
                return None
            if not href.startswith("http"):
                href = _BASE_URL + href

            # 標題：嘗試多層提取
            title = ""
            for title_sel in [
                "h2", "h3", "h4",
                "[class*='title']", "[class*='name']",
                "strong", ".event-name", "span",
            ]:
                try:
                    t_el = el.query_selector(title_sel)
                    if t_el:
                        title = (t_el.inner_text() or "").strip()
                        if title:
                            break
                except Exception:
                    continue

            if not title:
                # 整個元素的文字，取第一行
                all_text = (el.inner_text() or "").strip()
                title = all_text.split("\n")[0].strip()

            if not title or len(title) < 3:
                return None

            # 日期 + 地點文字
            all_text = (el.inner_text() or "").strip()
            date_text, venue_text = self._extract_date_venue_from_text(all_text, title)

            return {
                "title":      title,
                "date_text":  date_text,
                "venue":      venue_text,
                "source_url": href,
            }
        except Exception:
            return None

    @staticmethod
    def _extract_date_venue_from_text(full_text: str, title: str) -> tuple[str, str]:
        """從整塊文字中提取日期與場館。"""
        lines = [l.strip() for l in full_text.splitlines() if l.strip() and l.strip() != title]

        # 找日期行（數字年月日模式）
        date_text = ""
        venue_text = ""
        for line in lines:
            if re.search(r"\d{4}[/\-年]", line) or re.search(r"\d{1,2}[/月]\d{1,2}", line):
                if not date_text:
                    date_text = line
            elif len(line) > 1 and not date_text.endswith(line):
                if not venue_text:
                    venue_text = line

        return date_text, venue_text

    # ── parse() ──────────────────────────────────────────────────────────────

    def parse(self, raw: list[dict]) -> list[dict]:
        """標準化爬回的原始資料，過濾無效項目。"""
        result = []
        seen: set[str] = set()
        for item in raw:
            try:
                normalized = normalize(item)
                if not normalized:
                    continue
                # 簡單去重（同標題同日期）
                key = f"{normalized['name']}|{normalized['concert_date']}"
                if key in seen:
                    continue
                seen.add(key)
                result.append(normalized)
            except Exception as exc:
                self._log("WARNING", f"[KKTIX] parse 略過一筆：{exc}")
        return result
