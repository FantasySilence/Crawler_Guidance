# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 完整案例：抓两页并保存 CSV                           #
# ================================================================ #

"""
05_crawl_two_pages.py - 完整案例：抓两页并保存 CSV

对应《网络数据获取与爬虫入门指南》6.10：
  - 代码 6-9  Playwright 抓取豆瓣前两页

流程和 requests 版本完全对应：翻页 → 解析 → 校验 → 保存。
区别只在于"翻页"是点 .paginator .next a，而不是改 start 参数。

说明：本文件自带 parse_page（与 04_parse_page.py 相同），
     这样单独运行本脚本即可，不依赖其他文件。

运行：.venv/Scripts/python.exe 05_crawl_two_pages.py
输出：data/processed/douban_top250_playwright.csv（utf-8-sig）
"""

import csv
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://movie.douban.com/top250?start=0&filter="
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
FIELDS = ["rank", "title", "rating", "quote", "url"]

PROCESSED_DIR = Path(__file__).resolve().parent / "data" / "processed"


def read_quote(card):
    """取短评，兼容教材版（.inq）与现行页面（无 inq 类）。"""
    for selector in (".quote .inq", ".quote span"):
        node = card.locator(selector)
        if node.count():
            return node.first.inner_text().strip()
    return ""


def parse_page(page):
    """解析当前页，返回卡片列表；调用前应先 wait_for_selector。"""
    rows = []
    for card in page.locator("ol.grid_view > li").all():
        rows.append(
            {
                # inner_text() 拿到的是字符串：排名转 int、评分转 float，
                # 这样排序、校验、写 CSV 时不会把 "9.7" 当成文本
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
    rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA, locale="zh-CN")
        page = context.new_page()
        page.set_default_timeout(30_000)

        page.goto(URL, wait_until="domcontentloaded", timeout=30_000)

        # 只抓两页：每页 25 条，两页正好 50 条
        for index in range(2):
            page.wait_for_selector("ol.grid_view > li")
            page_rows = parse_page(page)
            rows.extend(page_rows)
            print(f"page {index + 1}: rows {len(page_rows)}")

            # 最后一页没有"后页"链接，用 count() 判断，避免点到不存在的元素
            next_link = page.locator(".paginator .next a")
            if not next_link.count():
                break
            next_link.click()
            # 点击后等导航完成；下一轮循环会继续等榜单重新渲染
            page.wait_for_load_state("domcontentloaded")

        # 先关 page/context，再关 browser；长期运行时要避免 page 泄漏
        context.close()
        browser.close()

    # 保存前先做一次简单核对：条数、排名是否连续、有没有重复
    ranks = [row["rank"] for row in rows]
    print("rows:", len(rows), "unique ranks:", len(set(ranks)))
    if sorted(ranks) != list(range(1, len(rows) + 1)):
        print("警告：排名不是 1..N 连续，先检查是否漏页或重复抓取")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = PROCESSED_DIR / "douban_top250_playwright.csv"
    # utf-8-sig 带 BOM，Excel 双击打开中文不乱码
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print("csv:", csv_path)


if __name__ == "__main__":
    main()
