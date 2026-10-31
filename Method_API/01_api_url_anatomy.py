"""
01_api_url_anatomy.py - 解剖一个 API 请求（对应指南 2.1、2.2）

对应《网络数据获取与爬虫入门指南》：
  - 表 2-1  API 的六个基本概念（endpoint / method / query / header / status / response）
  - 代码 2-1  一个带查询参数的 API URL
  - 表 2-2  URL 的六个部分

这个脚本不发任何网络请求，只做两件事：
  1. 用 urllib.parse 把一条 API URL 拆成"协议+主机 / 路径 / 查询参数"；
  2. 逐条解释每个查询参数和常见状态码的含义。

把这一步看懂，后面调任何 REST 接口都只是在拼这条 URL。
运行：.venv/Scripts/python.exe 01_api_url_anatomy.py
"""

from urllib.parse import parse_qsl, urlsplit

# 代码 2-1 里的那条 FRED URL。key 用占位符：
# 真实 key 只放环境变量（见 05_api_fred.py），不要写进代码、更不要提交到仓库。
API_URL = (
    "https://api.stlouisfed.org/fred/series/observations"
    "?series_id=GDPC1"
    "&api_key=YOUR_KEY"
    "&file_type=json"
    "&observation_start=2000-01-01"
)

# 表 2-2 的六个部分里，"查询参数"最需要逐个理解：它们决定"取哪一条数据"。
PARAM_NOTES = {
    "series_id": "取哪一条序列（GDPC1 = 美国实际 GDP，季度、链式美元）",
    "api_key": "证明你有权限的凭证（真实值只放环境变量）",
    "file_type": "要求返回 JSON（不是 XML）",
    "observation_start": "限制观测区间的起点",
}

# HTTP 状态码是排查问题的第一线索：先看码，再看正文。
STATUS_NOTES = {
    200: "成功",
    400: "参数写错（拼写、日期格式、必填参数缺失）",
    401: "缺少或无效的 key",
    403: "key 合法但无权访问该资源",
    404: "路径或资源不存在（先核对 endpoint）",
    429: "请求太快：读 Retry-After，退避后再试，不要立刻换 IP",
    500: "服务器端问题：可以有限重试 5xx，但要设上限",
}


def main():
    # urlsplit 只做字符串切分，不联网：scheme=协议，netloc=主机，path=路径，query=参数串
    parts = urlsplit(API_URL)

    print("协议+主机:", f"{parts.scheme}://{parts.netloc}")  # 去哪里取
    print("路径:", parts.path)  # 取哪类资源
    print("查询串:", parts.query)  # 取哪一条、要什么格式
    print()

    # parse_qsl 把 "a=1&b=2" 变成 [("a", "1"), ("b", "2")]，顺序保留、自动解码
    print("拆开的查询参数:")
    for key, value in parse_qsl(parts.query):
        note = PARAM_NOTES.get(key, "(文档里查不到的参数：不要猜，去读文档)")
        print(f"  {key:<18}= {value:<12}  # {note}")
    print()

    print("状态码速查:")
    for code, note in STATUS_NOTES.items():
        print(f"  {code}: {note}")
    print()

    # 关键结论：endpoint 固定，换参数就能换数据；整个过程不需要打开浏览器。
    print("同一个 endpoint 只改参数，就能取不同序列、不同区间。")


if __name__ == "__main__":
    main()
