# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 点击“后页”翻到第二页并核对排名                       #
# ================================================================ #

"""
03_click_next_page.py - 点击"后页"翻到第二页

对应《网络数据获取与爬虫入门指南》6.5：
  - 代码 6-4  点击后页并抽取第二页

豆瓣的分页是普通链接（?start=25&filter=），Playwright 可以直接点击，
再等 URL 变化和榜单刷新，不需要自己拼 URL。

运行：.venv/Scripts/python.exe 03_click_next_page.py
"""

import re

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
        page.wait_for_selector("ol.grid_view > li")

        cards = page.locator("ol.grid_view > li")
        print("page 1 cards:", cards.count())
        print("page 1 first rank:", page.locator(".pic em").first.inner_text())

        next_link = page.locator(".paginator .next a")
        # 先确认"后页"链接存在：第一页有，最后一页没有
        expect(next_link).to_have_count(1)

        # click() 会等元素可点击，并等这次点击触发的导航完成
        next_link.click()

        # 等待 URL 变化。这里用正则而不是 glob：
        # glob 里的 ? 和 * 都是通配符，像 top250?start=25 这样的 URL 容易被误匹配，
        # 正则写成 \? 才是字面量问号。
        page.wait_for_url(re.compile(r".*top250\?start=25.*"))

        # 等新一页的榜单重新渲染出来，再读取
        page.wait_for_selector("ol.grid_view > li")

        print("page 2 cards:", cards.count())
        # 第二页第一条的排名应该是 26（第一页是 1~25）
        print("page 2 first rank:", page.locator(".pic em").first.inner_text())

        # 如果点击后没有跳转：先看是否出现弹窗、登录墙或验证页，
        # 不要靠加大 sleep 硬等。
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
