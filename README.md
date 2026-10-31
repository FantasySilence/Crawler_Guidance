# Crawler_Guidance

> 网络数据获取与爬虫入门 · 配套示例代码

《网络数据获取与爬虫入门指南（零基础教学版）》的配套示例代码。

主线案例是「豆瓣电影 Top 250」，用 requests + BeautifulSoup、Scrapy、Playwright 各写一遍；
另外加一个官方 API 案例（世界银行 / FRED），用来说明「有 API 优先用 API」。
每个目录都能单独运行，目录里的 `README.md` 写明了逐文件说明与排错方法。

- 教材原文：`guidance_pdf/网络数据获取与爬虫入门指南_零基础教学版.pdf`
- 许可：MIT（见 [LICENSE](LICENSE)）
- 环境：Python 3.12

## 学习路径

1. 先读指南第 1–3 章：数据在哪里、HTML 结构、CSS 选择器。不要一上来就写 Scrapy 或 Playwright。
2. 从 [`Method_API`](Method_API) 开始：最简单，不用解析网页，先把「请求 → 响应 → 字段」跑通。
3. 再到 [`Method_request+bs4`](Method_request+bs4)：走完「请求 → 解析 → 翻页 → 校验 → 保存」闭环。
4. 需要上千页、周期性运行时，看 [`Method_Scrapy`](Method_Scrapy)。
5. 只有数据必须靠浏览器渲染或点击时才用 [`Method_Playwright`](Method_Playwright)。

## 四种方案怎么选

先回答「数据在哪里」，再选工具。顺序就是推荐优先级：能用 API 就不用爬虫，能不用浏览器就不用浏览器。

| 你的情况 | 用什么 | 去哪个目录 |
| --- | --- | --- |
| 有官方 API、开放数据或批量下载 | 直接调接口，`requests` + `json` | [Method_API](Method_API) |
| 数据在第一次返回的 HTML 里，页面不多 | `requests` + BeautifulSoup | [Method_request+bs4](Method_request+bs4) |
| 几千页、要周期运行、要断点和并发 | Scrapy 框架 | [Method_Scrapy](Method_Scrapy) |
| 数据由 JavaScript 渲染，或要点击、滚动、登录 | 浏览器自动化 Playwright | [Method_Playwright](Method_Playwright) |

豆瓣 Top250 其实属于第二种：用 API 示例说明「有 API 优先用 API」，用 Scrapy / Playwright 示例说明
「框架和浏览器各自解决什么问题」，不代表豆瓣需要它们。

## 目录结构

```
Crawler_Guidance/
├─ guidance_pdf/                  # 教程 PDF（含本项目的出处）
├─ Method_API/                    # 第 2 章：官方 API（世界银行、FRED）
│  ├─ 01_api_url_anatomy.py … 05_api_fred.py
│  └─ README.md
├─ Method_request+bs4/            # 第 3–4 章：requests + BeautifulSoup
│  ├─ 01_selector_playground.py … 04_crawl_top250.py
│  ├─ fixtures/douban_top250_sample.html
│  └─ README.md
├─ Method_Scrapy/                 # 第 5 章：Scrapy 项目
│  ├─ douban_top250/               # scrapy.cfg + spiders/ + pipelines.py …
│  └─ README.md
├─ Method_Playwright/             # 第 6 章：Playwright
│  ├─ 01_launch_and_wait.py … 07_reuse_context.py
│  └─ README.md
└─ LICENSE
```

`Method_*` 前面没有数字，因为它们代表四种独立方案；每个目录内部的文件按「建议运行顺序」编号
（Scrapy 例外，项目文件名由框架约定固定，运行顺序写在它的 README 里）。

## 环境准备

每个目录都用**独立的虚拟环境**，互不影响。`.venv` 不会提交到仓库，克隆后需要自己创建（只需一次）：

```powershell
cd Method_API
py -3.12 -m venv .venv      # 没有 py 启动器就写 python -m venv .venv
```

之后用 `.venv\Scripts\python.exe`（Windows）直接运行即可，不必激活；激活也行：
`.venv\Scripts\Activate.ps1`（若 PowerShell 禁止执行脚本，就用解释器全路径，别去改执行策略）。

### 依赖安装

每个目录的 `requirements.txt` 就是该目录的依赖清单（从各目录当前环境导出，版本固定），直接装即可：

```powershell
# Method_API：官方 API
cd Method_API
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Method_request+bs4：静态页抓取
cd ..\Method_request+bs4
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Method_Scrapy：框架
cd ..\Method_Scrapy
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Method_Playwright：浏览器自动化
cd ..\Method_Playwright
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium
```

各目录实际用到的包：

