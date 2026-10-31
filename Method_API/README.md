# Method_API：官方 API 取数示例

本目录对应《网络数据获取与爬虫入门指南（零基础教学版）》**第 2 章「官方 API：最优先的方案」**。
所有示例都用纯 HTTP 调接口拿 JSON，不需要浏览器，也不涉及网页解析——这正是「有 API 就优先用 API」的意思。

## 文件对照

| 文件 | 对应章节 | 讲什么 |
| --- | --- | --- |
| `01_api_url_anatomy.py` | 2.1 / 2.2（表 2-1、表 2-2、代码 2-1） | 拆一条 API URL：协议+主机、路径、查询参数、状态码，不联网 |
| `02_api_worldbank.py` | 2.3（代码 2-2、2-3） | 世界银行接口，无需 key：请求 → 校验结构 → 转 DataFrame → 处理缺失 |
| `03_api_paging.py` | 2.5（代码 2-6、2-7） | 分页循环、429 退避、给 Session 挂有限重试 |
| `04_api_json_to_table.py` | 2.6（代码 2-8）、2.9（表 2-4） | 原始 JSON + manifest 留存、json_normalize 摊平、落 CSV |
| `05_api_fred.py` | 2.4（代码 2-4、2-5） | 带 key 的接口：从环境变量读 key，错误正文怎么读 |

## 环境

虚拟环境已在 `Method_API/.venv` 准备好（Python 3.12 + requests / pandas / numpy 等，见 `requirements.txt`），无需重新安装。

```powershell
# 在 Method_API 目录下激活（PowerShell）
.venv\Scripts\Activate.ps1

# 或者直接用解释器路径，不必激活
.venv\Scripts\python.exe 02_api_worldbank.py
```

## 运行

文件名前的 `01`–`05` 就是建议运行顺序：先不联网的、再不需要 key 的，最后才是需要配 key 的。

```powershell
.venv\Scripts\python.exe 01_api_url_anatomy.py    # 纯本地，不发请求
.venv\Scripts\python.exe 02_api_worldbank.py      # 世界银行，可直接跑
.venv\Scripts\python.exe 03_api_paging.py         # 世界银行分页 + 重试演示
.venv\Scripts\python.exe 04_api_json_to_table.py  # 会写 data/raw 与 data/interim
.venv\Scripts\python.exe 05_api_fred.py           # 需要先设置 FRED_API_KEY
```

FRED 需要一个免费 key（<https://fredaccount.stlouisfed.org/apikeys>），只放环境变量：

```powershell
$env:FRED_API_KEY = "你的 key"      # 当前窗口有效
```

没有设置时 `05_api_fred.py` 会打印提示并退出，这是有意设计的。

如果控制台中文显示乱码，先执行 `chcp 65001`，或设置 `$env:PYTHONIOENCODING = "utf-8"`。

## 输出文件

`04_api_json_to_table.py` 沿用指南第 4 章建议的分层：

```
Method_API/data/
├─ raw/wb_gdp.json             # 原始响应，不覆盖、不加工
├─ raw/wb_gdp.manifest.json    # URL、状态码、抓取时间、字节数、sha256
└─ interim/wb_gdp.csv          # 摊平后的分析表（utf-8-sig，Excel 可直接打开）
```

取到的数据通常不提交进仓库；如需忽略，在 `.gitignore` 末尾加一行：

```
Method_API/data/
```

指南 2.6 的示例用 `to_parquet` 存中间结果，但当前虚拟环境没有 `pyarrow`，因此脚本默认写 CSV。
需要 Parquet 时执行 `pip install pyarrow`，再取消 `04_api_json_to_table.py` 里那两行注释。

## 与表 2-4「API 取数检查清单」的对应

| 检查项 | 示例里的落点 |
| --- | --- |
| 文档 | 每个脚本头部都写了 endpoint、参数含义和响应结构 |
| 认证 | `05_api_fred.py` 用 `os.environ` 读 key，代码库中无明文凭证 |
| 分页 | `03_api_paging.py` 用 `meta["pages"]` 判断末页，不会漏页也不会多打请求 |
| 限流 | `MAX_429_RETRIES` 上限 + `Retry-After` 退避 + 翻页间隔 |
| 原始数据 | `04_api_json_to_table.py` 保存 JSON 与 manifest（URL、时间、sha256） |
| 字段 | `to_frame` 先校验字段再摊平，缺失统一转 NaN 并打印缺失比例 |
| 版本 | 注释中说明了 FRED 的 `realtime_start/end`（vintage）用法 |
| 引用 | manifest 里的 URL 与 `fetched_at` 可直接写进数据附录 |

