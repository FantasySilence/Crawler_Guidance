# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 清洗与校验（DropItem）                              #
# ================================================================ #

"""
pipelines.py - 清洗与校验（指南 5.5，代码 5-5）

Pipeline 的执行顺序由 settings.py 里的 ITEM_PIPELINES 数字决定：数字小的先执行。
process_item() 必须返回 Item（或 dict），或者抛 DropItem；
如果什么都不返回，Scrapy 会报错，这一条数据就丢了。

这里的两个 Pipeline 分工：
  CleanTop250Pipeline     300  把"页面上的字符串"变成"能分析的类型"
  ValidateTop250Pipeline  400  过滤掉明显不合法的记录（抛 DropItem 并在日志里留痕）
"""

from scrapy.exceptions import DropItem


class CleanTop250Pipeline:
    """
    清洗：排名转 int、评分转 float、文本压掉多余空白（代码 5-5）。

    豆瓣页面上的排名和评分都是字符串（"1"、"9.7"），
    直接存进 CSV 会让后面的排序、筛选、求均值全部出错。
    """

    def process_item(self, item, spider):
        # item 是 Top250Item（也是 dict 子类），用 .get 兼容缺字段的情况
        rank = str(item.get("rank", "")).strip()
        rating = str(item.get("rating", "")).strip()

        # isdigit() 只认纯数字；".."、""、None 一律变成 None，不猜
        item["rank"] = int(rank) if rank.isdigit() else None
        item["rating"] = float(rating) if rating else None

        # " ".join(text.split()) 把换行、全角空格、连续空格压成一个空格
        # 比 replace("\xa0", "") 之类的逐字符替换更省心
        item["title"] = " ".join(str(item.get("title", "")).split())
        item["quote"] = " ".join(str(item.get("quote", "")).split())
        item["url"] = str(item.get("url", "")).strip()
        return item


class ValidateTop250Pipeline:
    """
    校验：缺排名、评分越界、URL 不像详情页，就丢弃这一条。

    抛 DropItem 是"主动丢弃"：Scrapy 会记一次 item_dropped_count，
    不会中断整个抓取。日志级别设为 WARNING，方便回头统计丢了多少条。
    """

    def process_item(self, item, spider):
        if not item.get("rank"):
            raise DropItem(f"缺少排名：{item.get('title')!r}")

        rating = item.get("rating")
        if rating is None or not 0 <= rating <= 10:
            raise DropItem(f"评分非法：{rating!r}（{item.get('title')!r}）")

        if "/subject/" not in (item.get("url") or ""):
            raise DropItem(f"URL 不像详情页：{item.get('url')!r}")

        return item
