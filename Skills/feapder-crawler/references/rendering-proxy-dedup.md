# 渲染、代理和去重

## 浏览器渲染

动态页面只有在直接找接口不划算或不可行时，再使用浏览器渲染。
在 feapder 任务里，浏览器渲染的主路径是 `feapder.Request(..., render=True)` 加 `RENDER_DOWNLOADER` 配置。AI 不允许直接改写成独立 Playwright/Selenium 脚本；如果判断确实需要脱离 feapder 渲染路径，必须先向用户说明原因、影响和替代方案，并明确请求用户授权。

```python
yield feapder.Request("https://example.com", render=True, render_time=2)
```

默认渲染 downloader 通常是 Selenium，除非配置改成 Playwright：

```python
RENDER_DOWNLOADER = "feapder.network.downloader.SeleniumDownloader"
# RENDER_DOWNLOADER = "feapder.network.downloader.PlaywrightDownloader"
```

Selenium 配置：

```python
WEBDRIVER = {
    "pool_size": 1,
    "load_images": True,
    "user_agent": None,
    "proxy": None,
    "headless": False,
    "driver_type": "CHROME",
    "timeout": 30,
    "window_size": (1024, 800),
    "executable_path": None,
    "render_time": 0,
    "custom_argument": ["--ignore-certificate-errors", "--disable-blink-features=AutomationControlled"],
    "xhr_url_regexes": None,
    "auto_install_driver": True,
    "download_path": None,
    "use_stealth_js": False,
}
```

Playwright 配置：

```python
PLAYWRIGHT = {
    "user_agent": None,
    "proxy": None,
    "headless": False,
    "driver_type": "chromium",
    "timeout": 30,
    "window_size": (1024, 800),
    "render_time": 0,
    "wait_until": "networkidle",
    "url_regexes": None,
    "save_all": False,
}
```

如果渲染后页面内容发生变化，可以先更新 `response.text` 再提取。

## 代理和 User-Agent

常见配置：

```python
PROXY_EXTRACT_API = None
PROXY_ENABLE = True
PROXY_MAX_FAILED_TIMES = 5
PROXY_POOL = "feapder.network.proxy_pool.ProxyPool"

RANDOM_HEADERS = True
USER_AGENT_TYPE = "chrome"
DEFAULT_USERAGENT = "Mozilla/5.0 ..."
USE_SESSION = False
```

请求级参数优先于配置：

```python
yield feapder.Request(
    url,
    headers={"User-Agent": "..."},
    proxies={"http": "http://host:port", "https": "http://host:port"},
)
```

需要按请求动态设置 cookie/header/proxy 时，优先用 `download_midware`。

## 去重

Request 去重：

```python
REQUEST_FILTER_ENABLE = True
REQUEST_FILTER_SETTING = {
    "filter_type": 3,
    "expire_time": 2592000,
}
```

Item 去重：

```python
ITEM_FILTER_ENABLE = True
ITEM_FILTER_SETTING = {
    "filter_type": 1,
}
```

filter 类型：

- `1`：永久 BloomFilter
- `2`：内存去重
- `3`：临时过期去重
- `4`：轻量去重

单个请求跳过去重：

```python
yield feapder.Request(url, filter_repeat=False)
```