| 目录 | 脚本直接 import | 清单里的其余内容 |
| --- | --- | --- |
| `Method_API` | `requests`、`pandas` | `numpy`/`python-dateutil`/`tzdata`（pandas 依赖）、`pyarrow`（可选，写 Parquet 用） |
| `Method_request+bs4` | `requests`、`beautifulsoup4`、`lxml` | `pandas`/`numpy`（脚本未使用，可删） |
| `Method_Scrapy` | `scrapy` | `Twisted`、`parsel`、`lxml`、`w3lib` 等框架依赖 |
| `Method_Playwright` | `playwright`、`requests`、`beautifulsoup4`、`lxml` | `greenlet`、`pyee` 等 playwright 依赖 |

说明：

- 清单是从各目录当前环境导出的，装完版本一致；`pandas` 会自动带上 `numpy`，
  `urllib3` 是 `requests` 的依赖，都不用单列。
- 想更精简：`Method_request+bs4` 清单里的 `pandas`/`numpy` 脚本并没有用到，可以删掉再装。
- `pyarrow` 已经装好；`04_api_json_to_table.py` 默认仍写 CSV，取消 `to_parquet` 那两行注释即可改存 Parquet。
- 浏览器只在 Playwright 目录需要，Chromium 约 150–300 MB，下载到 `%LOCALAPPDATA%\ms-playwright`。

## 快速开始

每条路径先跑「不联网 / 最轻」的那一步，确认环境通了再往下。

```powershell
# ① 先把 API 讲清楚：拆一条 URL，不发请求
cd Method_API
.venv\Scripts\python.exe 01_api_url_anatomy.py
.venv\Scripts\python.exe 02_api_worldbank.py     # 真请求世界银行（无需 key）

# ② 离线练选择器，再抓页面
cd ..\Method_request+bs4
.venv\Scripts\python.exe 01_selector_playground.py   # 纯本地
.venv\Scripts\python.exe 02_fetch_page.py            # 抓一页并保存原始 HTML
.venv\Scripts\python.exe 03_parse_cards.py           # 离线解析上一步的 HTML
.venv\Scripts\python.exe 04_crawl_top250.py --pages 1

# ③ Scrapy：命令必须在有 scrapy.cfg 的目录里执行
cd ..\Method_Scrapy\douban_top250
..\.venv\Scripts\scrapy.exe list
..\.venv\Scripts\scrapy.exe crawl top250 -L INFO

# ④ Playwright：先确认浏览器能起来
cd ..\..\Method_Playwright
.venv\Scripts\python.exe 01_launch_and_wait.py
```

## 四个示例目录详解

### Method_API —— 官方 API（第 2 章）

- **学什么**：endpoint / 查询参数 / 状态码 / JSON；无 key 的世界银行接口、带 key 的 FRED 接口；
  分页、429 退避、有限重试；原始 JSON 落盘与 `manifest`（URL、时间、sha256）。
- **怎么跑**：`01` 纯本地拆 URL → `02` 世界银行 → `03` 分页与重试 → `04` 摊平成表 → `05` FRED（需
  `$env:FRED_API_KEY`，免费申请）。
- **产出**：`Method_API/data/raw/wb_gdp.json`、`wb_gdp.manifest.json`、`data/interim/wb_gdp.csv`
  （环境里已装 `pyarrow`，取消 `04` 里 `to_parquet` 两行注释即可改存 Parquet）。
- **重点**：key 只放环境变量；缺失值转 `NaN` 而不是补 0；分页按 `meta["pages"]` 判断末页。

### Method_request+bs4 —— requests + BeautifulSoup（第 3–4 章）

- **学什么**：DOM 与 CSS 选择器；`Session` + UA + 超时 + 重试；编码修正；抽取排名、片名、评分、
  短评、链接；`start` 参数翻页；JSONL 断点与 CSV 导出。
- **怎么跑**：`01` 离线选择器练习（用 `fixtures/` 里的示例 HTML）→ `02` 抓第一页 → `03` 离线解析 →
  `04` 抓 10 页（先 `--pages 1`）。
- **产出**：`data/raw/top250_start*.html`、`data/raw/douban_top250.jsonl`、
  `data/processed/douban_top250.csv`、`data/raw/douban_done.json`（断点）。
- **重点**：先保存 HTML 再调选择器；`utf-8-sig` 写 CSV；每页落盘，中断可续。

### Method_Scrapy —— Scrapy（第 5 章）

- **学什么**：项目结构；Spider 的 `parse` 与 `response.follow`；Item；Pipeline 清洗与 `DropItem`；
  `settings` 里的限速、重试、`FEEDS`；JOBDIR 断点续爬；`scrapy-playwright` 的接入方式（注释中）。
- **怎么跑**：

  ```powershell
  cd "Method_Scrapy\douban_top250"
  ..\.venv\Scripts\scrapy.exe crawl top250 -L INFO        # 跟随“后页”链接
  ..\.venv\Scripts\scrapy.exe crawl top250_pages -L INFO  # 固定 10 个 start 请求
  ```

