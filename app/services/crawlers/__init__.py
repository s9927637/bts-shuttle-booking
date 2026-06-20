from app.services.crawlers.mock import MockCrawler
from app.services.crawlers.playwright_test import PlaywrightTestCrawler
from app.services.crawlers.kktix import KKTixCrawler
from app.services.crawlers.tixcraft import TixCraftCrawler

REGISTRY = {
    "mock":            MockCrawler,
    "playwright_test": PlaywrightTestCrawler,
    "kktix":           KKTixCrawler,
    "tixcraft":        TixCraftCrawler,
}
