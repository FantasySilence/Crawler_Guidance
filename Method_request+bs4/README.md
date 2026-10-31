# Method_request+bs4：requests + BeautifulSoup 抓豆瓣 Top250

本目录对应《网络数据获取与爬虫入门指南（零基础教学版）》**第 3 章（HTML 网页结构）**与
**第 4 章（requests + BeautifulSoup：豆瓣 Top250）**。
它是全书最轻的一层：一个请求、一棵树、十页榜单，适合单站、少量页面、一次性任务。

## 文件对照

| 文件 | 对应章节 | 讲什么 |
| --- | --- | --- |
| `fixtures/douban_top250_sample.html` | 3.2（代码 3-1） | 教学用简化榜单页：3 个条目 + 分页容器，第 3 条故意没有短评 |
| `01_selector_playground.py` | 3.3–3.6、3.10（表 3-2/3-3/3-4/3-6） | **不联网**，在示例 HTML 上练 CSS 选择器，打印每个字段的命中数与取值 |
| `02_fetch_page.py` | 4.2、4.3、3.9（代码 4-3~4-7、3-6） | Session + UA + 有限重试 + robots 检查；状态码/编码诊断；原样保存第一页 HTML |
| `03_parse_cards.py` | 4.4–4.6、3.9（代码 4-9~4-12、3-7） | `select` / `select_one` 抽字段，缺失短评的判断，`parse_number` 清洗，收集详情页链接 |
| `04_crawl_top250.py` | 4.7–4.9（代码 4-13~4-17） | 翻页 → JSONL 追加 → done 断点 → 从 JSONL 重放 → 校验 → 写 CSV |

## 环境

虚拟环境已在 `Method_request+bs4/.venv` 准备好（Python 3.12 + requests / beautifulsoup4 / lxml / pandas），无需重新安装。

```powershell
# 在 Method_request+bs4 目录下
.venv\Scripts\python.exe 01_selector_playground.py
```

## 建议的运行顺序

```powershell
# 1. 离线认识选择器，不需要网络
.venv\Scripts\python.exe 01_selector_playground.py

# 2. 取回第一页 HTML，看状态码、编码、字节数，并保存到 data/raw
.venv\Scripts\python.exe 02_fetch_page.py

# 3. 离线解析保存下来的 HTML（字段逐个和浏览器 Elements 面板核对）
.venv\Scripts\python.exe 03_parse_cards.py

# 4. 先跑一页，确认字段和校验都通过
.venv\Scripts\python.exe 04_crawl_top250.py --pages 1

# 5. 再跑全部 10 页（约 50 秒，5 秒间隔）
.venv\Scripts\python.exe 04_crawl_top250.py
```

`04_crawl_top250.py` 支持断点续跑：每页写完立即更新 `data/raw/douban_done.json`，
中断后重新运行会跳过已完成的页。

## 输出文件

沿用指南建议的分层（`data/raw` 放原始响应，`data/processed` 放分析用数据）：

```
Method_request+bs4/data/
├─ raw/
│  ├─ top250_start0.html        # 原始 HTML，按页存档，不覆盖
│  ├─ douban_top250.jsonl       # 逐页追加，一行一条（保留全部字段）
│  └─ douban_done.json          # 已完成的 start 列表，断点续跑用
└─ processed/
   └─ douban_top250.csv         # 由 JSONL 重放 + 去重 + 校验后生成，utf-8-sig
```

CSV 字段比指南的 5 列多了两列：`title_original`（原名，来自第二个 `span.title`；没有第二个
`span.title` 的条目留空）和 `votes`（评价人数）。不想要就直接从 `FIELDS` 里删掉。

## 页面结构变化（2026-10 实测）

现行豆瓣 Top250 页面和教材示例有两处不同，`03_parse_cards.py` 与 `04_crawl_top250.py`
都已做兼容：先按教材选择器取，落空再退回新结构。

| 字段 | 教材 / 示例 HTML | 现行页面 |
| --- | --- | --- |
| 短评 | `<span class="inq">`，选择器 `.quote .inq` | `<p class="quote"><span>…</span></p>`，内层 span 没有 `inq` 类 |
| 评价人数 | `.star span:last-child` | 评分容器不再带 `class="star"`，退回「文本含`人评价`」的 span |

`fixtures/douban_top250_sample.html` 仍是教材版结构，用于离线练选择器；
`02_fetch_page.py` 抓下来的真实页面会走兼容分支。

## 抓取边界

- **限速**：串行请求，间隔 5 秒；豆瓣 robots.txt 里的 `Crawl-delay: 5` 虽被注释，本书仍照此执行。
- **UA 的用途**：`02_fetch_page.py` 里的浏览器 UA 只是让公开页面正常返回，不是伪装身份、绕过登录或风控。
- **遇到 403 / 429 / 验证码**：停止采集并降速，记录后结束；不要换代理、换账号硬绕。
- **适用范围**：Top250 是公开榜单，用于教学练习。它是电影数据，不是经济学数据源；
  正式研究应优先用官方 API（见 `../Method_API`）、年鉴、机构订阅或商业数据库。
- **robots.txt** 只是最低门槛，真正的授权要看服务条款和许可。

## 常见错误速查（表 4-3）

| 现象 | 可能原因 | 处理 |
| --- | --- | --- |
| 403 Forbidden | 访问过快 / UA 被拒 | 停止并降速，不要换代理硬绕 |
| 429 Too Many Requests | 请求太快 | 读 `Retry-After`，退避后再试 |
| Timeout | 网络慢或站点限流 | 增大 `timeout`、减少单页体积 |
| 中文乱码 | 编码判断错误 | 显式 `resp.encoding = "utf-8"` |
| `NoneType` 报错 | 短评/评分节点不存在 | 保存 HTML，回浏览器验证选择器 |
| 结果为空列表 | 选择器过窄 / 页面改版 | 确认 `ol.grid_view` 是否存在 |
| 重复行 | 翻页循环重复 | 用 `rank` 或 `url` 去重 |
| Excel 打开乱码 | CSV 没有 BOM | 用 `utf-8-sig` 写文件 |
| 评分是字符串 | 没有转 float | `float()` 或 `pd.to_numeric` |

## 排查顺序

固定成这几步，比到处猜要快：

1. 浏览器打开同一个 URL，确认页面本身能看；
2. 用 requests 打印状态码和 `text[:500]`；
3. 把 HTML 保存到本地，用同一个选择器在本地文件上测（`03_parse_cards.py` 就是这么做的）；
4. 最后才怀疑翻页、编码、限速这些环节。
