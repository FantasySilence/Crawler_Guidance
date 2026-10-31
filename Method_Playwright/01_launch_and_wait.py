# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 启动 Chromium，等待榜单并保存整页截图                #
# ================================================================ #

"""
01_launch_and_wait.py - 打开豆瓣 Top250，等榜单出现

对应《网络数据获取与爬虫入门指南》6.2、6.3、6.7：
  - 代码 6-1  安装 Playwright 与 Chromium
  - 代码 6-2  打开豆瓣 Top250 并等待 25 个条目
  - 6.7  截图与调试

这一节只做一件事：用真实浏览器打开页面，确认榜单真的渲染出来了。
先拿到 title 和条目数，再谈解析——不要一上来就写选择器循环。

关于 headless：
  - headless=True 不显示窗口，适合脚本和服务器；
  - 调试时改成 headless=False 并加 slow_mo=300，能看清每一步；
  - 还可以设环境变量 PWDEBUG=1，配合 page.pause() 单步。

运行：.venv/Scripts/python.exe 01_launch_and_wait.py
输出：data/raw/douban_top250_page1.png（整页截图，失败时先看它）
"""

from pathlib import Path

from playwright.sync_api import expect, sync_playwright

URL = "https://movie.douban.com/top250?start=0&filter="

# 与 requests 版本保持一致的桌面 UA。它只是让公开页面正常返回，
# 不是伪造指纹或绕过风控；遇到验证码/登录墙应停止，而不是加代理硬绕。
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"


def main():
    # sync_playwright() 适合脚本；在 FastAPI、Scrapy 这类异步框架里用 async_playwright()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # context 相当于一个独立的浏览器会话：Cookie、UA、语言都在这里设置
        context = browser.new_context(user_agent=UA, locale="zh-CN")
        page = context.new_page()

        # 6.8 的提醒：给页面设默认超时，避免某个元素不存在时无限等待
        page.set_default_timeout(30_000)
        page.set_default_navigation_timeout(30_000)

        # wait_until 用 domcontentloaded，不要默认 networkidle：
        # 有轮询、长连接或广告的页面可能永远不"空闲"，networkidle 会一直等到超时。
        page.goto(URL, wait_until="domcontentloaded", timeout=30_000)

        # 等到榜单容器里出现 <li> 再继续；这比 time.sleep(5) 稳，也更快
        page.wait_for_selector("ol.grid_view > li")

        print("title:", page.title())

        cards = page.locator("ol.grid_view > li")
        print("cards:", cards.count())

        # expect 是"断言 + 等待"：最多等默认超时，期间反复检查数量是否为 25
        expect(cards).to_have_count(25)
        print("expect 25 cards: ok")

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        shot = RAW_DIR / "douban_top250_page1.png"
        page.screenshot(path=str(shot), full_page=True)
        print("screenshot:", shot)

        # 先关 page/context，再关 browser；长期运行时这一步能避免内存一直涨
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
