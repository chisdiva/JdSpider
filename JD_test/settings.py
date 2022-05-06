# Scrapy settings for JD_test project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'JD_test'

SPIDER_MODULES = ['JD_test.spiders']
NEWSPIDER_MODULE = 'JD_test.spiders'

# Enables scheduling storing requests queue in redis.
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
# SCHEDULER_PERSIST = True
# Ensure all spiders share same duplicates filter through redis.
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"

# Specify the host and port to use when connecting to Redis (optional).
REDIS_HOST = '1.14.150.188'
REDIS_PORT = 5546
MAX_IDLE_TIME_BEFORE_CLOSE = 90
# Custom redis client parameters (i.e.: socket timeout, etc.)
REDIS_PARAMS = {
    'password': ''
}

IMAGES_STORE = 's3://jdsp-image/productImage'
IMAGES_STORE_S3_ACL = 'public-read'
AWS_ENDPOINT_URL = 'http://s3-cn-south-1.qiniucs.com'
IMAGES_EXPIRES = 10
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
AWS_REGION_NAME = 'cn-south-1'
AWS_USE_SSL = False  # or True (None by default)
AWS_VERIFY = False  # or True (None by default)

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'JD_test (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

custom_settings = {
        "COOKIES_ENABLED": False,
}
# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
DOWNLOAD_DELAY = 1.5
DOWNLOAD_TIMEOUT = 10
# AUTOTHROTTLE_ENABLED = True
# AUTOTHROTTLE_START_DELAY = 4
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'JD_test.middlewares.JdTestSpiderMiddleware': 543,
#}
# SPIDER_MIDDLEWARES = {
#     'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
# }
# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'JD_test.middlewares.JSPageMiddleware': 1,
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'JD_test.middlewares.RandomUserAgentMiddleware': 543,
    'JD_test.middlewares.RandomProxyMiddleware': 722,
    'JD_test.middlewares.MyRetryMiddleware': 500,
}
RETRY_ENABLED = True
RETRY_HTTP_CODES = [302, 401, 403, 500, 502, 503, 504, 522, 524, 408, 429]

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'JD_test.pipelines.MongoPipeline': 300,
    # 'JD_test.pipelines.CategoryPipeline': 305,
    'JD_test.pipelines.CommentContentPipeline': 100,
    'scrapy.pipelines.images.ImagesPipeline': 1,
    'JD_test.pipelines.TimePipeline': 20,
}

#user_agent_list = []
# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'


MONGO_HOST = '1.14.150.188'
MONGO_PORT = 27017
MONGO_DBNAME = 'JD_test'
MONGO_USERNAME = ''
MONGO_PASSWORD = ''
MONGO_AUTHSOURCE=''
#MONGO_DOCNAME = 'Goods'


# LOG_FILE = "3and4.log"
# LOG_LEVEL = "INFO"
