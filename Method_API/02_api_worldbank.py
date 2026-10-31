# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 调用世界银行无 key 接口：校验结构后转 DataFrame       #
# ================================================================ #

"""
02_api_worldbank.py - 官方 API 入门：世界银行（不需要 key）

对应《网络数据获取与爬虫入门指南》2.3 节：
  - 代码 2-2  调用世界银行 API 并转成 DataFrame
  - 代码 2-3  先检查响应结构，再解析

本节内容：
  1. 用 requests 发一个带查询参数的 GET 请求；
  2. 先校验响应结构，再解析（不要直接对 None 取下标）；
  3. 把观测值转成 DataFrame，并把缺失值显式标记为 NaN，而不是悄悄补 0。

接口说明（世界银行 v2，无需 key、无需登录）：
  https://api.worldbank.org/v2/country/{国别}/indicator/{指标}
  - 国别：三位代码，如 CHN（中国）、USA（美国）、WLD（全世界）
  - 指标：NY.GDP.MKTP.CD = GDP（现价美元）
  - 响应固定是一个"两元素列表"：
        payload[0] = 元数据 {"page": 1, "pages": 1, "per_page": 100, "total": 65, ...}
        payload[1] = 观测值列表 [{"date": "2024", "value": 18791744304280.0, ...}, ...]
    参数写错时 payload[1] 可能是 None，甚至整个 payload 变成 {"message": [...]}。

运行：.venv/Scripts/python.exe 02_api_worldbank.py
（若控制台中文乱码，先执行 chcp 65001，或设 PYTHONIOENCODING=utf-8）
"""

import pandas as pd
import requests

# 接口的公共前缀。把它和路径分开写，换国家/指标时只改调用处的参数。
BASE_URL = "https://api.worldbank.org/v2"
INDICATOR = "NY.GDP.MKTP.CD"  # GDP（现价美元）


def fetch_payload(country="CHN", indicator=INDICATOR):
    """请求世界银行指标接口，返回 (payload, resp)。

    resp 也要返回：出问题时我们想看到 status_code 和最终 URL，
    这两个信息在写数据附录、复现结果时同样需要。
    """
    url = f"{BASE_URL}/country/{country}/indicator/{indicator}"
    # per_page=100、page=1：本指标共约 65 条观测，一页就够。
    # 需要多页时要判断 meta["pages"] 再翻页，见 03_api_paging.py。
    params = {"format": "json", "per_page": 100, "page": 1}

    # timeout 必填：不设的话，遇到 DNS 或网络异常时脚本可能一直挂着。
    resp = requests.get(url, params=params, timeout=30)

    # raise_for_status(): 4xx/5xx 直接抛 HTTPError。
    # 不检查状态码就把错误页当数据解析，是初学者最常见的一类 bug。
    resp.raise_for_status()
    return resp.json(), resp


def parse_payload(payload):
    """校验响应结构，返回 (meta, rows)。

    世界银行的正常响应是 [meta, rows]；
    rows 为 None 通常意味着国别代码、指标代码或分页参数有问题。
    """
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        # 把原始响应打进异常里，方便直接看到接口自己的错误信息
        raise ValueError(f"API 返回异常：{payload}")
    return payload[0], payload[1]


def rows_to_frame(rows):
    """把观测值列表转成按年份升序排列的 DataFrame。"""
    # 只保留两列：date（年份字符串）和 value（字符串或 null）
    df = pd.DataFrame(rows)[["date", "value"]]

    # value 可能是数字、字符串、null、".." 或空字符串：
    # 统一用 to_numeric(errors="coerce") 转数值，解析不出来的记为缺失(NaN)。
    # 不要用 fillna(0)：那会把"尚未公布"伪装成"等于 0"，直接污染回归结果。
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # 接口里 date 是 "2024" 这样的四位数年份，用 format="%Y" 明确告诉 pandas 格式
    df["date"] = pd.to_datetime(df["date"], format="%Y")

    return df.sort_values("date").reset_index(drop=True)


def main():
    payload, resp = fetch_payload()
    meta, rows = parse_payload(payload)
    df = rows_to_frame(rows)

    # 这三个信息建议每次都打印/记录：状态码正常，后面的解析才有意义
    print("status:", resp.status_code)
    print("url:", resp.url)  # resp.url 是拼好参数的完整地址，可直接写进数据附录
    print("content-type:", resp.headers.get("content-type"))

    # 元数据里带着分页和版本信息：lastupdated 是数据修订时间，写论文时要引用
    keys = ("page", "pages", "per_page", "total", "lastupdated")
    print("meta:", {k: meta.get(k) for k in keys})

    print("rows:", len(df))
    print("missing value:", int(df["value"].isna().sum()))

    # 打印最近 10 年。尾部是新的、头部是 1960 年的老数据。
    with pd.option_context("display.max_rows", 10, "display.width", 120):
        print(df.tail(10))


if __name__ == "__main__":
    main()
