"""
Concert Normalizer

將各爬蟲回傳的原始資料標準化為統一格式，再交給 BaseCrawler.save() 寫入 DB。

輸出標準 dict（每筆）：
  artist        : str        藝人名稱
  name          : str        演唱會全名
  concert_date  : date|None  演出日期
  venue         : str|None   場館名稱
  city          : str|None   城市
  source_url    : str|None   原始網址
  status        : str        預設 '評估中'
"""

import re
from datetime import date, datetime
from typing import Optional

# ── 城市關鍵字 → 標準城市名 ────────────────────────────────────────────────
_VENUE_CITY_MAP: list[tuple[str, str]] = [
    ("高雄",    "高雄"),
    ("台北",    "台北"), ("臺北",    "台北"),
    ("台中",    "台中"), ("臺中",    "台中"),
    ("台南",    "台南"), ("臺南",    "台南"),
    ("新北",    "新北"),
    ("桃園",    "桃園"),
    ("新竹",    "新竹"),
    ("嘉義",    "嘉義"),
    ("屏東",    "屏東"),
    ("花蓮",    "花蓮"),
    ("宜蘭",    "宜蘭"),
    ("台東",    "台東"),
    ("Kaohsiung",  "高雄"),
    ("Taipei",     "台北"),
    ("Taichung",   "台中"),
    ("Tainan",     "台南"),
]

# ── 知名藝人名稱模式（正規化前置辨識） ───────────────────────────────────────
_KNOWN_ARTISTS: list[str] = [
    "BLACKPINK", "BTS", "防彈少年團",
    "TWICE", "aespa", "IVE",
    "SEVENTEEN", "LE SSERAFIM", "NewJeans",
    "GOT7", "EXO", "SHINee", "NCT 127", "NCT",
    "STAYC", "stayc",
    "SuperM", "2PM",
    "藤井風", "Mr.Children", "RADWIMPS", "ONE OK ROCK",
    "五月天", "周杰倫", "Jay Chou", "林俊傑", "JJ Lin",
    "陳奕迅", "Eason Chan", "張惠妹", "A-mei", "MAMAMOO",
    "ENHYPEN", "TXT", "Tomorrow X Together",
    "Stray Kids", "ITZY", "NMIXX",
    "MONSTA X", "ASTRO", "VICTON",
]
# 依長度排序：優先匹配較長的藝人名稱（避免 NCT 先比對到 NCT 127）
_KNOWN_ARTISTS.sort(key=len, reverse=True)


# ── 日期格式解析 ─────────────────────────────────────────────────────────────

_DATE_PATTERNS: list[str] = [
    "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d",
    "%Y年%m月%d日",
    "%m/%d/%Y", "%d/%m/%Y",
]


def parse_date(text: str) -> Optional[date]:
    """嘗試多種格式解析日期字串，失敗回傳 None。"""
    if not text:
        return None
    text = text.strip()

    # 移除時間部分 "2025/11/15 19:30" → "2025/11/15"
    text = re.split(r"[\s（(]", text)[0]

    # 中文年月日
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # 嘗試標準格式
    for fmt in _DATE_PATTERNS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    # 只有 MM/DD（無年份）→ 假設今年或明年
    m = re.match(r"^(\d{1,2})/(\d{1,2})$", text)
    if m:
        mo, day = int(m.group(1)), int(m.group(2))
        today = date.today()
        try:
            d = date(today.year, mo, day)
            if d < today:
                d = date(today.year + 1, mo, day)
            return d
        except ValueError:
            pass

    return None


def extract_city(venue_text: str) -> Optional[str]:
    """從場館文字中提取城市名稱。"""
    if not venue_text:
        return None
    for keyword, city in _VENUE_CITY_MAP:
        if keyword.lower() in venue_text.lower():
            return city
    return None


def extract_artist(title: str) -> str:
    """
    從演唱會標題中嘗試提取藝人名稱。
    若無匹配，回傳標題前 20 字作為 fallback。
    """
    if not title:
        return "未知藝人"
    for artist in _KNOWN_ARTISTS:
        if artist.lower() in title.lower():
            return artist
    # Fallback：取標題中第一個大寫字母連續段 or 全部
    return title[:30].strip()


def normalize(raw: dict) -> Optional[dict]:
    """
    將原始爬蟲 dict 轉為標準 Concert dict。
    回傳 None 代表此筆資料無效（缺少必要欄位）。

    raw 可包含：
      title / name    演唱會標題（必要）
      artist          藝人名稱（可選；缺少時從 title 推斷）
      date_text       日期字串（可選）
      concert_date    date 物件（可選，優先）
      venue           場館（可選）
      city            城市（可選；缺少時從 venue 推斷）
      url / source_url 原始網址（可選）
    """
    title = (raw.get("title") or raw.get("name") or "").strip()
    if not title:
        return None

    # 藝人
    artist = (raw.get("artist") or "").strip() or extract_artist(title)

    # 日期
    concert_date = raw.get("concert_date")
    if not concert_date:
        concert_date = parse_date(raw.get("date_text") or raw.get("date") or "")

    # 場館
    venue = (raw.get("venue") or "").strip() or None

    # 城市（先直接取，再從 venue 推斷）
    city = (raw.get("city") or "").strip() or extract_city(venue or "") or None

    # 來源網址
    source_url = raw.get("source_url") or raw.get("url") or None

    return {
        "artist":       artist,
        "name":         title,
        "concert_date": concert_date,
        "venue":        venue,
        "city":         city,
        "source_url":   source_url,
        "status":       raw.get("status", "評估中"),
    }
