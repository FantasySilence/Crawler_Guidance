"""
middlewares.py - 下载中间件示例（指南 5.10，代码 5-11）

下载中间件可以改请求头、挂代理、处理异常。
这里只放一个最小的代理示例，**默认不启用**。

先问"我有没有权利"，再问"我能不能绕过"：
  - 被封禁、要求登录、出现验证码，都是站点在表达访问边界；
  - 这时应改用官方 API、申请授权或购买数据，而不是换 IP 继续抓。
代理只适合"有权访问、但网络位置受限"的场景（例如机构内网只放行特定出口）。

启用方式（在 settings.py 里加，数字 543 只是示例位置）：
    DOWNLOADER_MIDDLEWARES = {
        "douban_top250.middlewares.ProxyMiddleware": 543,
    }
"""


class ProxyMiddleware:
    """把每个请求的代理写进 request.meta（代码 5-11）。"""

    def process_request(self, request, spider):
        # 真实项目里从配置或环境变量读，不要硬编码在代码里
        request.meta["proxy"] = "http://127.0.0.1:7890"
