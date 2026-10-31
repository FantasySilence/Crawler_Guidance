# ================================================================ #
# @Author: Fantasy_Silence                                         #
# @Time: 2026-10-31                                                #
# @IDE: Visual Studio Code & PyCharm                               #
# @Python: 3.12.7                                                  #
# ================================================================ #
# @Description: 从环境变量读 key 调用 FRED 接口                      #
# ================================================================ #

"""
05_api_fred.py - 带 key 的 API：以 FRED 为例

对应《网络数据获取与爬虫入门指南》2.4 节：
  - 代码 2-4  在终端设置环境变量
  - 代码 2-5  用环境变量调用 FRED API

FRED（圣路易斯联储）的接口需要注册后发放的 api_key：
  https://api.stlouisfed.org/fred/series/observations
      ?series_id=GDPC1&api_key=...&file_type=json&observation_start=2000-01-01
GDPC1 = 美国实际 GDP（2017 年链式美元，季度、季调年率）。

key 是凭证，不是配置：只放环境变量，代码里只出现变量名。
  Windows PowerShell（当前窗口有效）:  $env:FRED_API_KEY = "你的 key"
  macOS / Linux:                       export FRED_API_KEY="你的 key"

运行：.venv/Scripts/python.exe 05_api_fred.py
"""

import os

import requests
import pandas as pd

BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
SERIES_ID = "GDPC1"  # 换序列只改这里，例如 CPIAUCSL（CPI）、UNRATE（失业率）
START = "2000-01-01"


def get_api_key():

    """
    从环境变量读 key；缺失时直接退出，而不是带着空 key 去请求。
    """

    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        # SystemExit 比 return None 更明确：调用方无法"忘记"检查
        raise SystemExit(
            "请先设置环境变量 FRED_API_KEY。\n"
            '  PowerShell:  $env:FRED_API_KEY = "你的 key"\n'
            '  macOS/Linux: export FRED_API_KEY="你的 key"'
        )
    return api_key


def fetch_observations(series_id=SERIES_ID, start=START):

    """
    请求一条序列的观测值，返回 (payload, observations)。
    """

    params = {
        "series_id": series_id,
        "api_key": get_api_key(),  # 只在请求时取值，不出来回传参
        "file_type": "json",  # 不写这个会默认返回 XML
        "observation_start": start,
        # 需要"当时能看到的数据"（vintage / 实时库 ALFRED）时加下面两个参数，
        # 并把日期写进数据附录；否则读者无法判断你是否用了事后修订的数据：
        # "realtime_start": "2008-01-01", "realtime_end": "2008-12-31",
    }

    resp = requests.get(BASE_URL, params=params, timeout=30)
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        # 参数或鉴权出错时 FRED 返回 400/401，正文里带 error_message。
        # 只看 "400 Client Error" 排不出问题，必须打印正文。
        raise SystemExit(f"请求失败：{exc}\n响应正文：{resp.text[:500]}") from exc

    payload = resp.json()
    obs = payload.get("observations")
    if not obs:
        # 序列代码写错、日期区间为空时，observations 可能是空列表或缺失
        raise ValueError(f"没有取到观测值，请检查 series_id / 日期区间：{payload}")
    return payload, obs


def observations_to_frame(obs):

    """
    观测值转 DataFrame，并把 FRED 的缺失标记 "." 转成 NaN。
    """
    
    df = pd.DataFrame(obs)[["date", "value"]]

    # FRED 用 "." 表示该期没有数据（不是 0）。requests 拿到的是字符串，
    # to_numeric(errors="coerce") 会把 "."、null、"" 统一变成 NaN。
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # 这里的 date 是 "2000-01-01" 这种完整日期，不用 format 也能解析
    df["date"] = pd.to_datetime(df["date"])

    return df.sort_values("date").reset_index(drop=True)


def main():
    payload, obs = fetch_observations()
    df = observations_to_frame(obs)

    print("series:", SERIES_ID)
    print("count:", payload.get("count"))  # 接口声明的观测条数
    print("rows:", len(df))
    print("missing value:", int(df["value"].isna().sum()))
    print("range:", df["date"].min().date(), "->", df["date"].max().date())

    # 头尾各看几行：头部能发现起点参数有没有生效，尾部能发现数据是否更新到最新一期
    print(df.head(5))
    print(df.tail(5))


if __name__ == "__main__":

    # 设置API_KEY
    os.environ["FRED_API_KEY"] = "YOUR_KEY"  # 替换为你的实际 key
    main()
