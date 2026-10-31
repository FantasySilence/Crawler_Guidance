# Method_Playwright：用浏览器打开豆瓣 Top250

本目录对应《网络数据获取与爬虫入门指南（零基础教学版）》**第 6 章「Playwright：用浏览器打开
豆瓣 Top250」**。

先说结论：**豆瓣 Top250 是静态页面，requests 更快、更省资源**。本章用 Playwright 是为了练习
"打开页面 → 等待元素 → 点击翻页 → 抽取卡片 → 截图排错"这套浏览器自动化流程，不是因为
豆瓣需要浏览器。真正需要浏览器的是 6.11 那个由 JavaScript 渲染的对照沙盒。

## 文件对照

| 文件 | 对应章节 | 讲什么 |
| --- | --- | --- |
| `01_launch_and_wait.py` | 6.2、6.3、6.7（代码 6-2、6-6） | 启动 Chromium、`goto` + `wait_for_selector`、`expect` 断言、整页截图 |
| `02_locator_basics.py` | 6.4（代码 6-3、表 6-2） | `count` / `first` / `nth` / `last`、`inner_text` 与 `get_attribute`、`get_by_text` |
| `03_click_next_page.py` | 6.5（代码 6-4） | 点击 `.paginator .next a`，用**正则**等 URL 变化，读第二页排名 26 |
| `04_parse_page.py` | 6.6（代码 6-5） | `parse_page()`：排名、片名、评分、短评、链接五个字段，处理缺失短评 |
| `05_crawl_two_pages.py` | 6.10（代码 6-9） | 完整案例：抓两页 50 条，校验排名连续，写 CSV |
| `06_dynamic_vs_static.py` | 6.11（代码 6-10、表 6-3） | 同一 URL：requests 拿到 0 条，Playwright 等到 10 条 |
| `07_reuse_context.py` | 6.8（代码 6-7） | 一个浏览器 + 一个 context + 两个 page，`finally` 里关闭资源 |

## 环境

虚拟环境已在 `Method_Playwright/.venv` 准备好（Python 3.12 + playwright 1.64.1 + requests /
beautifulsoup4 / lxml 6.1.3），Chromium 也已装好，无需重新安装。换机器时才需要：

```powershell
pip install playwright beautifulsoup4 lxml
playwright install chromium          # Linux 服务器加 --with-deps
```

运行（在本目录下，按文件序号顺序）：

```powershell
.venv\Scripts\python.exe 01_launch_and_wait.py
.venv\Scripts\python.exe 02_locator_basics.py
.venv\Scripts\python.exe 03_click_next_page.py
.venv\Scripts\python.exe 04_parse_page.py
.venv\Scripts\python.exe 05_crawl_two_pages.py
.venv\Scripts\python.exe 06_dynamic_vs_static.py
.venv\Scripts\python.exe 07_reuse_context.py
```

## 输出文件

```
Method_Playwright/data/
├─ raw/
│  └─ douban_top250_page1.png              # 第一页整页截图，排错时先看它
└─ processed/
   └─ douban_top250_playwright.csv         # 前两页 50 条，utf-8-sig
```

## 调试技巧

- `headless=False` 打开可见浏览器，`slow_mo=300` 放慢每一步；
- `PWDEBUG=1` 加 `page.pause()` 可以单步执行；
- 失败时**先截图**再怀疑选择器：`page.screenshot(path=..., full_page=True)`；
- 等待用「具体元素或 URL」，不要用固定 `time.sleep`；
- 不要默认 `wait_until="networkidle"`：有轮询、长连接或广告的页面可能永远不空闲。

## 页面结构变化（2026-10 实测）

现行豆瓣 Top250 页面和教材示例有两处不同，`02_locator_basics.py` 会把差异打印出来，
`04_parse_page.py` / `05_crawl_two_pages.py` 已做兼容（先按教材选择器取，落空再退回新结构）。

| 字段 | 教材 / 示例 | 现行页面 |
| --- | --- | --- |
| 短评 | `.quote .inq`（`span` 带 `inq` 类） | `<p class="quote"><span>…</span></p>`，内层 `span` 没有 `inq` 类 |
| 评分容器 | `.star` | 容器不再带 `star` 类（本章只取 `.rating_num`，不受影响） |

## 何时该用 Playwright（表 6-1 的浓缩版）

| 场景 | 用 Playwright？ | 更合适的做法 |
| --- | --- | --- |
| 数据在第一次 HTML 里（豆瓣 Top250） | 不需要 | requests + BeautifulSoup |
| 数据由 XHR 返回 JSON | 通常不需要 | 直接用 requests 请求那个接口 |
| 需要点击、滚动、登录 | 需要 | — |
| 需要下载附件 | 需要 | 先找直接下载链接 |
| 大规模多页 | 谨慎 | Scrapy + 少量 Playwright 请求 |

## 检查清单（表 6-5）

| 检查项 | 通过标准 | 本目录的落点 |
| --- | --- | --- |
| 必要性 | 已确认没有可复现的 JSON 接口 | `06_dynamic_vs_static.py` 用 requests 对照 |
| 等待 | 等具体元素/URL，不用固定 sleep | 所有脚本用 `wait_for_selector` / `wait_for_url` |
| 并发 | 浏览器复用，页面数受限，超时明确 | `07_reuse_context.py`，`set_default_timeout(30s)` |
| 调试 | 失败时有截图，不靠猜 | `01_launch_and_wait.py` 保存整页截图 |
| 合规 | 没有绕过登录、付费墙、验证码 | 只访问公开榜单；遇到拦截就停止 |

## 常见问题（表 6-4）

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 一直等到超时 | 选择器错 / 页面没加载 / 验证页 | 截图；先等 `body`；检查 URL |
| 元素找到了但点不动 | 被遮挡、不可见、未启用 | 滚动到可见；等按钮 `enabled` |
| 翻页后还是第一页 | 点击未生效 / 等待不足 | 等 URL 或 `.pic em` 变化 |
| 服务器上失败、本地成功 | 字体 / 无头 / 网络 / 反爬 | 看截图；不要伪造指纹 |
| 内存越来越大 | page / context 未关闭 | 限制并发；定期重启浏览器 |
