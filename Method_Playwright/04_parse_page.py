# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 抽取一页的排名、片名、评分与短评                      #
# ================================================================ #

"""
04_parse_page.py - 抽取一页：排名、片名、评分、短评、链接

对应《网络数据获取与爬虫入门指南》6.6：
  - 代码 6-5  用 Playwright 抽取一页的五个字段

做法和 BeautifulSoup 一样：先定位卡片，再在卡片内部取字段。
locator 是"惰性"的，作用域挂在 card 上，就不会把导航栏、页脚的文字混进来。

运行：.venv/Scripts/python.exe 04_parse_page.py
"""

from playwright.sync_api import sync_playwright

URL = "https://movie.douban.com/top250?start=0&filter="
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def read_quote(card):
    """取短评；没有短评时返回空字符串。

    教材写法是 .quote .inq，但 2026 年的现行页面把内层 span 的 class 去掉了，
    只剩 <p class="quote"><span>…</span></p>。先试旧结构，落空再退回新结构。
    """
    for selector in (".quote .inq", ".quote span"):
        node = card.locator(selector)
        if node.count():
            return node.first.inner_text().strip()
    return ""


def parse_page(page):
    """解析当前页面，返回该页所有卡片。调用前应先 wait_for_selector 等榜单渲染。"""
    rows = []
    cards = page.locator("ol.grid_view > li")
    for card in cards.all():
        rows.append(
            {
                # inner_text() 拿到的是字符串：排名转 int、评分转 float，
                # 后面做排序、校验、存 CSV 才不会把 "9.7" 当成文本
                "rank": int(card.locator(".pic em").inner_text().strip()),
                "title": card.locator(".hd a .title").first.inner_text().strip(),
                "rating": float(card.locator(".rating_num").inner_text().strip()),
                "quote": read_quote(card),
                # 详情链接是属性，不是文本：用 get_attribute
                "url": card.locator(".hd a").first.get_attribute("href"),
            }
        )
    return rows


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA, locale="zh-CN")
        page = context.new_page()
        page.set_default_timeout(30_000)

        page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_selector("ol.grid_view > li")

        rows = parse_page(page)
        print("rows:", len(rows))

        # 逐字段打印第一条，和浏览器 Elements 面板核对
        for key, value in rows[0].items():
            print(f"  {key:<8} = {value!r}")

        # 短评不是每部都有：统计缺失，而不是假设一定有
        no_quote = [row["rank"] for row in rows if not row["quote"]]
        print("没有短评的排名:", no_quote)

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
