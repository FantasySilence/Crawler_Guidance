# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 复用浏览器与页面，控制资源开销                        #
# ================================================================ #

"""
07_reuse_context.py - 复用浏览器与页面

对应《网络数据获取与爬虫入门指南》6.8：
  - 代码 6-7  复用浏览器与页面

Playwright 的开销主要在浏览器进程上。不要为每个 URL 启动一个浏览器，
正确做法是：一个 browser + 一个 context + 少量 page 复用，并给每个页面设超时。
豆瓣只有 10 页，串行足够；真要并发，也应该用信号量限制同时在跑的页面数。

运行：.venv/Scripts/python.exe 07_reuse_context.py
"""

from playwright.sync_api import sync_playwright

URL_TEMPLATE = "https://movie.douban.com/top250?start={start}&filter="
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
STARTS = (0, 25)  # 第一页、第二页


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 同一个 context 共享 Cookie 和 Session，最接近"一个用户连续访问"
        context = browser.new_context(user_agent=UA, locale="zh-CN")
        try:
            pages = [context.new_page() for _ in STARTS]
            for page, start in zip(pages, STARTS):
                page.set_default_timeout(30_000)
                page.goto(
                    URL_TEMPLATE.format(start=start),
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
                page.wait_for_selector("ol.grid_view > li")
                cards = page.locator("ol.grid_view > li")
                first_rank = page.locator(".pic em").first.inner_text()
                print(f"start={start}: cards={cards.count()} first_rank={first_rank}")
        finally:
            # 用 finally 保证异常时也能关掉：page/context 不关，内存会一直涨
            # 长时间运行的脚本，定期重启浏览器比无限复用更稳
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
