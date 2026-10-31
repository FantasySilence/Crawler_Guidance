# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 原始 JSON 与 manifest 留存，摊平后落 CSV             #
# ================================================================ #

"""
04_api_json_to_table.py - 从 JSON 到分析表：原样留存 + 摊平 + 落盘

对应《网络数据获取与爬虫入门指南》：
  - 2.6  从 JSON 到表格                代码 2-8
  - 2.9  API 取数检查清单              表 2-4（原始数据要保存 JSON + 抓取时间 + URL）

处理顺序（不要颠倒）：
  1. 请求接口，拿到 payload；
  2. 原始 JSON 原样落盘，另写一份 manifest 记录 URL / 抓取时间 / 状态码 / sha256；
     —— 这一步是"证据"，以后要换解析逻辑，靠它重放，不用再麻烦接口；
  3. 用 pandas.json_normalize 摊平嵌套字段，挑列、改类型、统计缺失比例；
  4. 存中间结果 CSV，供后面分析用。

目录（沿用 data/raw、data/interim 分层）：
  Method_API/data/raw/wb_gdp.json            原始响应，不覆盖、不加工
  Method_API/data/raw/wb_gdp.manifest.json   取数证据（URL、时间、状态码、哈希）
  Method_API/data/interim/wb_gdp.csv         摊平后的分析表

运行：.venv/Scripts/python.exe 04_api_json_to_table.py
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.worldbank.org/v2"
INDICATOR = "NY.GDP.MKTP.CD"  # GDP（现价美元）
COUNTRY = "CHN"

# 用 __file__ 定位目录：无论从仓库根目录还是 Method_API 目录运行，
# 输出都落在 Method_API/data 下，不会因为当前工作目录不同而写散。
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
INTERIM_DIR = BASE_DIR / "data" / "interim"


def fetch(country=COUNTRY, indicator=INDICATOR):
    """请求接口，返回 (payload, resp)。"""
    url = f"{BASE_URL}/country/{country}/indicator/{indicator}"
    params = {"format": "json", "per_page": 100, "page": 1}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    payload = resp.json()
    # 先校验结构，别急着 json_normalize：结构不对时摊平出来的是一张空表，
    # 后面每一步都会"正常"地跑完，错误被藏得很深。
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        raise ValueError(f"API 返回异常：{str(payload)[:300]}")
    return payload, resp


def save_raw(payload, resp, stem="wb_gdp"):
    """原始 JSON 原样落盘，并写 manifest。返回 (raw_path, manifest)。"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_DIR / f"{stem}.json"
    # ensure_ascii=False：保留中文和其他非 ASCII 字符，便于人工核对
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "source": "World Bank API v2",
        "url": resp.url,  # 含全部查询参数的完整地址
        "status_code": resp.status_code,
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "content_type": resp.headers.get("content-type"),
        "bytes": len(resp.content),
        # sha256 用来判断两次取数是否一致（数据修订、分页错位都能被它发现）
        "sha256": hashlib.sha256(resp.content).hexdigest(),
        "file": raw_path.name,
    }
    manifest_path = RAW_DIR / f"{stem}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return raw_path, manifest


def to_frame(rows):
    """把观测值摊平成一张干净的分析表。"""
    # json_normalize 把嵌套的 indicator{}/country{} 拆成 "indicator.id" 这样的点号列名
    df = pd.json_normalize(rows)

    # 先确认字段都在：接口改字段名时这里会立刻报错，而不是悄悄少几列
    keep = ["date", "value", "indicator.id", "indicator.value", "country.id", "country.value"]
    missing = [col for col in keep if col not in df.columns]
    if missing:
        raise KeyError(f"缺少字段 {missing}；接口实际返回 {list(df.columns)}")

    df = df[keep].rename(
        columns={
            "indicator.id": "indicator",
            "indicator.value": "indicator_name",
            "country.id": "country",
            "country.value": "country_name",
        }
    )

    # 缺失编码可能是 null、".."、""，统一转 NaN；不要 fillna(0)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], format="%Y")

    return df.sort_values(["country", "date"]).reset_index(drop=True)


def save_interim(df, stem="wb_gdp"):
    """把分析表写到 data/interim，返回 CSV 路径。"""
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = INTERIM_DIR / f"{stem}.csv"
    # utf-8-sig 带 BOM，Excel 双击打开中文不乱码；
    # 纯程序读取时用 encoding="utf-8" 也可以（BOM 会被自动跳过）。
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # 需要 Parquet（更省空间、保留类型）时，启用下面两行即可
    # parquet_path = INTERIM_DIR / f"{stem}.parquet"
    # df.to_parquet(parquet_path, index=False)

    return csv_path


def main():
    payload, resp = fetch()
    meta, rows = payload[0], payload[1]

    # 1) 原始层：原样保存 + 证据清单
    raw_path, manifest = save_raw(payload, resp)

    # 2) 摊平 + 类型转换
    df = to_frame(rows)

    # 3) 中间层：分析用的表
    csv_path = save_interim(df)

    missing_ratio = float(df["value"].isna().sum()) / len(df)
    print("raw:", raw_path)
    print("manifest:", manifest["fetched_at"], manifest["sha256"][:12] + "...")
    print("total:", meta.get("total"), "rows:", len(df), "pages:", meta.get("pages"))
    print(f"missing value: {missing_ratio:.1%}")
    print(df.head(3))
    print("csv:", csv_path)


if __name__ == "__main__":
    main()
