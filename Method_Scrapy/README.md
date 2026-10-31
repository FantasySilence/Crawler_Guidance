# Method_Scrapy：用 Scrapy 抓豆瓣 Top250

本目录对应《网络数据获取与爬虫入门指南（零基础教学版）》**第 5 章「Scrapy：豆瓣 Top250 的
规模化抓取」**。

豆瓣只有 10 页、250 条，用第 4 章的 requests + BS4 就够了；这一章的意义是把同一份数据用框架
重写一遍，看清"队列、去重、重试、并发、管道"分别解决了什么问题。**不要为了用框架而用框架。**

## 文件对照

| 路径 | 对应章节 | 讲什么 |
| --- | --- | --- |
| `douban_top250/scrapy.cfg` | 5.2（代码 5-2） | 项目入口：指定默认 settings |
| `douban_top250/douban_top250/items.py` | 5.5（代码 5-4） | `Top250Item`：只声明字段，不清洗 |
| `douban_top250/douban_top250/pipelines.py` | 5.5（代码 5-5） | 清洗（排名转 int、评分转 float）+ 校验（`DropItem`） |
| `douban_top250/douban_top250/settings.py` | 5.7（代码 5-8、表 5-3） | robots、5 秒间隔、1 并发、重试、UA、Pipeline、FEEDS |
| `douban_top250/douban_top250/middlewares.py` | 5.10（代码 5-11） | 最小代理中间件示例，**默认不启用** |
| `douban_top250/douban_top250/spiders/top250.py` | 5.3（代码 5-3） | 跟随 `.paginator .next a` 翻页，yield Item |
| `douban_top250/douban_top250/spiders/top250_pages.py` | 5.6（代码 5-7） | 用 `start_requests` 固定生成 10 个起始请求 |

## 环境

虚拟环境已在 `Method_Scrapy/.venv` 准备好（Python 3.12 + Scrapy 2.19.0，Twisted / lxml /
parsel 均已装好）。**没有装 scrapy-playwright**，因为豆瓣不需要浏览器（见文末附录）。

## 运行顺序

Scrapy 是框架，入口是命令行而不是脚本，所以序号放在下面：

```powershell
# 0. 进入项目目录（scrapy.cfg 在哪，crawl 就在哪执行）
cd douban_top250

# 1. 先确认项目能加载、两个 Spider 都在
..\.venv\Scripts\scrapy.exe list
#    top250
#    top250_pages

# 2. 主案例：跟随"后页"链接，抓完 10 页（settings 里的 FEEDS 会自动导出）
..\.venv\Scripts\scrapy.exe crawl top250 -L INFO

# 3. 对照案例：固定 10 个 start 请求，不依赖翻页链接
..\.venv\Scripts\scrapy.exe crawl top250_pages -L INFO

# 4. 不用 FEEDS、直接用命令行导出（-O 覆盖，-o 追加）
..\.venv\Scripts\scrapy.exe crawl top250 -O data/top250_cli.jsonl

# 5. 断点续爬：第一次中断后，再执行同一条命令会从断点继续
..\.venv\Scripts\scrapy.exe crawl top250 -s JOBDIR=state/top250
```

## 输出文件

```
Method_Scrapy/douban_top250/data/
├─ douban_top250.jsonl    # FEEDS 自动导出，一行一条
└─ douban_top250.csv      # utf-8-sig，Excel 可直接打开，列顺序固定
```

第 4 步的 `-O` 会在 FEEDS 之外**再写一份**；这是有意的：FEEDS 负责"每次固定产出"，
命令行 `-O/-o` 适合临时指定路径或格式。目录不存在时 Scrapy 会自动创建。

抓到的数据通常不提交进仓库，需要时在 `.gitignore` 加 `Method_Scrapy/douban_top250/data/`
和 `Method_Scrapy/douban_top250/state/`。

## 日志看什么（5.8）

运行时重点看四个统计量：

