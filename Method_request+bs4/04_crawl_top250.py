# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 翻页、JSONL 断点、校验后导出 CSV                     #
# ================================================================ #

"""
04_crawl_top250.py - 完整闭环：10 页 → 250 条 → CSV/JSONL + 断点续跑

对应《网络数据获取与爬虫入门指南》：
  - 4.7  翻页：start 每次加 25（代码 4-13）
  - 4.8  保存：CSV、JSONL 与断点（代码 4-14、4-15、4-16）
  - 4.9  完整案例（代码 4-17）
  - 4.11 常见错误与排查（表 4-3）

流程：翻页（start = 0, 25, ..., 225）→ 解析 → 每页写 JSONL + 记录 done →
      从 JSONL 重放 → 校验（条数、排名连续、评分范围、URL 唯一）→ 写 CSV。

三个停止条件（比只写 range 更稳）：
  1. 没有下一页（解析到 0 条）；
  2. 达到 --pages 指定的最大页数；
  3. 这一页已经抓过（done 集合 / JSONL 去重）。
前两条是循环边界，第三条保证中断后不重复抓、也不重复写。

运行：
  .venv/Scripts/python.exe 04_crawl_top250.py --pages 1    # 先跑一页，核对字段
  .venv/Scripts/python.exe 04_crawl_top250.py              # 再跑全部 10 页

限速：豆瓣 robots.txt 里的 Crawl-delay: 5 虽被注释，本书按 5 秒执行。
      串行、不并发。遇到 403/验证码/登录要求就停下来，不要换代理硬绕。
"""

import argparse
import csv
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://movie.douban.com/top250"
PAGE_SIZE = 25
DELAY = 5.0  # 每次请求之间的间隔（秒）

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DONE_PATH = RAW_DIR / "douban_done.json"
JSONL_PATH = RAW_DIR / "douban_top250.jsonl"
CSV_PATH = PROCESSED_DIR / "douban_top250.csv"

# 字段顺序就是 CSV 的列顺序；和 03_parse_cards.py 的 parse_card 保持一致
FIELDS = ["rank", "title", "title_original", "rating", "votes", "quote", "url"]


# --------------------------------------------------------------------------
# 请求
# --------------------------------------------------------------------------
def build_session():
    """带请求头和有限重试的 Session（代码 4-5、4-6）。"""
    session = requests.Session()
    session.headers.update(HEADERS)
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_html(session, start):
    """请求某一页并返回 HTML（start=0 是第一页）。"""
    resp = session.get(BASE_URL, params={"start": start, "filter": ""}, timeout=30)
    resp.raise_for_status()  # 403/429/5xx 直接暴露
    resp.encoding = "utf-8"  # 豆瓣是 UTF-8，显式设置避免乱码
    return resp.text


