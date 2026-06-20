"""
TixCraftCrawler — 預留 TixCraft 爬蟲框架（尚未實作正式爬蟲邏輯）。
"""
from app.services.crawlers.base import BaseCrawler


class TixCraftCrawler(BaseCrawler):

    source_name = "tixcraft"

    def fetch(self) -> list[dict]:
        raise NotImplementedError("TixCraftCrawler 尚未實作，請使用 MockCrawler 測試流程")

    def parse(self, raw: list[dict]) -> list[dict]:
        raise NotImplementedError("TixCraftCrawler 尚未實作")
