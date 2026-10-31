# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 定义 Top250 的字段                                  #
# ================================================================ #

"""
items.py - 定义要抓的字段（指南 5.5，代码 5-4）

Item 只负责"声明字段"，不做任何清洗：
  - Spider 只负责抓：把页面上的文本原样交给 Item；
  - Pipeline 负责加工：转类型、压空白、校验、去重、入库。

这样以后换存储、加字段、改清洗规则，都不用动抓取逻辑。
"""

import scrapy


class Top250Item(scrapy.Item):
    """
    豆瓣 Top250 的一条电影记录。

    scrapy.Field() 只是占位符，不限制类型；类型转换统一交给 pipelines.py。
    字段顺序在这里不影响导出的列顺序（CSV 的顺序由 FEEDS 的 fields 或命令行决定）。
    """

    rank = scrapy.Field()  # 排名，1—250
    title = scrapy.Field()  # 中文片名
    rating = scrapy.Field()  # 评分，0.0—10.0
    quote = scrapy.Field()  # 短评，可能为空
    url = scrapy.Field()  # 详情页链接
