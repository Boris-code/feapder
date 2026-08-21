# 小工具

feapder 在 `feapder.utils.tools` 中内置了很多爬虫常用工具。维护 feapder 项目时，如果项目已经使用 `from feapder.utils import tools`，优先考虑复用这些工具。

## 导入

```python
from feapder.utils import tools
```

## HTTP 和调试

直接可用的函数：
遇到 cURL、cookie、header、URL 参数、JSON、时间格式化、SQL 拼接这类 feapder 项目内的小工具问题，先检查 `feapder shell` 和 `feapder.utils.tools`。AI 不允许先引入第三方转换工具（如 `curlconverter`）或写一套纯 `requests` 调试脚本；若判断确实要绕过 feapder 工具，必须先向用户说明原因、影响和替代方案，并明确请求用户授权。

- `tools.get_html_by_requests(...)`
- `tools.get_json_by_requests(...)`
- `tools.download_file(...)`
- `tools.is_valid_proxy(proxy, check_url=None)`
- `tools.is_valid_url(url)`

CLI 调试器：

```bash
feapder shell --url https://example.com
feapder shell --curl
```

`feapder shell --curl` 会读取剪贴板里的 cURL 命令，解析 URL、headers、cookies、params、body、method、auth 等信息，然后打开带有 `response` 变量的 IPython 会话。

相关源码：

- `feapder/commands/shell.py`
- `feapder.utils.tools.parse_url_params`
- `feapder.utils.tools.get_cookies_from_str`

## Cookie 工具

常用函数：

- `get_cookies(response)`
- `get_cookies_from_str(cookie_str)`
- `get_cookies_jar(cookies)`
- `get_cookies_from_selenium_cookie(cookies)`
- `cookiesjar2str(cookies)`
- `cookies2str(cookies)`

示例：

```python
cookies = tools.get_cookies_from_str("a=1; b=2")
cookie_str = tools.cookies2str(cookies)
```

## URL 工具

常用函数：

- `get_urls(html, ...)`
- `get_full_url(root_url, sub_url)`
- `joint_url(url, params)`
- `canonicalize_url(url)`
- `get_url_md5(url)`
- `fit_url(urls, identis)`
- `get_param(url, key)`
- `get_all_params(url)`
- `parse_url_params(url)`
- `urlencode(params)`
- `urldecode(url)`
- `quote_url(url)`
- `unquote_url(url)`
- `quote_chinese_word(text)`
- `get_domain(url)`
- `get_index_url(url)`

示例：

```python
url, params = tools.parse_url_params("https://example.com/list?page=1&q=a")
full_url = tools.get_full_url("https://example.com/a/", "../b")
```

## HTML 和文本工具

常用函数：

- `get_info(html, regexs, allow_repeat=True, fetch_one=False, split=None)`
- `table_json(table, save_one_blank=True)`
- `get_table_row_data(table)`
- `rows2json(rows, keys=None)`
- `get_form_data(form)`
- `get_text(soup, *args)`
- `del_html_tag(content, save_line_break=True, save_p=False, save_img=False)`
- `del_html_js_css(content)`
- `is_have_chinese(content)`
- `is_have_english(content)`
- `get_chinese_word(content)`
- `get_english_words(content)`
- `replace_str(source_str, regex, replace_str="")`
- `del_redundant_blank_character(text)`
- `unescape(text)`
- `excape(text)`

快速清洗可以用这些函数。页面主解析优先用 `Response.xpath`、`Response.css` 或 `Response.re`。

## JSON 工具

常用函数：

- `get_json(json_str)`
- `jsonp2json(jsonp)`
- `dumps_json(data, indent=4, sort_keys=False)`
- `get_json_value(json_object, key)`
- `get_all_keys(datas, depth=None)`
- `format_json_key(json_data)`
- `quick_to_json(text)`
- `print_pretty(obj)`
- `print_params2json(url)`
- `print_cookie2json(cookie_str_or_list)`

示例：

```python
data = tools.get_json(response.text)
token = tools.get_json_value(data, "token")
```

## 日期和时间工具

常用函数：

