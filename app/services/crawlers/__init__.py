from app.services.crawlers.mock import MockCrawler
from app.services.crawlers.kktix import KKTixCrawler
from app.services.crawlers.tixcraft import TixCraftCrawler

REGISTRY = {
    "mock":     MockCrawler,
    "kktix":    KKTixCrawler,
    "tixcraft": TixCraftCrawler,
}
