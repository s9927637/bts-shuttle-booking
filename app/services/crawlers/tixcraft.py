"""
TixCraftCrawler — 使用 Playwright 抓取 TixCraft 演唱會活動。

目標頁面：
    https://tixcraft.com/activity/category/C  (演唱會分類)

DOM 結構（已驗證 2026-06）：
    .eventContainer
        a[href]                        ← 活動連結（/activity/detail/...）
        img[alt]                       ← 活動名稱（最可靠）
        inner_text line 1              ← 日期（2026/06/27 (Sat.)）
        inner_text line 2              ← 活動名稱（同 img.alt）
"""
from __future__ import annotations

import re

from app.services.crawlers.playwright_base import PlaywrightBaseCrawler
from app.services.concert_normalizer import parse_date, extract_city
from app.services.location_parser import parse_city
from app.services.artist_parser import parse_artist

_BASE_URL = "https://tixcraft.com"
_LIST_URL = "https://tixcraft.com/activity/category/C"


class TixCraftCrawler(PlaywrightBaseCrawler):

    source_name = "tixcraft"
    _target_url = _LIST_URL
    _timeout_ms = 30_000
    _wait_ms    = 10_000

    # ── fetch() — 覆寫：DOM 直接解析 ─────────────────────────────────────────

    def fetch(self) -> list[dict]:
        """
        導航至 TixCraft 演唱會分類頁，等待 .eventContainer 出現，
        直接從 DOM 取出活動資料。
        回傳格式：[{"title", "date_text", "source_url"}]
        """
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        raw_items: list[dict] = []

        with sync_playwright() as pw:
            browser, ctx = self._make_browser_context(pw)
            page = ctx.new_page()
            page.set_default_timeout(self._timeout_ms)

            self._log("INFO", f"[TixCraft] 前往：{_LIST_URL}")
            try:
                page.goto(_LIST_URL, wait_until="networkidle", timeout=self._timeout_ms)
            except PWTimeout:
                self._log("WARNING", "[TixCraft] networkidle 超時，繼續嘗試")
            except Exception as exc:
                self._log("ERROR", f"[TixCraft] 頁面載入失敗：{exc}")
                browser.close()
                return []

            # 等待活動卡片出現
            try:
                page.wait_for_selector(".eventContainer", timeout=self._wait_ms)
            except PWTimeout:
                self._log("WARNING", "[TixCraft] 等待 .eventContainer 超時，嘗試繼續解析")

            items = page.query_selector_all(".eventContainer")
            self._log("INFO", f"[TixCraft] 找到 {len(items)} 個 eventContainer")

            for el in items:
                try:
                    raw = self._extract_item(el)
                    if raw:
                        raw_items.append(raw)
                except Exception as exc:
                    self._log("WARNING", f"[TixCraft] 單筆解析失敗：{exc}")

            browser.close()

        self._log("INFO", f"[TixCraft] fetch 完成，共 {len(raw_items)} 筆原始資料")
        return raw_items

    def _extract_item(self, el) -> dict | None:
        """從單一 .eventContainer 提取活動資訊。"""
        # 連結
        link = el.query_selector("a")
        if not link:
            return None
        href = link.get_attribute("href") or ""
        if not href:
            return None
        if not href.startswith("http"):
            href = _BASE_URL + href

        # 標題：優先用 img.alt（最穩定）
        img   = el.query_selector("img")
        title = (img.get_attribute("alt") or "").strip() if img else ""

        # 日期：取 inner_text 第一行
        full_text = el.inner_text().strip()
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        date_text = ""
        if lines:
            first = lines[0]
            # 判斷是否為日期行（含 / 與 4 位年份）
            if re.search(r"20\d{2}/\d{1,2}/\d{1,2}", first):
                date_text = first
            # 若第一行是標題，嘗試第二行
            elif len(lines) > 1 and re.search(r"20\d{2}/\d{1,2}/\d{1,2}", lines[1]):
                date_text = lines[1]

        # 若 img.alt 為空，用文字最後一行作標題
        if not title and lines:
            title = lines[-1]

        if not title or len(title) < 2:
            return None

        # 過濾無效標題（優惠購票說明頁、身心障礙票頁等，標題以 [ 開頭）
        if title.startswith("["):
            return None

        return {
            "title":     title,
            "date_text": date_text,
            "venue":     "",
            "source_url": href,
        }

    # ── parse() — 標準化 ─────────────────────────────────────────────────────

    def parse(self, raw: list[dict]) -> list[dict]:
        """
        標準化 fetch() 回傳的原始資料。
        同時從標題中提取城市資訊（例如 "in TAIPEI"、"in KAOHSIUNG"）。
        """
        result: list[dict] = []
        seen:   set[str]   = set()

        for item in raw:
            try:
                title      = item.get("title", "")
                date_text  = item.get("date_text", "")
                source_url = item.get("source_url", "")

                artist       = parse_artist(title)
                concert_date = _parse_tixcraft_date(date_text)
                city         = _extract_city_from_title(title) or extract_city("")

                record = {
                    "artist":       artist,
                    "name":         title,
                    "concert_date": concert_date,
                    "city":         city or "待確認",
                    "venue":        "待確認",
                    "source_url":   source_url,
                    "source_type":  "TIXCRAFT",
                    "status":       "active",
                }

                key = f"{artist}|{concert_date}|{title}"
                if key in seen:
                    continue
                seen.add(key)

                result.append(record)

            except Exception as exc:
                self._log("WARNING", f"[TixCraft] parse 略過一筆：{exc}")

        self._log("INFO", f"[TixCraft] parse 完成，{len(result)} 筆有效資料")
        return result


# ── 輔助函式 ──────────────────────────────────────────────────────────────────

def _parse_tixcraft_date(text: str):
    """
    解析 TixCraft 日期格式。
    例：
        "2026/06/27 (Sat.)"           → date(2026, 6, 27)
        "2026/06/20 (Sat.) ~ 2026/06/21 (Sun.)" → date(2026, 6, 20)（取開始日）
    """
    if not text:
        return None
    match = re.search(r"(20\d{2})/(\d{1,2})/(\d{1,2})", text)
    if match:
        from datetime import date
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None


def _extract_city_from_title(title: str) -> str:
    """
    從標題提取城市資訊。
    例："ITZY 3RD WORLD TOUR in KAOHSIUNG" → "高雄"
    """
    # 先用 location_parser
    city = parse_city(title)
    if city:
        return city

    # 英文城市關鍵字（TixCraft 標題常用英文）
    _EN_CITY_MAP = {
        "taipei":    "台北",
        "tpe":       "台北",
        "kaohsiung": "高雄",
        "khs":       "高雄",
        "taichung":  "台中",
        "tainan":    "台南",
        "taoyuan":   "桃園",
        "osaka":     "大阪",
        "tokyo":     "東京",
        "seoul":     "首爾",
    }
    lower = title.lower()
    for kw, city_name in _EN_CITY_MAP.items():
        if kw in lower:
            return city_name

    return ""
