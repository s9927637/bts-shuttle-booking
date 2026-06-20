"""
EventBuilder Service

Concert → EventPage 一鍵開團流程。
負責 slug 產生、重複偵測、欄位映射、Concert 狀態更新。
所有業務邏輯集中在此，Route 只負責呼叫。
"""
import re
from datetime import datetime

from app import db
from app.models.concert import Concert
from app.models.event_page import EventPage

# ── 城市 slug 對照表（與 event_page.py 共用同一份邏輯）───────────────────────
_CITY_SLUG = {
    "高雄": "kaohsiung", "台北": "taipei", "臺北": "taipei",
    "台中": "taichung", "臺中": "taichung",
    "台南": "tainan",   "臺南": "tainan",
    "新北": "new-taipei", "桃園": "taoyuan", "新竹": "hsinchu",
    "嘉義": "chiayi",   "屏東": "pingtung", "花蓮": "hualien",
    "宜蘭": "yilan",    "台東": "taitung",
}

# 部分藝名的英文 slug 對照（補充自動轉換效果不佳的日韓藝名）
_ARTIST_SLUG = {
    "藤井風":    "fujii-kaze",
    "BLACKPINK": "blackpink",
    "BTS":       "bts",
    "SEVENTEEN": "seventeen",
    "TWICE":     "twice",
    "aespa":     "aespa",
    "IVE":       "ive",
}


def _artist_to_slug(artist: str) -> str:
    slug = _ARTIST_SLUG.get(artist.strip())
    if slug:
        return slug
    return re.sub(r"[^a-z0-9]+", "-", artist.strip().lower()).strip("-")


def _city_to_slug(city: str) -> str:
    city = city.strip()
    return _CITY_SLUG.get(city) or re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")


def _make_slug(artist: str, city: str) -> str:
    """產生唯一 slug，重複時自動加數字尾碼。"""
    artist_part = _artist_to_slug(artist)
    city_part   = _city_to_slug(city) if city else ""
    base = f"{artist_part}-{city_part}" if city_part else artist_part
    base = re.sub(r"-{2,}", "-", base)

    slug, n = base, 2
    while EventPage.query.filter_by(slug=slug).filter(EventPage.deleted_at.is_(None)).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


# ── 公開 API ─────────────────────────────────────────────────────────────────

class EventAlreadyExists(Exception):
    """Concert 已有對應的 EventPage（未被軟刪除）。"""
    def __init__(self, event_page: EventPage):
        self.event_page = event_page
        super().__init__(f"EventPage 已存在：{event_page.slug}")


def build_event_from_concert(concert: Concert) -> EventPage:
    """
    從 Concert 建立對應的 EventPage。

    - 若該 Concert 已有未刪除的 EventPage，拋出 EventAlreadyExists。
    - 自動產生唯一 slug。
    - 將 Concert.status 更新為「確認開跑」。
    - 呼叫方負責 db.session.commit()。
    """
    # 檢查是否已存在
    existing = EventPage.query.filter_by(
        concert_id=concert.id
    ).filter(EventPage.deleted_at.is_(None)).first()
    if existing:
        raise EventAlreadyExists(existing)

    city = concert.city or ""
    slug = _make_slug(concert.artist, city)

    # 活動日期文字
    if concert.concert_date:
        event_date_str = concert.concert_date.strftime("%-m/%-d")
    else:
        event_date_str = None

    title = f"{concert.artist} {city}演唱會包車" if city else f"{concert.artist} 演唱會包車"

    ep = EventPage(
        title          = title,
        slug           = slug,
        artist_name    = concert.artist,
        event_name     = concert.name,
        event_date     = event_date_str,
        departure_city = city or None,
        price          = 2000,
        deposit        = 300,
        status         = "草稿",
        concert_id     = concert.id,
        created_at     = datetime.utcnow(),
        updated_at     = datetime.utcnow(),
    )
    db.session.add(ep)

    # 更新 Concert 狀態
    concert.status     = "確認開跑"
    concert.updated_at = datetime.utcnow()

    return ep
