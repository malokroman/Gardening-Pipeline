from dagster import Config, asset
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scrapers.spiders.rhs import RHSSpider


class PlantSearchConfig(Config):
    plants: list[str]


@asset(deps=["plant_search_query"])
def rhs_plants_info(config: PlantSearchConfig) -> None:
    settings = get_project_settings()
    process = CrawlerProcess(
        {
            **settings,
            "LOG_LEVEL": "INFO",
            "FEEDS": {
                "data/rhs_plants.jsonl": {
                    "format": "jsonlines",
                },
            },
        }
    )
    process.crawl(RHSSpider, plants=config.plants)
    process.start()
