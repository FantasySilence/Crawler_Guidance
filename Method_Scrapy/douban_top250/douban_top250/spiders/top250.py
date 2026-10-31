"""
spiders/top250.py - 豆瓣 Top250 主 Spider（指南 5.3，代码 5-3）

Spider 只做两件事：
  1. 在列表页把字段取出来，yield 成 Item；
  2. 找到"后页"，yield 一个新的 Request 继续抓。
清洗交给 pipelines.py，导出交给 settings.py 的 FEEDS。

parse 里可以 yield 三种东西：
  - dict / Item：一条数据，进入 Pipeline 和导出；
  - Request：继续抓的新请求；
  - None：忽略（这里不写 return 就是 None）。

运行（在 Method_Scrapy/douban_top250 目录下）：
    ..\\.venv\\Scripts\\scrapy.exe crawl top250 -L INFO
"""

import scrapy

from douban_top250.items import Top250Item


class Top250Spider(scrapy.Spider):
    # name 是命令行用的唯一标识：scrapy crawl top250
    name = "top250"

    # 只允许抓这个域名，防止 follow 到站外（详情页也在 movie.douban.com）
    allowed_domains = ["movie.douban.com"]

    # 起始地址写死在 start_urls 里；要"固定 10 页"的写法见 top250_pages.py
    start_urls = ["https://movie.douban.com/top250?start=0&filter="]

    def parse(self, response):
        """回调：必须叫 parse，或者被显式指定为 callback。"""
        cards = response.css("ol.grid_view > li")

        if not cards:
            # 200 但空结果：通常是选择器过窄，或页面被换成了验证页/登录页。
            # 先看响应，不要直接怀疑"网站改版"。
            self.logger.warning(
                "没有解析到条目：%s（检查 ol.grid_view 是否存在、页面是否被拦截）",
                response.url,
            )

        for card in cards:
            # 短评：教材写法是 .quote .inq::text。2026 年的现行页面去掉了 inq 类，
            # 只剩 <p class="quote"><span>…</span></p>，所以这里用 or 兼容两种结构。
            quote = (
                card.css(".quote .inq::text").get()
                or card.css(".quote span::text").get()
                or ""
            )

            # get(default="") 避免字段缺失时拿到 None；转类型统一放 Pipeline 做
            yield Top250Item(
                rank=card.css(".pic em::text").get(default="").strip(),
                title=card.css(".hd a .title::text").get(default="").strip(),
                rating=card.css(".rating_num::text").get(default="").strip(),
                quote=quote.strip(),
                url=card.css(".hd a::attr(href)").get(),
            )

        self.logger.info("page %s: %d cards", response.url, len(cards))

        next_page = response.css(".paginator .next a::attr(href)").get()
        if next_page:
            # response.follow 会把相对地址（?start=25&filter=）拼成绝对 URL，
            # 并让新请求继承当前请求的 meta；比手写 urljoin 更不容易出错。
            # 最后一页没有"后页"链接，next_page 为 None，循环自然停止；
            # Scrapy 的 dupefilter 也会拦住重复 URL，双重保险。
            yield response.follow(next_page, callback=self.parse)
