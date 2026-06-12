# Scrapy settings for ufc_scraper project
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

ADDONS = {}

USER_AGENT = ""

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 2
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 403]
DOWNLOAD_DELAY = 2.0
COOKIES_ENABLED = True

ITEM_PIPELINES = {
    'ufc_scraper.pipelines.DatabasePipeline': 100,
}

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 30
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

FEED_EXPORT_ENCODING = "utf-8"

DOWNLOAD_HANDLERS = {
    "http": "scrapy_impersonate.ImpersonateDownloadHandler",
    "https": "scrapy_impersonate.ImpersonateDownloadHandler",
}

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy_impersonate.RandomBrowserMiddleware": 400,
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"