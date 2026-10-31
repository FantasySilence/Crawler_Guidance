# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: locator 的定位、计数与取值                          #
# ================================================================ #

"""
02_locator_basics.py - Locator 的定位、计数与取值

对应《网络数据获取与爬虫入门指南》6.4：
  - 代码 6-3  用 locator 读取第一名
  - 表 6-2   豆瓣案例里的等待与定位（first / nth / get_by_text / all_inner_texts）

Playwright 的核心是 locator：它只描述"怎么找"，真正查询发生在调用 .count()、
.inner_text() 这类方法时。所以可以直接把 locator 先定义好，再等待、再取值。

运行：.venv/Scripts/python.exe 02_locator_basics.py
"""

from playwright.sync_api import expect, sync_playwright

URL = "https://movie.douban.com/top250?start=0&filter="
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA, locale="zh-CN")
        page = context.new_page()
        page.set_default_timeout(30_000)

        page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        # 动态页面里先等一下，再计数；否则 count() 可能立刻返回 0
        page.wait_for_selector("ol.grid_view > li")

        cards = page.locator("ol.grid_view > li")
        print("count:", cards.count())

        # 定位单个元素：first / nth(1) / last
        first = cards.first
        second = cards.nth(1)  # 0 基索引，nth(1) 是第二部
        print("first title:", first.locator(".hd a .title").first.inner_text())
        print("second title:", second.locator(".hd a .title").first.inner_text())
        print("last title:", cards.last.locator(".hd a .title").first.inner_text())

        # 取文本与取属性是两套 API：inner_text() / get_attribute()
        print("first rating:", first.locator(".rating_num").inner_text())
        print(
            "first href:",
            first.locator(".hd a").first.get_attribute("href"),
        )

        # 批量取文本：all_inner_texts() 返回列表。
        # 每张卡片通常有 1~2 个 span.title（中文名 + 原名），所以数量不一定是 25。
        titles = cards.locator(".hd a .title").all_inner_texts()
        print("title nodes:", len(titles), titles[:4])

        # 按文本找元素（表 6-2）：适合链接文字稳定的翻页按钮
        print("按文本命中'后页':", page.get_by_text("后页").count())

        # 断言数量：比 if count() == 25 更好，因为它会等、失败信息也更清楚
        expect(cards).to_have_count(25)

        # 2026 年的现行页面对短评做了一次改版：内层 span 去掉了 class="inq"。
        # 这两个数字说明教材选择器为何取不到短评，04_parse_page.py 里做了兼容。
        print("quote .inq count:", first.locator(".quote .inq").count())
        print("quote span count:", first.locator(".quote span").count())

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
