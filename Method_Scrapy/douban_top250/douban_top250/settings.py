"""
settings.py - 全局配置（指南 5.7，代码 5-8）

表 5-3 的保守配置都在这里：robots、5 秒间隔、1 并发、重试、UA、导出。
原则是先"慢而稳"，确认能稳定抓到 250 条，再谈并发和速度。
"""

BOT_NAME = "douban_top250"

SPIDER_MODULES = ["douban_top250.spiders"]
NEWSPIDER_MODULE = "douban_top250.spiders"

# Scrapy 2.12+ 的插件入口（add-ons），没有就保持空字典
ADDONS = {}


# ------------------------- 合规与身份 -------------------------
# 遵守 robots.txt。豆瓣的 robots.txt 没有禁止 /top250，但 Crawl-delay: 5 被注释掉了；
# 本指南仍按 5 秒执行。不要为了速度把 ROBOTSTXT_OBEY 关掉。
ROBOTSTXT_OBEY = True

# 用普通浏览器 UA 让公开页面正常返回；不是伪装指纹，也不用来绕过登录/风控
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ------------------------- 限速（表 5-3） -------------------------
# 先串行：1 并发 + 5 秒间隔，250 条大约 50 秒
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 5

# AutoThrottle 会按响应延迟动态调整实际间隔：
# 下限是 max(DOWNLOAD_DELAY, AUTOTHROTTLE_START_DELAY)，不会低于 5 秒
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0


# ------------------------- 重试 -------------------------
# 只解决"临时性失败"（超时、5xx）。403/429 说明被限制，应该停下并降速，
# 而不是把重试次数调大、换代理硬撞。
RETRY_TIMES = 3


# ------------------------- 数据管道 -------------------------
# 数字小的先执行：先清洗（300），再校验（400）
ITEM_PIPELINES = {
    "douban_top250.pipelines.CleanTop250Pipeline": 300,
    "douban_top250.pipelines.ValidateTop250Pipeline": 400,
}


# ------------------------- 导出 -------------------------
# 每次 crawl 都会写下面两个文件；目录不存在时会自动创建。
# 想改导出路径/格式，也可以不用这里的配置，改用命令行 -O / -o（见 README）。
FEEDS = {
    "data/douban_top250.jsonl": {
        "format": "jsonl",
        "encoding": "utf8",
        "overwrite": True,
    },
    "data/douban_top250.csv": {
        "format": "csv",
        # utf-8-sig 带 BOM，Excel 双击打开中文不乱码
        "encoding": "utf-8-sig",
        # 固定列顺序，避免每次运行列顺序随字段出现顺序变化
        "fields": ["rank", "title", "rating", "quote", "url"],
        "overwrite": True,
    },
}

FEED_EXPORT_ENCODING = "utf-8"


# ------------------------- 日志 -------------------------
# 排错时用 DEBUG；日常用 INFO，重点看 item_scraped_count / response_received_count
LOG_LEVEL = "INFO"


# ------------------------- 断点续爬（5.9，代码 5-10） -------------------------
# JOBDIR 不用写在这里，命令行传即可（同一命令再执行一次就会从断点继续）：
#   scrapy crawl top250 -s JOBDIR=state/top250
# 它保存请求队列和去重指纹，适合"抓一半断了"。


# ------------------------- 可选：Scrapy + Playwright（5.11） -------------------------
# 豆瓣 Top250 是静态页面，用 HTTP 下载器就够了，**不要**默认打开下面这段。
# 只有遇到真正依赖 JavaScript 的页面时才启用（需要 pip install scrapy-playwright，
# 并 playwright install chromium）：
#
# DOWNLOAD_HANDLERS = {
#     "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
#     "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
# }
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
#
# 启用后只对需要的请求带 meta（代码 5-14，见 README 的附录）。