| 统计量 | 含义 | 异常时先查 |
| --- | --- | --- |
| `item_scraped_count` | 成功产出的条数 | 应为 250；是 0 就查选择器和回调名 |
| `response_received_count` | 收到的响应数 | 应为 11 左右（10 页 + robots.txt） |
| `retry/count` | 重试次数 | 持续增长说明网络或站点不稳定 |
| `httperror/403_count` | 403 次数 | 大于 0 就降速或停止，不要换代理硬绕 |

`callback=self.parse_detial` 这类拼写错误**不会报错**，只是那条请求不会有 item——先看日志里的
Crawled 数和 item 数。

## 断点续爬（5.9）

`JOBDIR` 保存请求队列和去重指纹，适合"抓一半断了"。长期增量更新更适合写数据库，用
`(snapshot_date, rank)` 或 `(snapshot_date, url)` 做唯一约束，再配合 `last_seen`、
`content_hash` 判断是否变化。

注意：Scrapy 默认按 URL 去重，"URL 没变、榜单变了"的页面会被跳过；需要重抓时给请求加
`dont_filter=True` 并自己判断内容是否真的变了。

## 附录：接 Scrapy + Playwright（5.11，代码 5-12~5-14）

豆瓣 Top250 是静态页面，**本项目不启用**浏览器下载器。只有在遇到真正依赖 JavaScript 的页面时
才按下面做（本虚拟环境未安装 `scrapy-playwright`）：

```powershell
pip install scrapy-playwright
playwright install chromium
```

在 `settings.py` 里启用（对应代码 5-13，已在 settings 中注释掉）：

```python
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
```

只对需要的请求开浏览器（对应代码 5-14）：

```python
from scrapy_playwright.page import PageMethod

yield scrapy.Request(
    "https://movie.douban.com/top250?start=0&filter=",
    meta={
        "playwright": True,
        "playwright_page_methods": [
            PageMethod("wait_for_selector", "ol.grid_view > li"),
        ],
    },
)
```

## 页面结构变化（2026-10 实测）

现行豆瓣 Top250 页面和教材示例有两处不同，`spiders/top250.py` 对短评做了兼容：

| 字段 | 教材写法 | 现行页面 |
| --- | --- | --- |
| 短评 | `.quote .inq::text` | `<p class="quote"><span>…</span></p>`，`span` 没有 `inq` 类 |

`quote = card.css(".quote .inq::text").get() or card.css(".quote span::text").get() or ""`
——先按教材取，落空再退回新结构，两种页面都能跑。

## 常见坑（5.12）

- `allowed_domains` 太严：详情页在别的域名时请求会被过滤掉；
- 回调名拼错：不报错，但没有 item，看日志的 Crawled 数；
- 200 但空结果：选择器只匹配到空容器，或页面被换成验证页；
- 相对 URL 没处理：用 `response.follow` 或 `urljoin`，不要手拼字符串；
- 并发太高：豆瓣会 403，先降到 1 并发、5 秒间隔；
- 重复抓取：翻页没有停止条件，或详情页 URL 带随机参数；
- Pipeline 抛异常：单条数据会丢，查日志里的 `DropItem` 和 traceback。

## 检查清单（表 5-4）

| 检查项 | 通过标准 | 本项目的落点 |
| --- | --- | --- |
| 结构 | Spider 只抓，清洗在 Pipeline | `spiders/top250.py` vs `pipelines.py` |
| 选择器 | 在保存的 HTML 上可复现，有默认值 | `get(default="")`，短评双选择器 |
| 翻页 | 10 页、start 0—225、不重复 | `response.follow` + dupefilter |
| 配置 | robots、5 秒、1 并发、重试、UA | `settings.py` |
| 断点 | JOBDIR 或数据库幂等 | 命令行 `-s JOBDIR=state/top250` |
| 导出 | JSONL/CSV 路径明确、字段完整 | `FEEDS` |
| 日志 | 能看出请求数、item 数、403/429 | `LOG_LEVEL=INFO` |
| 合规 | 没有绕过登录、付费墙、验证码 | 只抓公开榜单 |


