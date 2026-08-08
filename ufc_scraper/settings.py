# Scrapy settings for ufc_scraper project
import os
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "ufc_scraper"

SPIDER_MODULES = ["ufc_scraper.spiders"]
NEWSPIDER_MODULE = "ufc_scraper.spiders"

# Zyte API Add-on
ADDONS = {
    "scrapy_zyte_api.Addon": 500,
}

# Zyte API Settings
ZYTE_API_KEY = os.getenv("ZYTE_API_KEY")
ZYTE_API_TRANSPARENT_MODE = True

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 4
COOKIES_ENABLED = False
AUTOTHROTTLE_ENABLED = False

ITEM_PIPELINES = {
    'ufc_scraper.pipelines.DatabasePipeline': 100,
    #'ufc_scraper.ranking_json_pipeline.RankingJsonPipeline': 200,
}

FEED_EXPORT_ENCODING = "utf-8"

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"