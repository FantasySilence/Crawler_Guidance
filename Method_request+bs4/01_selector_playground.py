# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 用教材版示例 HTML 离线练习 CSS 选择器                #
# ================================================================ #

"""
01_selector_playground.py - 离线练 CSS 选择器（对应指南第 3 章）

对应《网络数据获取与爬虫入门指南》：
  - 3.2  最小 HTML 文档（代码 3-1 的结构，见 fixtures/douban_top250_sample.html）
  - 3.3  标签、属性与文本（表 3-2）
  - 3.5  七个字段分别在哪个选择器下（表 3-3）
  - 3.6  CSS 选择器够用清单（表 3-4、代码 3-4）
  - 3.10 选择器稳定性分级（表 3-6）

这个脚本不联网：直接解析 fixtures 里的示例 HTML。
好处是可以放心改选择器、看哪里会取空，而不必反复请求豆瓣。
运行：.venv/Scripts/python.exe 01_selector_playground.py
"""

from pathlib import Path

from bs4 import BeautifulSoup

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "douban_top250_sample.html"

# 表 3-3：豆瓣 Top250 的七个字段位置。
# 最后一项 "href" 表示取属性，其余取文本（get_text）。
FIELDS = [
    ("排名", ".pic em", "text"),
    ("片名", ".hd a .title", "text"),
    ("评分", ".rating_num", "text"),
    ("评价人数", ".star span:last-child", "text"),
    ("短评", ".quote .inq", "text"),
    ("详情链接", ".hd a", "href"),
    ("下一页", ".paginator .next a", "href"),
]

# 表 3-4/代码 3-4 里的其他写法：这里只数命中数量，体会"同一页有多种定位方式"。
EXTRA_SELECTORS = [
    ("所有条目（直接子节点）", "ol.grid_view > li"),
    ("评分属性匹配", '[property="v:average"]'),
    ("href 以详情页开头", 'a[href^="https://movie.douban.com/subject/"]'),
    ("href 以电影 ID 结尾", 'a[href$="/1292052/"]'),
    ("href 含 subject", 'a[href*="/subject/"]'),
    ("第二部电影（按位置）", "li:nth-child(2)"),
    ("片名与评分（并集）", ".title, .rating_num"),
]


def describe(node, mode):
    """按 mode 取文本或 href；node 为 None 时返回 <缺失>。"""
    if node is None:
        # select_one() 找不到时返回 None，继续调 .get_text() 会抛
        # AttributeError: 'NoneType' object has no attribute 'get_text'
        return "<缺失>"
    if mode == "href":
        return node.get("href")
    return node.get_text(strip=True)


def main():
    html = FIXTURE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")  # lxml 快、容错好；没装时可用 "html.parser"

    print("页面标题:", soup.title.string)
    print("条目数:", len(soup.select("ol.grid_view > li")))
    print()

    print("== 表 3-3：七个字段 ==")
    for label, selector, mode in FIELDS:
        nodes = soup.select(selector)
        first = nodes[0] if nodes else None
        print(f"  {label:<6} {selector:<28} 命中 {len(nodes)} 个 | 第一个: {describe(first, mode)}")
    print("  提示: 下一页的 href 是相对地址（?start=25&filter=），")
    print("        拼成绝对 URL 要用 urllib.parse.urljoin，见 03_parse_cards.py")
    print()

    print("== 表 3-4：其他常用写法 ==")
    for label, selector in EXTRA_SELECTORS:
        print(f"  {label:<16} {selector:<40} 命中 {len(soup.select(selector))} 个")
    print()

    # 3.4 的思路：先定位卡片，再在卡片内部取字段，避免把导航栏、页脚的文字混进来。
    cards = soup.select("ol.grid_view > li")
    first_card = cards[0]
    print("== 卡片内取值（第 1 条）==")
    print("  排名:", first_card.select_one(".pic em").get_text(strip=True))
    print("  片名:", first_card.select_one(".hd a .title").get_text(strip=True))
    print("  评分:", first_card.select_one(".rating_num").get_text(strip=True))
    print("  短评:", first_card.select_one(".quote .inq").get_text(strip=True))
    print()

    # 3.5 的提醒：短评不是每部都有，必须先判断节点是否存在。
    no_quote = [card.select_one(".pic em").get_text(strip=True) for card in cards
                if card.select_one(".quote .inq") is None]
    print("没有短评的条目（排名）:", no_quote)
    print()

    # 注意：::text、::attr(href) 是 Scrapy/parsel 的扩展语法，BeautifulSoup 不认。
    # BeautifulSoup 里对应写 tag.get_text() 和 tag.get("href")，就是上面 describe() 做的事。


if __name__ == "__main__":
    main()