- **产出**：`data/douban_top250.jsonl`、`data/douban_top250.csv`（`FEEDS` 自动导出）。
- **重点**：Spider 只负责抓、Pipeline 负责洗；看日志的 `item_scraped_count` 是否为 250。

### Method_Playwright —— Playwright（第 6 章）

- **学什么**：启动 Chromium；`locator` 与等待；点击翻页；`inner_text` / `get_attribute`；截图排错；
  浏览器与页面复用；静态页与 JS 渲染页的对照。
- **怎么跑**：`01` 打开并等待 → `02` locator → `03` 点击后页 → `04` 抽字段 → `05` 抓两页存 CSV →
  `06` 动态页对照 → `07` 复用浏览器。
- **产出**：`data/raw/douban_top250_page1.png`、`data/processed/douban_top250_playwright.csv`。
- **重点**：等元素/URL，不用固定 `sleep`；失败先截图；豆瓣是静态页，requests 更合适。

## 数据与产物约定

沿用指南第 4 章的分层，各目录在运行时自动创建：

```
data/
├─ raw/          # 原始响应（HTML / JSON / JSONL）与截图，不覆盖
├─ interim/      # 清洗中间结果（CSV）
└─ processed/    # 分析用数据（CSV）
```

这些产物通常不提交进仓库，可以在 `.gitignore` 里加：

```
Method_API/data/
Method_request+bs4/data/
Method_Scrapy/douban_top250/data/
Method_Scrapy/douban_top250/state/
Method_Playwright/data/
```

## 抓取边界与合规

- 优先官方 API、批量下载、机构订阅；爬虫只用于没有其他入口的公开数据。
- 遵守 `robots.txt`，串行 + 5 秒间隔（豆瓣 `Crawl-delay` 虽被注释，本项目仍按 5 秒）。
- 遇到 403、429、验证码或登录墙：**停下来**，降速或换授权渠道，不要换代理、换账号硬绕。
- 浏览器 UA 只用于让公开页面正常返回，不是伪装身份或绕过风控。
- 豆瓣 Top250 是公开榜单，仅用于教学练习，不是经济学数据源。

## 页面结构变化（2026-10 实测）

现行豆瓣 Top250 与教材示例有两处不同，三个抓取目录的代码都已兼容：

| 字段 | 教材写法 | 现行页面 |
| --- | --- | --- |
| 短评 | `.quote .inq`（`span` 带 `inq` 类） | `<p class="quote"><span>…</span></p>`，`span` 没有 `inq` 类 |
| 评价人数 | `.star span:last-child` | 评分容器不再带 `class="star"` |

代码里统一写成「先按教材选择器取，落空再退回新结构」，所以两种页面都能跑。

## 常见问题

| 现象 | 原因与处理 |
| --- | --- |
| `.venv\Scripts\python.exe` 提示找不到路径 | 该目录还没建虚拟环境：`py -3.12 -m venv .venv` |
| `ModuleNotFoundError: No module named 'lxml'` | 该目录没装 lxml：`pip install lxml`（Playwright 的 `06`、bs4 目录都要用到） |
| 控制台中文乱码 | 先 `chcp 65001`，或设 `$env:PYTHONIOENCODING = "utf-8"` |
| Playwright 报找不到浏览器 | `.venv\Scripts\python.exe -m playwright install chromium` |
| `scrapy` 提示找不到项目 | 必须 `cd` 到有 `scrapy.cfg` 的 `Method_Scrapy\douban_top250` |
| `scrapy` 报 `UnicodeDecodeError` 读 `scrapy.cfg` | 这个文件要保持纯 ASCII（Scrapy 用系统编码读它） |
| FRED 直接退出并提示设置环境变量 | `$env:FRED_API_KEY = "你的 key"`，这是代码的刻意设计 |
| 想改存 Parquet | 环境已装 `pyarrow`，取消 `04_api_json_to_table.py` 里 `to_parquet` 两行注释即可 |
| 豆瓣返回 403 / 验证页 | 停止采集，降低频率；不要换代理硬绕 |
| Excel 打开 CSV 乱码 | 用 `utf-8-sig` 写文件（项目里的导出已是） |

## 与教程章节的对照

| 指南 | 内容 | 本项目 |
| --- | --- | --- |
| 第 1 章 | 数据获取概览、选型 | 本 README 的「四种方案怎么选」 |
| 第 2 章 | 官方 API | `Method_API/` |
| 第 3 章 | HTML 与 CSS 选择器 | `Method_request+bs4/fixtures/` + `01_selector_playground.py` |
| 第 4 章 | requests + BeautifulSoup | `Method_request+bs4/` |
| 第 5 章 | Scrapy | `Method_Scrapy/` |
| 第 6 章 | Playwright | `Method_Playwright/` |
| 第 7 章起 | 工程化、合规、排错 | 未单独建目录；相关做法散在各目录 README（分层、断点、检查清单） |

