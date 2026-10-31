# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 用 start_requests 生成固定 10 页请求                #
# ================================================================ #

"""
spiders/top250_pages.py - 用 start 参数生成 10 个起始请求（指南 5.6，代码 5-7）

和 top250.py 的差别只有"翻页方式"：
  - top250.py        跟着页面上的"后页"链接走：页数不确定、结构可能变化时更合适；
  - top250_pages.py  一次性排好 start=0,25,...,225：页数固定、想控制请求顺序时更合适。

parse 直接从 Top250Spider 继承，避免复制一份解析逻辑（改选择器只要改一处）。

运行（在 Method_Scrapy/douban_top250 目录下）：
    ..\\.venv\\Scripts\\scrapy.exe crawl top250_pages -L INFO
"""

import scrapy

from douban_top250.spiders.top250 import Top250Spider


class Top250PagesSpider(Top250Spider):
    # name 必须和父类的 "top250" 不同，否则 scrapy crawl 分不清用哪个
    name = "top250_pages"

    def start_requests(self):
        """替代父类的 start_urls + 默认 start_requests。"""
        for start in range(0, 250, 25):
            url = f"https://movie.douban.com/top250?start={start}&filter="
            # 10 个 URL 互不相同，dupefilter 不会误杀；
            # 如果是"同一 URL 隔周再抓"，需要 dont_filter=True 并自己判断内容是否变化。
            yield scrapy.Request(url, callback=self.parse)
