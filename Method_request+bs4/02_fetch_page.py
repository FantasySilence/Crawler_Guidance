"""
02_fetch_page.py - 取回豆瓣 Top250 第一页：状态码、编码、诊断、存原始 HTML

对应《网络数据获取与爬虫入门指南》：
  - 4.2  第一个请求：拿到豆瓣的 HTML（代码 4-3、4-4）
  - 4.3  会话、请求头、超时、重试与限速（代码 4-5、4-6、4-7）
  - 3.9  编码、实体与文本清洗（代码 3-6）

本节内容：
把 HTML 拿回来并确认它是对的。
先打印状态码、最终 URL、编码和 "grid_view" 是否存在，再谈解析——
把错误页当数据解析，是初学者最常见的一类 bug。

运行：.venv/Scripts/python.exe 02_fetch_page.py
输出：data/raw/top250_start0.html（原始响应，供 03_parse_cards.py 离线复现）
"""

from pathlib import Path
from urllib.error import URLError
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://movie.douban.com/top250"
ROBOTS_URL = "https://movie.douban.com/robots.txt"

# 代码 4-5：普通浏览器 UA + 中文偏好。
# 边界：用它只是让公开页面正常返回，不是伪装身份、绕过登录或风控。
# 如果豆瓣返回 403、验证码或要求登录，应当停止，而不是换代理、换账号继续。
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"


def build_session():
    """带请求头和有限重试的 Session（代码 4-5、4-6）。

    Retry 只解决"临时性失败"（429、5xx、连接抖动）。
    如果重试 3 次仍失败，说明问题不是临时性的：记录并停止，不要无限重试。
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    retry = Retry(
        total=3,
        backoff_factor=1.0,  # 约 0s、2s、4s 退避
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],  # 只重试幂等请求
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def check_robots():
    """
    用 RobotFileParser 做一次基本检查（代码 4-7）。

    robots.txt 只是最低门槛：它没有禁止，不代表服务条款允许批量采集。
    豆瓣的 robots.txt 里 Crawl-delay: 5 被注释掉了，本书仍按 5 秒执行。
    """
    rp = RobotFileParser()
    rp.set_url(ROBOTS_URL)
    try:
        rp.read()
    except URLError as exc:
        # robots.txt 拉不到时（网络抖动、临时故障）不要让整个脚本崩掉
        print("robots.txt 读取失败，跳过检查：", exc)
        return None

    allowed = rp.can_fetch(HEADERS["User-Agent"], BASE_URL)
    print("robots.txt 允许抓取 /top250:", allowed)
    return allowed


def fetch_html(session, start=0):
    """
    请求一页，返回 (html, resp)。

    params 里带 start 和 filter：start 是 25 的倍数，filter= 是豆瓣要求的空参数。
    """
    params = {"start": start, "filter": ""}
    resp = session.get(BASE_URL, params=params, timeout=30)

    # 代码 4-4：4xx/5xx 尽早暴露，避免把错误页当数据
    resp.raise_for_status()

    # 代码 3-6：编码优先信响应头，其次 apparent_encoding；豆瓣页面固定 UTF-8。
    # 判断错编码时，中文会变成"锟斤拷"或一堆问号。
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    resp.encoding = "utf-8"

    html = resp.text  # text 是解码后的字符串；content 才是原始字节
    if "grid_view" not in html:
        # 解析前先确认"榜单容器"存在。缺了它，后面所有选择器都会返回空列表。
        raise RuntimeError("响应中没有 grid_view：可能被拦截、页面改版，或这页不是榜单页")
    return html, resp


def save_raw_html(html, start=0):
    """
    把原始 HTML 原样落盘。以后调选择器直接读本地文件，不必反复请求豆瓣。
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"top250_start{start}.html"
    path.write_text(html, encoding="utf-8")
    return path


def main():
    check_robots()

    session = build_session()
    with session:  # Session 支持 with，退出时关闭连接池
        html, resp = fetch_html(session, start=0)

    # 第一批诊断信息：任何一项异常，都不要继续往下解析
    print("status:", resp.status_code)
    print("url:", resp.url)  # 最终 URL（含参数），写进数据附录做 provenance
    print("content-type:", resp.headers.get("content-type"))
    print("encoding:", resp.encoding)
    print("bytes:", len(resp.content))
    print("chars:", len(html))
    print("grid_view in html:", "grid_view" in html)

    path = save_raw_html(html, start=0)
    print("saved:", path)

    # 下一步：运行 03_parse_cards.py，用保存下来的 HTML 离线练习选择器。


if __name__ == "__main__":
    main()