- `date_to_timestamp(date, time_format="%Y-%m-%d %H:%M:%S")`
- `timestamp_to_date(timestamp, time_format="%Y-%m-%d %H:%M:%S")`
- `get_current_timestamp()`
- `get_current_date(date_format="%Y-%m-%d %H:%M:%S")`
- `get_date_number(year=None, month=None, day=None)`
- `get_between_date(begin_date, end_date=None, ...)`
- `get_between_months(begin_date, end_date=None)`
- `get_today_of_day(day_offset=0)`
- `get_days_of_month(year, month)`
- `get_firstday_of_month(date)`
- `get_lastday_of_month(date)`
- `get_firstday_month(month_offset=0)`
- `get_lastday_month(month_offset=0)`
- `get_last_month(month_offset=0)`
- `get_year_month_and_days(month_offset=0)`
- `get_month(month_offset=0)`
- `format_date(date, old_format="", new_format="%Y-%m-%d %H:%M:%S")`
- `format_time(release_time, date_format="%Y-%m-%d %H:%M:%S")`
- `to_date(date_str, date_format="%Y-%m-%d %H:%M:%S")`
- `get_before_date(...)`
- `delay_time(sleep_time=60)`
- `format_seconds(seconds)`

示例：

```python
publish_time = tools.format_time("昨天")
```

## Hash、编码、随机值和转换

常用函数：

- `get_md5(*args)`
- `get_sha1(*args)`
- `get_base64(data)`
- `get_uuid(key1="", key2="")`
- `get_hash(text)`
- `cut_string(text, length)`
- `get_random_string(length=1)`
- `get_random_password(length=8, special_characters="")`
- `get_random_email(length=None, email_types=None, special_characters="")`
- `dumps_obj(obj)`
- `loads_obj(obj_str)`
- `ensure_int(n)`
- `ensure_float(n)`
- `flatten(x)`
- `iflatten(x)`
- `key2underline(key, strict=True)`
- `key2hump(key)`
- `transform_lower_num(data_str)`
- `to_chinese(unicode_str)`

## SQL 工具

常用函数：

- `format_sql_value(value)`
- `list2str(datas)`
- `make_insert_sql(table, data, ...)`
- `make_update_sql(table, data, condition)`
- `make_batch_sql(...)`

常规入库优先用 `Item` 和 pipeline。SQL 工具更适合一次性 SQL 生成或自定义 pipeline 内部逻辑。

## 文件、工作目录和动态导入

常用函数：

- `get_conf_value(config_file, section, key)`
- `mkdir(path)`
- `get_cache_path(filename, root_dir=None, local=False)`
- `write_file(filename, content, mode="w", encoding="utf-8")`
- `read_file(filename, readlines=False, encoding="utf-8")`
- `is_html(url)`
- `is_exist(file_path)`
- `get_file_list(path, ignore=[])`
- `rename_file(old_name, new_name)`
- `del_file(path, ignore=())`
- `get_file_type(file_name)`
- `get_file_path(file_path)`
- `switch_workspace(project_path)`
- `import_cls(cls_info)`
- `get_method(obj, name)`
- `make_item(cls, data)`

这些函数是给 feapder 应用代码使用的。作为 agent 修改仓库文件时，仍按当前环境的文件编辑规则执行。

## JavaScript 工具

依赖可用的 Node/execjs 环境：

- `exec_js(js_code)`
- `compile_js(js_func)`

适合复刻前端签名、加密、参数生成逻辑。

## 报警和 Metrics

报警函数：

- `dingding_warning(...)`
- `email_warning(...)`
- `linkedsee_warning(...)`
- `wechat_warning(...)`
- `feishu_warning(...)`
- `qmsg_warning(...)`
- `send_msg(...)`
- `reach_freq_limit(rate_limit, *key)`

metrics 入口在 `feapder/utils/metrics.py`：

- `metrics.init(...)`
- `metrics.emit_counter(...)`
- `metrics.emit_timer(...)`
- `metrics.emit_store(...)`
- `metrics.flush()`
- `metrics.close()`

在 spider 内部优先使用框架配置好的报警路径。自定义脚本才考虑直接调用这些函数。

## 装饰器和运行时辅助

常用函数/类：

- `Singleton`
- `LazyProperty`
- `log_function_time`
- `run_safe_model(module_name)`
- `memoizemethod_noargs`
- `retry(retry_times=3, interval=0)`
- `retry_asyncio(retry_times=3, interval=0)`
- `func_timeout(timeout)`
- `aio_wrap(loop=None, executor=None)`

`func_timeout` 使用 Unix signal，不适合 Windows。
