"""
03_parse_cards.py - 用 BeautifulSoup 从卡片里抽字段

对应《网络数据获取与爬虫入门指南》：
  - 4.4  BeautifulSoup 的基本操作（代码 4-9、4-10，表 4-1）
  - 4.5  抽取一个电影条目（代码 4-11）
  - 3.9  清洗带单位的数字（代码 3-7）
  - 4.6  列表页 → 详情页：先收集链接（代码 4-12）

先读本地 HTML（02_fetch_page.py 存下来的原始页面），没有才现场请求一次。
这就是指南推荐的排查顺序：把 HTML 存到本地，用同一个选择器反复调试，
而不是每改一行代码就重新打一次豆瓣。

运行：.venv/Scripts/python.exe 03_parse_cards.py
"""

import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://movie.douban.com/top250"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

BASE_DIR = Path(__file__).resolve().parent
RAW_PATH = BASE_DIR / "data" / "raw" / "top250_start0.html"


def load_html():
    """优先用本地原始文件；没有时抓一次并保存。"""
    if RAW_PATH.exists():
        print("使用本地文件:", RAW_PATH)
        return RAW_PATH.read_text(encoding="utf-8")

    print("本地没有原始 HTML，现场请求一次……")
    resp = requests.get(BASE_URL, params={"start": 0, "filter": ""}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"  # 豆瓣页面是 UTF-8，显式设置避免乱码

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(resp.text, encoding="utf-8")
    return resp.text


def parse_number(text):
    """
    从带单位的文本里取出数字（代码 3-7）。

    parse_number("3353799人评价") -> 3353799.0
    parse_number("9.7")           -> 9.7
    parse_number("暂无评分")       -> None
    注意：它只取数字、不保留单位。"%""亿元""万人"这类字段，
    单位要单独存一列，否则合并数据时会出错。
    """
    if text is None:
        return None
    s = str(text).replace(",", "").replace("，", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def clean_original_title(node):
    """第二个 .title 是 "/ 原名"，去掉前导的斜杠和 &nbsp;（\\xa0）。"""
    text = node.get_text(strip=True).replace("\xa0", " ").strip()
    return text.lstrip("/ ").strip()


def parse_card(card):
    """从一个 <li> 卡片里抽取字段（代码 4-11）。

    每个字段都先判断节点是否存在：豆瓣条目不一定有短评，也不一定有原名。
    找不到时返回 None 或空字符串，不要假设字段一定存在。
    """
    rank_node = card.select_one(".pic em")
    title_nodes = card.select(".hd a .title")  # 第一个是中文名，第二个是原名
    rating_node = card.select_one(".rating_num")
    url_node = card.select_one(".hd a")

    # 短评：指南的写法是 .quote .inq。但 2026 年的现行页面把内层 span 的
    # class="inq" 去掉了，只剩 <p class="quote"><span>…</span></p>，
    # 于是 .quote .inq 一个都匹配不到。先试旧结构，落空再退回 .quote span。
    quote_node = card.select_one(".quote .inq")
    if quote_node is None:
        quote_node = card.select_one(".quote span")

    # 评价人数：同样受页面改版影响，评分容器已经不再带 class="star"，
    # .star span:last-child 也会落空。退回"文本里含人评价"的 span，
    # 比猜 div 的层级更稳。
    votes_node = card.select_one(".star span:last-child")
    if votes_node is None:
        votes_node = next(
            (span for span in card.select(".bd span") if "人评价" in span.get_text()),
            None,
        )

    # 评分是小数、人数带"人评价"、排名是整数：解析时就要转成正确类型
    votes = parse_number(votes_node.get_text(strip=True)) if votes_node else None

    return {
        "rank": int(rank_node.get_text(strip=True)) if rank_node else None,
        "title": title_nodes[0].get_text(strip=True) if title_nodes else "",
        "title_original": clean_original_title(title_nodes[1]) if len(title_nodes) > 1 else "",
        "rating": float(rating_node.get_text(strip=True)) if rating_node else None,
        "votes": int(votes) if votes is not None else None,
        "quote": quote_node.get_text(strip=True) if quote_node else "",
        "url": url_node.get("href") if url_node else "",
    }


def parse_page(html):
    """解析一页，返回该页所有卡片。"""
    soup = BeautifulSoup(html, "lxml")  # lxml 快、容错好
    cards = soup.select("ol.grid_view > li")
    if len(cards) != 25:
        # 正常一页 25 条。数量不对，通常是选择器太窄或页面结构变了。
        print(f"警告：本页解析到 {len(cards)} 条（预期 25），先检查 ol.grid_view 是否还在")
    return [parse_card(card) for card in cards]


def collect_links(html):
    """从列表页收集详情页链接（代码 4-12）。"""
    soup = BeautifulSoup(html, "lxml")
    links = []
    for card in soup.select("ol.grid_view > li"):
        a = card.select_one(".hd a")
        if a and a.get("href"):
            # urljoin 把相对链接（如 ?start=25）转成绝对 URL
            links.append(urljoin(BASE_URL, a["href"]))
    return links


def main():
    html = load_html()
    soup = BeautifulSoup(html, "lxml")

    # 表 4-1 的几个方法，先确认树建对了
    print("title:", soup.title.get_text(strip=True))
    print("cards:", len(soup.select("ol.grid_view > li")))

    rows = parse_page(html)
    print("rows:", len(rows))

    # 第一条完整打印出来，逐字段和浏览器 Elements 面板核对
    first = rows[0]
    for key, value in first.items():
        print(f"  {key:<14} = {value!r}")

    # 缺失字段是常态：统计一下有多少条没有短评
    no_quote = [row["rank"] for row in rows if not row["quote"]]
    print("没有短评的排名:", no_quote)

    # 详情链接：先收集，不要在这一步就进详情页
    links = collect_links(html)
    print("links:", len(links), links[:2])

    # 3.9 的清洗函数，单独验证三种输入
    print("parse_number 演示:", parse_number("3353799人评价"), parse_number("9.7"), parse_number("暂无评分"))


if __name__ == "__main__":
    main()
