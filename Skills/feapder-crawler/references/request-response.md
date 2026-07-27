# Request 和 Response

## Request

`feapder.Request` 封装了 `requests` 参数，并额外增加 feapder 框架参数。

常见框架参数：

- `url`：目标 URL。
- `callback`：parser 回调函数或函数名。
- `parser_name`：跨 parser 回调时使用的 parser 类名。
- `priority`：优先级，数值越小越优先，默认通常是 `300`。
- `filter_repeat`：当 `REQUEST_FILTER_ENABLE` 开启时，控制当前请求是否去重。
- `auto_request`：设为 `False` 时，parse 收到的 `response=None`，需要自己下载。
- `request_sync`：让 yield 出去的请求立即同步处理，而不是进入异步队列。
- `use_session`：使用 session downloader。
- `random_user_agent`：配合随机 headers 配置使用。
- `download_midware`：当前请求专用下载中间件。
- `is_abandoned`：异常时是否放弃重试。
- `render`：是否使用浏览器渲染。
- `render_time`：渲染后等待多久再取 HTML。
- 其他 `**kwargs`：可通过 `request.<name>` 读取。

带 callback 和参数透传的示例：

```python
def start_requests(self):
    yield feapder.Request(
        "https://example.com/list",
        callback=self.parse_list,
        category="books",
    )


def parse_list(self, request, response):
    category = request.category
    for href in response.css("a.detail::attr(href)").extract():
        yield feapder.Request(href, callback=self.parse_detail, category=category)
```

多来源或多步骤解析时，不要把所有页面都扔进默认 `parse()` 再用 URL 判断分发到 `_parse_xxx` 私有方法。优先让每条链路在 `Request` 上显式绑定 callback。

如果同一批种子能直接构造多个并列来源 URL，要在 `start_requests()` 中并列下发。不要先请求来源 A，再在 `parse_a()` 里创建来源 B 的请求；只有从当前 response 解析出来的派生 URL，才在对应 callback 内继续 yield。

```python
YYB_URL = "https://sj.qq.com/appdetail/{}"
WDJ_URL = "https://www.wandoujia.com/apps/{}"
MI_URL = "https://app.mi.com/details?id={}"


def start_requests(self):
    for pkg in self.seed_packages:
        yield feapder.Request(YYB_URL.format(pkg), callback=self.parse_yyb, pkg=pkg)
        yield feapder.Request(WDJ_URL.format(pkg), callback=self.parse_wandoujia, pkg=pkg)
        yield feapder.Request(MI_URL.format(pkg), callback=self.parse_mi, pkg=pkg)


def parse_yyb(self, request, response):
    pkg = request.pkg
    for related_pkg in self.extract_yyb_related(response):
        # 这是从应用宝响应里解析出的派生链路，所以留在 parse_yyb 中递归。
        yield feapder.Request(
            YYB_URL.format(related_pkg),
            callback=self.parse_yyb,
            pkg=related_pkg,
        )


def parse_wandoujia(self, request, response):
    pass


def parse_mi(self, request, response):
    pass
```

反例：

```python
def parse(self, request, response):
    if "sj.qq.com" in response.url:
        yield from self._parse_yyb(request, response)
    elif "wandoujia.com" in response.url:
        yield from self._parse_wandoujia(request, response)
```

这个反例能跑，但会隐藏 feapder 的 callback 链路，不利于调试 `request.callback_name`、失败重试、跨 parser 回调和后续维护。只有很小的单页爬虫才适合只写默认 `parse()`。

另一个反例是把并列来源串成伪流程：

```python
def parse_yyb(self, request, response):
    # 错：豌豆荚 URL 能由同一个 pkg 直接构造，不应该藏在应用宝 callback 里。
    yield feapder.Request(WDJ_URL.format(request.pkg), callback=self.parse_wandoujia)
```

如果豌豆荚和应用宝都是同一批 pkg 的独立补充来源，应在 `start_requests()` 中并列创建；`parse_yyb()` 只处理应用宝响应和应用宝响应派生出的推荐链。

## Parser 钩子

`BaseParser` 和各类 spider 都支持这些常见钩子：

```python
def start_requests(self):
    pass

def download_midware(self, request):
    return request

def validate(self, request, response):
    pass

def parse(self, request, response):
    pass

def exception_request(self, request, response, e):
    pass

def failed_request(self, request, response, e):
    pass

def start_callback(self):
    pass

def end_callback(self):
    pass
```

`validate` 语义：

- 抛异常：触发重试。
- 返回 `False`：丢弃当前请求。
- 返回 `True` 或 `None`：继续进入 parser callback。

## Response

`feapder.Response` 封装了 `requests.Response`。

常用提取方式：

```python
response.xpath("//title/text()").extract_first()
response.xpath("//a/@href").extract()
response.css("a::attr(href)").extract()
response.re(r"<title>(.*?)</title>")
response.re_first(r"id=(\d+)", default=None)
response.bs4().title
response.json
response.text
response.extract()
response.open()
```

和 `requests.Response` 的重要差异：

- JSON 用 `response.json`，不是 `response.json()`。
- 编码可用 `response.encoding`，也支持简写 `response.code`。
- HTML 相对链接会按配置自动转为绝对链接。

常用构造方式：

```python
response = feapder.Response(raw_requests_response)
response = feapder.Response.from_text(text=html, url="https://example.com")
response = feapder.Response.from_dict(response_dict)
```