# --------------------------------------------------------------------------
# 解析
# --------------------------------------------------------------------------
def parse_number(text):
    """从带单位的文本里取出数字（代码 3-7）："3353799人评价" -> 3353799.0。"""
    if text is None:
        return None
    s = str(text).replace(",", "").replace("，", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def clean_original_title(node):
    """第二个 .title 是 "/ 原名"，去掉前导斜杠和 &nbsp;（\\xa0）。"""
    text = node.get_text(strip=True).replace("\xa0", " ").strip()
    return text.lstrip("/ ").strip()


def parse_card(card):
    """从一个 <li> 卡片里抽取字段（代码 4-11），缺失字段给 None 或空串。

    两个字段要兼容新旧两种页面结构（与 03_parse_cards.py 保持一致）：
      - 短评：旧页面是 <span class="inq">，现行页面把 inq 类去掉了；
      - 评价人数：旧页面评分容器是 .star，现行页面没有这个类。
    """
    rank_node = card.select_one(".pic em")
    title_nodes = card.select(".hd a .title")
    rating_node = card.select_one(".rating_num")
    url_node = card.select_one(".hd a")

    quote_node = card.select_one(".quote .inq")
    if quote_node is None:
        quote_node = card.select_one(".quote span")

    votes_node = card.select_one(".star span:last-child")
    if votes_node is None:
        votes_node = next(
            (span for span in card.select(".bd span") if "人评价" in span.get_text()),
            None,
        )

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
    """解析一页，返回卡片列表；顺带把页码参数里的相对链接转成绝对 URL。"""
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("ol.grid_view > li")
    rows = [parse_card(card) for card in cards]
    for row in rows:
        row["url"] = urljoin(BASE_URL, row["url"])
    if len(rows) != PAGE_SIZE:
        print(f"  警告：本页解析到 {len(rows)} 条（预期 {PAGE_SIZE}），先检查选择器")
    return rows


# --------------------------------------------------------------------------
# 断点：done 记录"哪些 start 已经完成"，每页写完立即落盘
# --------------------------------------------------------------------------
def load_done(path=DONE_PATH):
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return set(json.load(f))


def save_done(done, path=DONE_PATH):
    """先写临时文件再 os.replace：即使此刻断电，也不会留下半个 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(sorted(done), f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# 保存：JSONL 逐页追加，CSV 由 JSONL 重放后生成
# --------------------------------------------------------------------------
def append_jsonl(rows, path=JSONL_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path=JSONL_PATH):
    """读回全部已抓的记录（含之前中断的运行），用于生成 CSV 和校验。"""
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def dedupe(rows):
    """按 URL 去重（重复抓取、翻页错位都可能造出重复行）。"""
    seen, unique = set(), []
    for row in rows:
        key = row.get("url") or f"rank:{row.get('rank')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return sorted(unique, key=lambda r: r["rank"] or 0)


def write_csv(rows, path=CSV_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig 带 BOM，Excel 双击打开中文不乱码
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


# --------------------------------------------------------------------------
# 校验：写文件之前先确认数据像不像真的
# --------------------------------------------------------------------------
def validate(rows, expected_count):
    """返回问题列表；空列表表示通过（表 4-3 的常见错误都能在这里暴露）。"""
    problems = []

    if expected_count is not None and len(rows) != expected_count:
        problems.append(f"条数 {len(rows)}，预期 {expected_count}")

    ranks = [row.get("rank") for row in rows]
    if any(rank is None for rank in ranks):
        problems.append("有记录的 rank 为空")
    elif sorted(ranks) != list(range(1, len(rows) + 1)):
        # 排名必须 1..N 连续：有缺口说明漏页，有重复说明翻页重复
        problems.append("rank 不是 1..N 连续（有缺口或重复）")

    bad_rating = [row["rank"] for row in rows
                  if row.get("rating") is None or not 0 <= row["rating"] <= 10]
    if bad_rating:
        problems.append(f"评分越界或缺失：{bad_rating[:10]}")

    bad_url = [row["rank"] for row in rows if "/subject/" not in (row.get("url") or "")]
    if bad_url:
        problems.append(f"URL 不像详情页：{bad_url[:10]}")

    return problems


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def main(pages=10):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    session = build_session()
    done = load_done()
    print(f"断点里已完成 {len(done)} 页")

    with session:
        for index, start in enumerate(range(0, pages * PAGE_SIZE, PAGE_SIZE), start=1):
            if start in done:
                print(f"skip start={start}（已完成，不重复抓）")
                continue

            try:
                html = fetch_html(session, start)
            except requests.HTTPError as exc:
                print(f"请求失败：{exc}")
                print("403/429 请停止采集并降速，不要换代理硬绕；已完成的页已写进 done，可稍后续跑")
                raise

            # 原始 HTML 按页存档：以后调选择器、对账都靠它，不覆盖
            (RAW_DIR / f"top250_start{start}.html").write_text(html, encoding="utf-8")

            rows = parse_page(html)
            if not rows:
                # 停止条件 1：没有下一页（或页面被拦截）。不要死循环。
                print("本页没有解析到条目，停止翻页")
                break

            append_jsonl(rows)
            done.add(start)
            save_done(done)  # 每页落盘一次：中断后从 done 恢复
            print(f"page {index}/{pages} start={start} rows={len(rows)} done={len(done)}")

            time.sleep(DELAY)  # 串行 + 固定间隔，最简单的限速

    # 从 JSONL 重放：这样断点续跑的 CSV 也完整（本次的 + 历史已完成页的）
    rows = dedupe(read_jsonl())
    if not rows:
        print("没有抓到任何数据，不写 CSV")
        return None
    print("总条数（去重后）:", len(rows))

    # 预期条数按"已完成页数"算，而不是本次 --pages：
    # 中断续跑时 done 里可能有更多页，CSV 应该覆盖它们。
    expected = len(done) * PAGE_SIZE if done else None
    problems = validate(rows, expected)
    if problems:
        print("数据校验未通过：")
        for problem in problems:
            print("  -", problem)
        print("先别覆盖已有 CSV：按提示回去查选择器、翻页或去重逻辑")
        return None

    csv_path = write_csv(rows)
    print("校验通过，csv:", csv_path)
    return csv_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抓取豆瓣电影 Top250 榜单")
    parser.add_argument(
        "--pages", type=int, default=10,
        help="抓几页（每页 25 条，默认 10 页共 250 条）",
    )
    args = parser.parse_args()
    main(pages=args.pages)
