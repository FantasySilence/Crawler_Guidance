"""
03_api_paging.py - 分页、限流与重试

对应《网络数据获取与爬虫入门指南》2.5 节：
  - 代码 2-6  带限速与分页的 API 循环
  - 代码 2-7  给 Session 配置有限重试

两个部分，分别演示两种"抗抖动"的思路：
  Part A  fetch_world_bank()：自己写循环翻页，遇到 429 读 Retry-After 退避；
  Part B  build_session()：把 5xx/429 的重试交给 urllib3 的 Retry，代码更省。

注意：
  1. 重试必须有上限（否则接口故障时脚本会永远转圈）；
  2. 只对幂等的 GET 重试。POST 可能已经写入成功，"超时后重发"会造出重复订单。

运行：.venv/Scripts/python.exe 03_api_paging.py
"""

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://api.worldbank.org/v2"
INDICATOR = "NY.GDP.MKTP.CD"  # GDP（现价美元）

MAX_429_RETRIES = 3  # 同一页被限流时最多重试几次
DEFAULT_INTERVAL = 0.3  # 正常翻页之间的间隔（秒）


def fetch_world_bank(indicator=INDICATOR, country="CHN", max_pages=50, interval=DEFAULT_INTERVAL):
    """
    逐页抓取某个国别指标，返回全部观测值。

    世界银行 v2 的分页约定：page / per_page，元数据里的 pages 是总页数。
    别的接口可能是 offset/limit、cursor 或 next 链接——先读文档，再写循环，
    不要照抄别人的分页参数。

    max_pages 是护栏：参数写错（比如误传了全球指标）时，
    没有上限的循环会把几千页全拖一遍，既慢又可能把配额烧光。
    """
    url = f"{BASE_URL}/country/{country}/indicator/{indicator}"
    params = {"format": "json", "per_page": 100, "page": 1}
    rows = []

    for _ in range(max_pages):
        # ---- 同一页：处理 429 限流 ----
        for attempt in range(1, MAX_429_RETRIES + 1):
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code != 429:
                break
            # 429 不代表"被封"，接口通常用 Retry-After 告诉你等多久。
            # 这里假设它是秒数；严格起见可兼容 HTTP 日期格式。
            wait = int(resp.headers.get("Retry-After", "30"))
            print(f"429 限流：等待 {wait}s 后重试第 {params['page']} 页（第 {attempt} 次）")
            time.sleep(wait)
        else:
            # for-else：只有重试次数全部用尽（每次都是 429）才会走到这里，
            # 说明该停下来查配额和请求频率了，而不是继续硬打接口。
            raise RuntimeError(f"连续 {MAX_429_RETRIES} 次被限流，停止请求，先检查配额与频率")

        # 400/401/403/404/5xx 在这里统一抛错；429 已经在上面处理掉了
        resp.raise_for_status()
        payload = resp.json()
        # 结构校验和 02_api_worldbank.py 一样：接口出错时返回的可能是 {"message": [...]}，
        # 直接解包会得到"too many values to unpack"这种看不懂的报错。
        if not isinstance(payload, list) or len(payload) < 2:
            raise ValueError(f"API 返回异常：{str(payload)[:300]}")
        meta, data = payload[0], payload[1]

        if not data:  # 空页：通常是翻过了最后一页，也可能是检索条件没有匹配
            break
        rows.extend(data)

        # 到了最后一页就停。用 pages 判断，而不是"抓到空页才停"，
        # 这样不会多打一次请求，也不会依赖接口的边界行为。
        if params["page"] >= meta.get("pages", 1):
            break

        params["page"] += 1
        time.sleep(interval)  # 限速不是礼貌装饰，是保证不被封、数据不被截断的工程手段

    return rows


def build_session(retries=3, backoff=1.0):
    """
    返回一个挂了有限重试策略的 requests.Session。

    Retry 的参数含义：
      total            总重试次数（含首次失败）
      backoff_factor   退避系数，间隔约为 0, 2, 4 ... 秒
      status_forcelist 哪些状态码需要重试：限流 + 5xx
      allowed_methods  只对幂等方法重试，避免把写操作重发
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    # 两个前缀都挂上：只挂 https 的话，走 http 的源站不会应用这套重试
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_first_page(session, indicator=INDICATOR, country="CHN"):
    """
    用带重试的 Session 请求第一页，演示代码 2-7 的用法。
    """
    url = f"{BASE_URL}/country/{country}/indicator/{indicator}"
    params = {"format": "json", "per_page": 100, "page": 1}
    try:
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RetryError as exc:
        # Retry 次数用尽后 requests 抛 RetryError（里面是 urllib3 的 MaxRetryError）。
        # 这时不要再叠加外层重试，先确认接口状态。
        raise SystemExit(f"重试次数已用完，接口仍不可用：{exc}") from exc

    meta, data = resp.json()
    return meta, data


def main():
    print("[Part A] 手动分页 + 手动 429 退避")
    rows = fetch_world_bank()
    print("rows:", len(rows))
    # 接口默认按年份倒序返回，但不要依赖顺序：自己排序更稳
    dates = sorted(row["date"] for row in rows)
    print("range:", dates[0], "->", dates[-1])

    print()
    print("[Part B] Session 自动重试")
    session = build_session()
    with session:  # Session 支持 with，退出时关闭连接池
        meta, data = fetch_first_page(session)
    print("page 1 rows:", len(data or []))
    print("pages:", meta.get("pages"), "total:", meta.get("total"))


if __name__ == "__main__":
    main()
