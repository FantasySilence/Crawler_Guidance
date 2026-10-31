"""
06_dynamic_vs_static.py - 同一个 URL：requests 看不到，Playwright 能看到

对应《网络数据获取与爬虫入门指南》6.11：
  - 代码 6-10  同一个 URL：requests 看不到，Playwright 能看到
  - 表 6-3    静态页与动态页的对照

豆瓣 Top250 的榜单写在第一次返回的 HTML 里，所以用 requests 就够了；
这个脚本换成一个真正由 JavaScript 渲染的公开教学沙盒 quotes.toscrape.com/js/：
  - requests 拿到的 HTML 只有空容器，div.quote 数量是 0；
  - Playwright 等 JS 注入后，div.quote 是 10 条。

注意：quotes.toscrape.com 只是教学沙盒，不是数据源，
     这里只用来说明"第一次 HTML 里没有数据"时浏览器才不可替代。

运行：.venv/Scripts/python.exe 06_dynamic_vs_static.py
"""

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL = "https://quotes.toscrape.com/js/"


def fetch_with_requests():
    """A. requests：只拿到服务器第一次返回的 HTML，不执行 JS。"""
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()

    # 解析器用 lxml（快、容错好）
    # 换到没装 lxml 的机器时，这里可以改成 "html.parser"（标准库，无需安装）。
    soup = BeautifulSoup(resp.text, "lxml")
    cards = soup.select("div.quote")
    print("requests status:", resp.status_code)
    print("requests div.quote:", len(cards))  # 0：数据是 JS 注入的
    return cards


def fetch_with_playwright():
    """B. Playwright：等 JS 执行完、元素出现后再取。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(30_000)

        page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        # 关键的一步：等 JS 把 div.quote 注入进来，而不是固定 sleep
        page.wait_for_selector("div.quote")

        rows = []
        for card in page.locator("div.quote").all():
            rows.append(
                {
                    "quote": card.locator("span.text").inner_text().strip(),
                    # 沙盒的引号外面还包着弯引号，做数据分析前要清洗
                    "author": card.locator("small.author").inner_text().strip(),
                    "tags": ";".join(card.locator("a.tag").all_inner_texts()),
                }
            )

        browser.close()
        return rows


def main():
    cards = fetch_with_requests()
    rows = fetch_with_playwright()

    print("playwright div.quote:", len(rows))  # 10
    print("first row:", rows[0])

    # 结论：先判断数据在不在第一次 HTML 里。
    # 动态页的处理顺序：
    #   ① Network 里找返回 JSON 的 XHR，能复现就用 requests；
    #   ② 数据写在内联 <script> 数组里，可以解析脚本，但结构易变；
    #   ③ 只能靠浏览器渲染/点击/滚动/登录时，才用 Playwright。
    print("差距：requests", len(cards), "条，playwright", len(rows), "条")


if __name__ == "__main__":
    main()
