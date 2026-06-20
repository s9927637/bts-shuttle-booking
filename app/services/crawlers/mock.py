"""
MockCrawler — 第一版使用 Mock Data 驗證整條 Crawler → Concerts → 待開團 流程。
不連接任何外部網站。
"""
from datetime import date

from app.services.crawlers.base import BaseCrawler


_MOCK_CONCERTS = [
    {
        "artist":       "藤井風",
        "name":         "藤井風 ASIA TOUR 2025",
        "concert_date": date(2025, 11, 15),
        "city":         "高雄",
        "venue":        "高雄巨蛋",
    },
    {
        "artist":       "BLACKPINK",
        "name":         "BLACKPINK WORLD TOUR [BORN PINK]",
        "concert_date": date(2025, 12, 6),
        "city":         "高雄",
        "venue":        "高雄世運主場館",
    },
    {
        "artist":       "SEVENTEEN",
        "name":         "SEVENTEEN TOUR 'FOLLOW' TO ASIA",
        "concert_date": date(2025, 12, 20),
        "city":         "高雄",
        "venue":        "高雄世運主場館",
    },
]


class MockCrawler(BaseCrawler):

    source_name = "mock"

    def fetch(self) -> list[dict]:
        self._log("INFO", "MockCrawler: 載入 Mock 測試資料（不連接外部網站）")
        return list(_MOCK_CONCERTS)

    def parse(self, raw: list[dict]) -> list[dict]:
        result = []
        for item in raw:
            result.append({
                "artist":       item["artist"],
                "name":         item["name"],
                "concert_date": item.get("concert_date"),
                "city":         item.get("city"),
                "venue":        item.get("venue"),
                "status":       "評估中",
            })
        return result
