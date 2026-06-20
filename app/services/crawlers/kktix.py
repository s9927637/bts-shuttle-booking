"""
KKTixCrawler — 預留 KKTix 爬蟲框架（尚未實作正式爬蟲邏輯）。
"""
from app.services.crawlers.base import BaseCrawler


class KKTixCrawler(BaseCrawler):

    source_name = "kktix"

    def fetch(self) -> list[dict]:
        raise NotImplementedError("KKTixCrawler 尚未實作，請使用 MockCrawler 測試流程")

    def parse(self, raw: list[dict]) -> list[dict]:
        raise NotImplementedError("KKTixCrawler 尚未實作")
