# -*- coding: utf-8 -*-
"""
Created on 2018-09-06 14:21
---------
@summary: 工具
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import asyncio
import base64
import calendar
import codecs
import configparser  # 读配置文件的
import datetime
import functools
import hashlib
import html
import importlib
import json
import os
import pickle
import random
import re
import signal
import socket
import ssl
import string
import sys
import time
import traceback
import urllib
import urllib.parse
import uuid
import weakref
from functools import partial, wraps
from hashlib import md5
from pprint import pformat
from pprint import pprint
from urllib import request
from urllib.parse import urljoin

import redis
import requests
import six
from requests.cookies import RequestsCookieJar
from w3lib.url import canonicalize_url as _canonicalize_url

import feapder.setting as setting
from feapder.db.redisdb import RedisDB
from feapder.utils.email_sender import EmailSender
from feapder.utils.log import log

try:
    import execjs  # pip install PyExecJS
except Exception as e:
    pass

os.environ["EXECJS_RUNTIME"] = "Node"  # 设置使用node执行js

# 全局取消ssl证书验证
ssl._create_default_https_context = ssl._create_unverified_context

TIME_OUT = 30
TIMER_TIME = 5

redisdb = None


def get_redisdb():
    global redisdb
    if not redisdb:
        redisdb = RedisDB()
    return redisdb


# 装饰器
class Singleton(object):
    def __init__(self, cls):
        self._cls = cls
        self._instance = {}

    def __call__(self, *args, **kwargs):
        if self._cls not in self._instance:
            self._instance[self._cls] = self._cls(*args, **kwargs)
        return self._instance[self._cls]


class LazyProperty:
    """
    属性延时初始化，且只初始化一次
    """

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            value = self.func(instance)
            setattr(instance, self.func.__name__, value)
            return value


def log_function_time(func):
    try:

        @functools.wraps(func)  # 将函数的原来属性付给新函数
        def calculate_time(*args, **kw):
            began_time = time.time()
            callfunc = func(*args, **kw)
            end_time = time.time()
            log.debug(func.__name__ + " run time  = " + str(end_time - began_time))
            return callfunc

        return calculate_time
    except:
        log.debug("求取时间无效 因为函数参数不符")
        return func


def run_safe_model(module_name):
    def inner_run_safe_model(func):
        try:

            @functools.wraps(func)  # 将函数的原来属性付给新函数
            def run_func(*args, **kw):
                callfunc = None
                try:
                    callfunc = func(*args, **kw)
                except Exception as e:
                    log.error(module_name + ": " + func.__name__ + " - " + str(e))
                    traceback.print_exc()
                return callfunc

            return run_func
        except Exception as e:
            log.error(module_name + ": " + func.__name__ + " - " + str(e))
            traceback.print_exc()
            return func

    return inner_run_safe_model


def memoizemethod_noargs(method):
    """Decorator to cache the result of a method (without arguments) using a
    weak reference to its object
    """
    cache = weakref.WeakKeyDictionary()

    @functools.wraps(method)
    def new_method(self, *args, **kwargs):
        if self not in cache:
            cache[self] = method(self, *args, **kwargs)
        return cache[self]

    return new_method


def retry(retry_times=3, interval=0):
    """
    普通函数的重试装饰器
    Args:
        retry_times: 重试次数
        interval: 每次重试之间的间隔

    Returns:

    """

    def _retry(func):
        @functools.wraps(func)  # 将函数的原来属性付给新函数
        def wapper(*args, **kwargs):
            for i in range(retry_times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    log.error(
                        "函数 {} 执行失败 重试 {} 次. error {}".format(func.__name__, i + 1, e)
                    )
                    time.sleep(interval)
                    if i + 1 >= retry_times:
                        raise e

        return wapper

    return _retry


def retry_asyncio(retry_times=3, interval=0):
    """
    协程的重试装饰器
    Args:
        retry_times: 重试次数
        interval: 每次重试之间的间隔

    Returns:

    """

    def _retry(func):
        @functools.wraps(func)  # 将函数的原来属性付给新函数
        async def wapper(*args, **kwargs):
            for i in range(retry_times):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    log.error(
                        "函数 {} 执行失败 重试 {} 次. error {}".format(func.__name__, i + 1, e)
                    )
                    await asyncio.sleep(interval)
                    if i + 1 >= retry_times:
                        raise e

        return wapper

    return _retry


def func_timeout(timeout):
    """
    函数运行时间限制装饰器
    注: 不支持window
    Args:
        timeout: 超时的时间

    Eg:
        @set_timeout(3)
        def test():
            ...

    Returns:

    """

    def wapper(func):
        def handle(
            signum, frame
        ):  # 收到信号 SIGALRM 后的回调函数，第一个参数是信号的数字，第二个参数是the interrupted stack frame.
            raise TimeoutError

        def new_method(*args, **kwargs):
            signal.signal(signal.SIGALRM, handle)  # 设置信号和回调函数
            signal.alarm(timeout)  # 设置 timeout 秒的闹钟
            r = func(*args, **kwargs)
            signal.alarm(0)  # 关闭闹钟
            return r

        return new_method

    return wapper


########################【网页解析相关】###############################


# @log_function_time
def get_html_by_requests(
    url, headers=None, code="utf-8", data=None, proxies={}, with_response=False
):
    html = ""
    r = None
    try:
        if data:
            r = requests.post(
                url, headers=headers, timeout=TIME_OUT, data=data, proxies=proxies
            )
        else:
            r = requests.get(url, headers=headers, timeout=TIME_OUT, proxies=proxies)

        if code:
            r.encoding = code
        html = r.text

    except Exception as e:
        log.error(e)
    finally:
        r and r.close()

    if with_response:
        return html, r
    else:
        return html


def get_json_by_requests(
    url,
    params=None,
    headers=None,
    data=None,
    proxies={},
    with_response=False,
    cookies=None,
):
    json = {}
    response = None
    try:
        # response = requests.get(url, params = params)
        if data:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                params=params,
                timeout=TIME_OUT,
                proxies=proxies,
                cookies=cookies,
            )
        else:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=TIME_OUT,
                proxies=proxies,
                cookies=cookies,
            )
        response.encoding = "utf-8"
        json = response.json()
    except Exception as e:
        log.error(e)
    finally:
        response and response.close()

    if with_response:
        return json, response
    else:
        return json


def get_cookies(response):
    cookies = requests.utils.dict_from_cookiejar(response.cookies)
    return cookies


def get_cookies_from_str(cookie_str):
    """
    >>> get_cookies_from_str("key=value; key2=value2; key3=; key4=; ")
    {'key': 'value', 'key2': 'value2', 'key3': '', 'key4': ''}

    Args:
        cookie_str: key=value; key2=value2; key3=; key4=

    Returns:

    """
    cookies = {}
    for cookie in cookie_str.split(";"):
        cookie = cookie.strip()
        if not cookie:
            continue
        key, value = cookie.split("=", 1)
        key = key.strip()
        value = value.strip()
        cookies[key] = value

    return cookies


def get_cookies_jar(cookies):
    """
    @summary: 适用于selenium生成的cookies转requests的cookies
    requests.get(xxx, cookies=jar)
    参考：https://www.cnblogs.com/small-bud/p/9064674.html

    ---------
    @param cookies: [{},{}]
    ---------
    @result: cookie jar
    """

    cookie_jar = RequestsCookieJar()
    for cookie in cookies:
        cookie_jar.set(cookie["name"], cookie["value"])

    return cookie_jar


def get_cookies_from_selenium_cookie(cookies):
    """
    @summary: 适用于selenium生成的cookies转requests的cookies
    requests.get(xxx, cookies=jar)
    参考：https://www.cnblogs.com/small-bud/p/9064674.html

    ---------
    @param cookies: [{},{}]
    ---------
    @result: cookie jar
    """

    cookie_dict = {}
    for cookie in cookies:
        if cookie.get("name"):
            cookie_dict[cookie["name"]] = cookie["value"]

    return cookie_dict


def cookiesjar2str(cookies):
    str_cookie = ""
    for k, v in requests.utils.dict_from_cookiejar(cookies).items():
        str_cookie += k
        str_cookie += "="
        str_cookie += v
        str_cookie += "; "
    return str_cookie


def cookies2str(cookies):
    str_cookie = ""
    for k, v in cookies.items():
        str_cookie += k
        str_cookie += "="
        str_cookie += v
        str_cookie += "; "
    return str_cookie


def get_urls(
    html,
    stop_urls=(
        "javascript",
        "+",
        ".css",
        ".js",
        ".rar",
        ".xls",
        ".exe",
        ".apk",
        ".doc",
        ".jpg",
        ".png",
        ".flv",
        ".mp4",
    ),
):
    # 不匹配javascript、 +、 # 这样的url
    regex = r'<a.*?href.*?=.*?["|\'](.*?)["|\']'

    urls = get_info(html, regex)
    urls = sorted(set(urls), key=urls.index)
    if stop_urls:
        stop_urls = isinstance(stop_urls, str) and [stop_urls] or stop_urls
        use_urls = []
        for url in urls:
            for stop_url in stop_urls:
                if stop_url in url:
                    break
            else:
                use_urls.append(url)

        urls = use_urls
    return urls


def get_full_url(root_url, sub_url):
    """
    @summary: 得到完整的ur
    ---------
    @param root_url: 根url （网页的url）
    @param sub_url:  子url （带有相对路径的 可以拼接成完整的）
    ---------
    @result: 返回完整的url
    """

    return urljoin(root_url, sub_url)


def joint_url(url, params):
    # param_str = "?"
    # for key, value in params.items():
    #     value = isinstance(value, str) and value or str(value)
    #     param_str += key + "=" + value + "&"
    #
    # return url + param_str[:-1]

    if not params:
        return url

    params = urlencode(params)
    separator = "?" if "?" not in url else "&"
    return url + separator + params


def canonicalize_url(url):
    """
    url 归一化 会参数排序 及去掉锚点
    """
    return _canonicalize_url(url)


def get_url_md5(url):
    url = canonicalize_url(url)
    url = re.sub("^http://", "https://", url)
    return get_md5(url)


def fit_url(urls, identis):
    identis = isinstance(identis, str) and [identis] or identis
    fit_urls = []
    for link in urls:
        for identi in identis:
            if identi in link:
                fit_urls.append(link)
    return list(set(fit_urls))


def get_param(url, key):
    match = re.search(f"{key}=([^&]+)", url)
    if match:
        return match.group(1)
    return None


def get_all_params(url):
    """
    >>> get_all_params("https://www.baidu.com/s?wd=feapder")
    {'wd': 'feapder'}
    """
    params_json = {}
    params = url.split("?", 1)[-1].split("&")
    for param in params:
        key_value = param.split("=", 1)
        if len(key_value) == 2:
            params_json[key_value[0]] = unquote_url(key_value[1])
        else:
            params_json[key_value[0]] = ""

    return params_json


def parse_url_params(url):
    """
    解析url参数
    :param url:
    :return:

    >>> parse_url_params("https://www.baidu.com/s?wd=%E4%BD%A0%E5%A5%BD")
    ('https://www.baidu.com/s', {'wd': '你好'})
    >>> parse_url_params("wd=%E4%BD%A0%E5%A5%BD")
    ('', {'wd': '你好'})
    >>> parse_url_params("https://www.baidu.com/s?wd=%E4%BD%A0%E5%A5%BD&pn=10")
    ('https://www.baidu.com/s', {'wd': '你好', 'pn': '10'})
    >>> parse_url_params("wd=%E4%BD%A0%E5%A5%BD&pn=10")
    ('', {'wd': '你好', 'pn': '10'})
    >>> parse_url_params("https://www.baidu.com")
    ('https://www.baidu.com', {})
    >>> parse_url_params("https://www.spidertools.cn/#/")
    ('https://www.spidertools.cn/#/', {})
    """
    root_url = ""
    params = {}
    if "?" not in url:
        if re.search("[&=]", url) and not re.search("/", url):
            # 只有参数
            params = get_all_params(url)
        else:
            root_url = url

    else:
        root_url = url.split("?", 1)[0]
        params = get_all_params(url)

    return root_url, params


def urlencode(params):
    """
    字典类型的参数转为字符串
    @param params:
    {
        'a': 1,
        'b': 2
    }
    @return: a=1&b=2
    """
    return urllib.parse.urlencode(params)


def urldecode(url):
    """
    将字符串类型的参数转为json
    @param url: xxx?a=1&b=2
    @return:
    {
        'a': 1,
        'b': 2
    }
    """
    params_json = {}
    params = url.split("?")[-1].split("&")
    for param in params:
        key, value = param.split("=")
        params_json[key] = unquote_url(value)

    return params_json


def unquote_url(url, encoding="utf-8"):
    """
    @summary: 将url解码
    ---------
    @param url:
    ---------
    @result:
    """

    return urllib.parse.unquote(url, encoding=encoding)


def quote_url(url, encoding="utf-8"):
    """
    @summary: 将url编码 编码意思http://www.w3school.com.cn/tags/html_ref_urlencode.html
    ---------
    @param url:
    ---------
    @result:
    """

    return urllib.parse.quote(url, safe="%;/?:@&=+$,", encoding=encoding)


def quote_chinese_word(text, encoding="utf-8"):
    def quote_chinese_word_func(text):
        chinese_word = text.group(0)
        return urllib.parse.quote(chinese_word, encoding=encoding)

    return re.sub("([\u4e00-\u9fa5]+)", quote_chinese_word_func, text, flags=re.S)


def unescape(str):
    """
    反转译
    """
    return html.unescape(str)


def excape(str):
    """
    转译
    """
    return html.escape(str)


_regexs = {}


# @log_function_time
def get_info(html, regexs, allow_repeat=True, fetch_one=False, split=None):
    regexs = isinstance(regexs, str) and [regexs] or regexs

    infos = []
    for regex in regexs:
        if regex == "":
            continue

        if regex not in _regexs.keys():
            _regexs[regex] = re.compile(regex, re.S)

        if fetch_one:
            infos = _regexs[regex].search(html)
            if infos:
                infos = infos.groups()
            else:
                continue
        else:
            infos = _regexs[regex].findall(str(html))

        if len(infos) > 0:
            # print(regex)
            break

    if fetch_one:
        infos = infos if infos else ("",)
        return infos if len(infos) > 1 else infos[0]
    else:
        infos = allow_repeat and infos or sorted(set(infos), key=infos.index)
        infos = split.join(infos) if split else infos
        return infos


def table_json(table, save_one_blank=True):
    """
    将表格转为json 适应于 key：value 在一行类的表格
    @param table: 使用selector封装后的具有xpath的selector
    @param save_one_blank: 保留一个空白符
    @return:
    """
    data = {}

    trs = table.xpath(".//tr")
    for tr in trs:
        tds = tr.xpath("./td|./th")

        for i in range(0, len(tds), 2):
            if i + 1 > len(tds) - 1:
                break

            key = tds[i].xpath("string(.)").extract_first(default="").strip()
            value = tds[i + 1].xpath("string(.)").extract_first(default="").strip()
            value = replace_str(value, "[\f\n\r\t\v]", "")
            value = replace_str(value, " +", " " if save_one_blank else "")

            if key:
                data[key] = value

    return data


def get_table_row_data(table):
    """
    获取表格里每一行数据
    @param table: 使用selector封装后的具有xpath的selector
    @return: [[],[]..]
    """

    datas = []
    rows = table.xpath(".//tr")
    for row in rows:
        cols = row.xpath("./td|./th")
        row_datas = []
        for col in cols:
            data = col.xpath("string(.)").extract_first(default="").strip()
            row_datas.append(data)
        datas.append(row_datas)

    return datas


def rows2json(rows, keys=None):
    """
    将行数据转为json
    @param rows: 每一行的数据
    @param keys: json的key，空时将rows的第一行作为key
    @return:
    """
    data_start_pos = 0 if keys else 1
    datas = []
    keys = keys or rows[0]
    for values in rows[data_start_pos:]:
        datas.append(dict(zip(keys, values)))

    return datas


def get_form_data(form):
    """
    提取form中提交的数据
    :param form: 使用selector封装后的具有xpath的selector
    :return:
    """
    data = {}
    inputs = form.xpath(".//input")
    for input in inputs:
        name = input.xpath("./@name").extract_first()
        value = input.xpath("./@value").extract_first()
        if name:
            data[name] = value

    return data


def get_domain(url):
    return urllib.parse.urlparse(url).netloc


def get_index_url(url):
    return "/".join(url.split("/")[:3])


def get_ip(domain):
    ip = socket.getaddrinfo(domain, "http")[0][4][0]
    return ip


def get_localhost_ip():
    """
    利用 UDP 协议来实现的，生成一个UDP包，把自己的 IP 放如到 UDP 协议头中，然后从UDP包中获取本机的IP。
    这个方法并不会真实的向外部发包，所以用抓包工具是看不到的
    :return:
    """
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = ""
    finally:
        if s:
            s.close()

    return ip


def ip_to_num(ip):
    import struct

    ip_num = socket.ntohl(struct.unpack("I", socket.inet_aton(str(ip)))[0])
    return ip_num


def is_valid_proxy(proxy, check_url=None):
    """
    检验代理是否有效
    @param proxy: xxx.xxx.xxx:xxx
    @param check_url: 利用目标网站检查，目标网站url。默认为None， 使用代理服务器的socket检查, 但不能排除Connection closed by foreign host
    @return: True / False
    """
    is_valid = False

    if check_url:
        proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36"
        }
        response = None
        try:
            response = requests.get(
                check_url, headers=headers, proxies=proxies, stream=True, timeout=20
            )
            is_valid = True

        except Exception as e:
            log.error("check proxy failed: {} {}".format(e, proxy))

        finally:
            if response:
                response.close()

    else:
        ip, port = proxy.split(":")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sk:
            sk.settimeout(7)
            try:
                sk.connect((ip, int(port)))  # 检查代理服务器是否开着
                is_valid = True

            except Exception as e:
                log.error("check proxy failed: {} {}:{}".format(e, ip, port))

    return is_valid


def is_valid_url(url):
    """
    验证url是否合法
    :param url:
    :return:
    """
    if re.match(r"(^https?:/{2}\w.+$)|(ftp://)", url):
        return True
    else:
        return False


def get_text(soup, *args):
    try:
        return soup.get_text()
    except Exception as e:
        log.error(e)
        return ""


def del_html_tag(content, save_line_break=True, save_p=False, save_img=False):
    """
    删除html标签
    @param content: html内容
    @param save_p: 保留p标签
    @param save_img: 保留图片标签
    @param save_line_break: 保留\n换行
    @return:
    """
    if not content:
        return content
    # js
    content = re.sub("(?i)<script(.|\n)*?</script>", "", content)  # (?)忽略大小写
    # css
    content = re.sub("(?i)<style(.|\n)*?</style>", "", content)  # (?)忽略大小写
    # 注释
    content = re.sub("<!--(.|\n)*?-->", "", content)
    # 干掉&nbsp;等无用的字符 但&xxx= 这种表示参数的除外
    content = re.sub("(?!&[a-z]+=)&[a-z]+;?", "", content)

    if save_p and save_img:
        content = re.sub("<(?!(p[ >]|/p>|img ))(.|\n)+?>", "", content)
    elif save_p:
        content = re.sub("<(?!(p[ >]|/p>))(.|\n)+?>", "", content)
    elif save_img:
        content = re.sub("<(?!img )(.|\n)+?>", "", content)
    elif save_line_break:
        content = re.sub("<(?!/p>)(.|\n)+?>", "", content)
        content = re.sub("</p>", "\n", content)
    else:
        content = re.sub("<(.|\n)*?>", "", content)

    if save_line_break:
        # 把非换行符的空白符替换为一个空格
        content = re.sub("[^\S\n]+", " ", content)
        # 把多个换行符替换为一个换行符 如\n\n\n 或 \n \n \n 替换为\n
        content = re.sub("(\n ?)+", "\n", content)
    else:
        content = re.sub("\s+", " ", content)
    content = content.strip()

    return content


def del_html_js_css(content):
    content = replace_str(content, "(?i)<script(.|\n)*?</script>")  # (?)忽略大小写
    content = replace_str(content, "(?i)<style(.|\n)*?</style>")
    content = replace_str(content, "<!--(.|\n)*?-->")

    return content


def is_have_chinese(content):
    regex = "[\u4e00-\u9fa5]+"
    chinese_word = get_info(content, regex)
    return chinese_word and True or False


def is_have_english(content):
    regex = "[a-zA-Z]+"
    english_words = get_info(content, regex)
    return english_words and True or False


def get_chinese_word(content):
    regex = "[\u4e00-\u9fa5]+"
    chinese_word = get_info(content, regex)
    return chinese_word


def get_english_words(content):
    regex = "[a-zA-Z]+"
    english_words = get_info(content, regex)
    return english_words or ""


##################################################
def get_json(json_str):
    """
    @summary: 取json对象
    ---------
    @param json_str: json格式的字符串
    ---------
    @result: 返回json对象
    """

    try:
        return json.loads(json_str) if json_str else {}
    except Exception as e1:
        try:
            json_str = json_str.strip()
            json_str = json_str.replace("'", '"')
            keys = get_info(json_str, "(\w+):")
            for key in keys:
                json_str = json_str.replace(key, '"%s"' % key)

            return json.loads(json_str) if json_str else {}

        except Exception as e2:
            log.error(
                """
                e1: %s
                format json_str: %s
                e2: %s
                """
                % (e1, json_str, e2)
            )

        return {}


def jsonp2json(jsonp):
    """
    将jsonp转为json
    @param jsonp: jQuery172013600082560040794_1553230569815({})
    @return:
    """
    try:
        return json.loads(re.match(".*?({.*}).*", jsonp, re.S).group(1))
    except:
        raise ValueError("Invalid Input")


def dumps_json(data, indent=4, sort_keys=False):
    """
    @summary: 格式化json 用于打印
    ---------
    @param data: json格式的字符串或json对象
    ---------
    @result: 格式化后的字符串
    """
    try:
        if isinstance(data, str):
            data = get_json(data)

        data = json.dumps(
            data,
            ensure_ascii=False,
            indent=indent,
            skipkeys=True,
            sort_keys=sort_keys,
            default=str,
        )

    except Exception as e:
        data = pformat(data)

    return data


def get_json_value(json_object, key):
    """
    @summary:
    ---------
    @param json_object: json对象或json格式的字符串
    @param key: 建值 如果在多个层级目录下 可写 key1.key2  如{'key1':{'key2':3}}
    ---------
    @result: 返回对应的值，如果没有，返回''
    """
    current_key = ""
    value = ""
    try:
        json_object = (
            isinstance(json_object, str) and get_json(json_object) or json_object
        )

        current_key = key.split(".")[0]
        value = json_object[current_key]

        key = key[key.find(".") + 1 :]
    except Exception as e:
        return value

    if key == current_key:
        return value
    else:
        return get_json_value(value, key)


def get_all_keys(datas, depth=None, current_depth=0):
    """
    @summary: 获取json李所有的key
    ---------
    @param datas: dict / list
    @param depth: 字典key的层级 默认不限制层级 层级从1开始
    @param current_depth: 字典key的当前层级 不用传参
    ---------
    @result: 返回json所有的key
    """

    keys = []
    if depth and current_depth >= depth:
        return keys

    if isinstance(datas, list):
        for data in datas:
            keys.extend(get_all_keys(data, depth, current_depth=current_depth + 1))
    elif isinstance(datas, dict):
        for key, value in datas.items():
            keys.append(key)
            if isinstance(value, dict):
                keys.extend(get_all_keys(value, depth, current_depth=current_depth + 1))

    return keys


def to_chinese(unicode_str):
    format_str = json.loads('{"chinese":"%s"}' % unicode_str)
    return format_str["chinese"]


##################################################
def replace_str(source_str, regex, replace_str=""):
    """
    @summary: 替换字符串
    ---------
    @param source_str: 原字符串
    @param regex: 正则
    @param replace_str: 用什么来替换 默认为''
    ---------
    @result: 返回替换后的字符串
    """
    str_info = re.compile(regex)
    return str_info.sub(replace_str, source_str)


def del_redundant_blank_character(text):
    """
    删除冗余的空白符， 只保留一个
    :param text:
    :return:
    """
    return re.sub("\s+", " ", text)


##################################################
def get_conf_value(config_file, section, key):
    cp = configparser.ConfigParser(allow_no_value=True)
    with codecs.open(config_file, "r", encoding="utf-8") as f:
        cp.read_file(f)
    return cp.get(section, key)


def mkdir(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except OSError as exc:  # Python >2.5
        pass


def get_cache_path(filename, root_dir=None, local=False):
    """
    Args:
        filename:
        root_dir:
        local: 是否存储到当前目录

    Returns:

    """
    if root_dir is None:
        if local:
            root_dir = os.path.join(sys.path[0], ".cache")
        else:
            root_dir = os.path.join(os.path.expanduser("~"), ".feapder/cache")
    file_path = f"{root_dir}{os.sep}{filename}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    return f"{root_dir}{os.sep}{filename}"


def write_file(filename, content, mode="w", encoding="utf-8"):
    """
    @summary: 写文件
    ---------
    @param filename: 文件名（有路径）
    @param content: 内容
    @param mode: 模式 w/w+ (覆盖/追加)
    ---------
    @result:
    """

    directory = os.path.dirname(filename)
    mkdir(directory)
    with open(filename, mode, encoding=encoding) as file:
        file.writelines(content)


def read_file(filename, readlines=False, encoding="utf-8"):
    """
    @summary: 读文件
    ---------
    @param filename: 文件名（有路径）
    @param readlines: 按行读取 （默认False）
    ---------
    @result: 按行读取返回List，否则返回字符串
    """

    content = None
    try:
        with open(filename, "r", encoding=encoding) as file:
            content = file.readlines() if readlines else file.read()
    except Exception as e:
        log.error(e)

    return content


def get_oss_file_list(oss_handler, prefix, date_range_min, date_range_max=None):
    """
    获取文件列表
    @param prefix: 路径前缀 如 data/car_service_line/yiche/yiche_serial_zongshu_info
    @param date_range_min: 时间范围 最小值 日期分隔符为/ 如 2019/03/01 或 2019/03/01/00/00/00
    @param date_range_max: 时间范围 最大值 日期分隔符为/ 如 2019/03/01 或 2019/03/01/00/00/00
    @return: 每个文件路径 如 html/e_commerce_service_line/alibaba/alibaba_shop_info/2019/03/22/15/53/15/8ca8b9e4-4c77-11e9-9dee-acde48001122.json.snappy
    """

    # 计算时间范围
    date_range_max = date_range_max or date_range_min
    date_format = "/".join(
        ["%Y", "%m", "%d", "%H", "%M", "%S"][: date_range_min.count("/") + 1]
    )
    time_interval = [
        {"days": 365},
        {"days": 31},
        {"days": 1},
        {"hours": 1},
        {"minutes": 1},
        {"seconds": 1},
    ][date_range_min.count("/")]
    date_range = get_between_date(
        date_range_min, date_range_max, date_format=date_format, **time_interval
    )

    for date in date_range:
        file_folder_path = os.path.join(prefix, date)
        objs = oss_handler.list(prefix=file_folder_path)
        for obj in objs:
            filename = obj.key
            yield filename


def is_html(url):
    if not url:
        return False

    try:
        content_type = request.urlopen(url).info().get("Content-Type", "")

        if "text/html" in content_type:
            return True
        else:
            return False
    except Exception as e:
        log.error(e)
        return False


def is_exist(file_path):
    """
    @summary: 文件是否存在
    ---------
    @param file_path:
    ---------
    @result:
    """

    return os.path.exists(file_path)


def download_file(url, file_path, *, call_func=None, proxies=None, data=None):
    """
    下载文件，会自动创建文件存储目录
    Args:
        url: 地址
        file_path: 文件存储地址
        call_func: 下载成功的回调
        proxies: 代理
        data: 请求体

    Returns:

    """
    directory = os.path.dirname(file_path)
    mkdir(directory)

    # 进度条
    def progress_callfunc(blocknum, blocksize, totalsize):
        """回调函数
        @blocknum : 已经下载的数据块
        @blocksize : 数据块的大小
        @totalsize: 远程文件的大小
        """
        percent = 100.0 * blocknum * blocksize / totalsize
        if percent > 100:
            percent = 100
        # print ('进度条 %.2f%%' % percent, end = '\r')
        sys.stdout.write("进度条 %.2f%%" % percent + "\r")
        sys.stdout.flush()

    if url:
        try:
            if proxies:
                # create the object, assign it to a variable
                proxy = request.ProxyHandler(proxies)
                # construct a new opener using your proxy settings
                opener = request.build_opener(proxy)
                # install the openen on the module-level
                request.install_opener(opener)

            request.urlretrieve(url, file_path, progress_callfunc, data)

            if callable(call_func):
                call_func()
            return 1
        except Exception as e:
            log.error(e)
            return 0
    else:
        return 0


def get_file_list(path, ignore=[]):
    templist = path.split("*")
    path = templist[0]
    file_type = templist[1] if len(templist) >= 2 else ""

    # 递归遍历文件
    def get_file_list_(path, file_type, ignore, all_file=[]):
        file_list = os.listdir(path)

        for file_name in file_list:
            if file_name in ignore:
                continue

            file_path = os.path.join(path, file_name)
            if os.path.isdir(file_path):
                get_file_list_(file_path, file_type, ignore, all_file)
            else:
                if not file_type or file_name.endswith(file_type):
                    all_file.append(file_path)

        return all_file

    return get_file_list_(path, file_type, ignore) if os.path.isdir(path) else [path]


def rename_file(old_name, new_name):
    os.rename(old_name, new_name)


def del_file(path, ignore=()):
    files = get_file_list(path, ignore)
    for file in files:
        try:
            os.remove(file)
        except Exception as e:
            log.error(
                """
                删除出错: %s
                Exception : %s
                """
                % (file, str(e))
            )
        finally:
            pass


def get_file_type(file_name):
    """
    @summary: 取文件后缀名
    ---------
    @param file_name:
    ---------
    @result:
    """
    try:
        return os.path.splitext(file_name)[1]
    except Exception as e:
        log.exception(e)


def get_file_path(file_path):
    """
    @summary: 取文件路径
    ---------
    @param file_path: /root/a.py
    ---------
    @result: /root
    """
    try:
        return os.path.split(file_path)[0]
    except Exception as e:
        log.exception(e)


#############################################


def exec_js(js_code):
    """
    @summary: 执行js代码
    ---------
    @param js_code: js代码
    ---------
    @result: 返回执行结果
    """

    return execjs.eval(js_code)


def compile_js(js_func):
    """
    @summary: 编译js函数
    ---------
    @param js_func:js函数
    ---------
    @result: 返回函数对象 调用 fun('js_funName', param1,param2)
    """

    ctx = execjs.compile(js_func)
    return ctx.call


#############################################


def date_to_timestamp(date, time_format="%Y-%m-%d %H:%M:%S"):
    """
    @summary:
    ---------
    @param date:将"2011-09-28 10:00:00"时间格式转化为时间戳
    @param format:时间格式
    ---------
    @result: 返回时间戳
    """

    timestamp = time.mktime(time.strptime(date, time_format))
    return int(timestamp)


def timestamp_to_date(timestamp, time_format="%Y-%m-%d %H:%M:%S"):
    """
    @summary:
    ---------
    @param timestamp: 将时间戳转化为日期
    @param format: 日期格式
    ---------
    @result: 返回日期
    """
    if timestamp is None:
        raise ValueError("timestamp is null")

    date = time.localtime(timestamp)
    return time.strftime(time_format, date)


def get_current_timestamp():
    return int(time.time())


def get_current_date(date_format="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.now().strftime(date_format)
    # return time.strftime(date_format, time.localtime(time.time()))


def get_date_number(year=None, month=None, day=None):
    """
    @summary: 获取指定日期对应的日期数
    默认当前周
    ---------
    @param year: 2010
    @param month: 6
    @param day: 16
    ---------
    @result: (年号，第几周，第几天) 如 (2010, 24, 3)
    """
    if year and month and day:
        return datetime.date(year, month, day).isocalendar()
    elif not any([year, month, day]):
        return datetime.datetime.now().isocalendar()
    else:
        assert year, "year 不能为空"
        assert month, "month 不能为空"
        assert day, "day 不能为空"


def get_between_date(
    begin_date, end_date=None, date_format="%Y-%m-%d", **time_interval
):
    """
    @summary: 获取一段时间间隔内的日期，默认为每一天
    ---------
    @param begin_date: 开始日期 str 如 2018-10-01
    @param end_date: 默认为今日
    @param date_format: 日期格式，应与begin_date的日期格式相对应
    @param time_interval: 时间间隔 默认一天 支持 days、seconds、microseconds、milliseconds、minutes、hours、weeks
    ---------
    @result: list 值为字符串
    """

    date_list = []

    begin_date = datetime.datetime.strptime(begin_date, date_format)
    end_date = (
        datetime.datetime.strptime(end_date, date_format)
        if end_date
        else datetime.datetime.strptime(
            time.strftime(date_format, time.localtime(time.time())), date_format
        )
    )
    time_interval = time_interval or dict(days=1)

    while begin_date <= end_date:
        date_str = begin_date.strftime(date_format)
        date_list.append(date_str)

        begin_date += datetime.timedelta(**time_interval)

    if end_date.strftime(date_format) not in date_list:
        date_list.append(end_date.strftime(date_format))

    return date_list


def get_between_months(begin_date, end_date=None):
    """
    @summary: 获取一段时间间隔内的月份
    需要满一整月
    ---------
    @param begin_date: 开始时间 如 2018-01-01
    @param end_date: 默认当前时间
    ---------
    @result: 列表 如 ['2018-01', '2018-02']
    """

    def add_months(dt, months):
        month = dt.month - 1 + months
        year = dt.year + month // 12
        month = month % 12 + 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    date_list = []
    begin_date = datetime.datetime.strptime(begin_date, "%Y-%m-%d")
    end_date = (
        datetime.datetime.strptime(end_date, "%Y-%m-%d")
        if end_date
        else datetime.datetime.strptime(
            time.strftime("%Y-%m-%d", time.localtime(time.time())), "%Y-%m-%d"
        )
    )
    while begin_date <= end_date:
        date_str = begin_date.strftime("%Y-%m")
        date_list.append(date_str)
        begin_date = add_months(begin_date, 1)
    return date_list


def get_today_of_day(day_offset=0):
    return str(datetime.date.today() + datetime.timedelta(days=day_offset))


def get_days_of_month(year, month):
    """
    返回天数
    """

    return calendar.monthrange(year, month)[1]


def get_firstday_of_month(date):
    """''
    date format = "YYYY-MM-DD"
    """

    year, month, day = date.split("-")
    year, month, day = int(year), int(month), int(day)

    days = "01"
    if int(month) < 10:
        month = "0" + str(int(month))
    arr = (year, month, days)
    return "-".join("%s" % i for i in arr)


def get_lastday_of_month(date):
    """''
    get the last day of month
    date format = "YYYY-MM-DD"
    """
    year, month, day = date.split("-")
    year, month, day = int(year), int(month), int(day)

    days = calendar.monthrange(year, month)[1]
    month = add_zero(month)
    arr = (year, month, days)
    return "-".join("%s" % i for i in arr)


def get_firstday_month(month_offset=0):
    """''
    get the first day of month from today
    month_offset is how many months
    """
    (y, m, d) = get_year_month_and_days(month_offset)
    d = "01"
    arr = (y, m, d)
    return "-".join("%s" % i for i in arr)


def get_lastday_month(month_offset=0):
    """''
    get the last day of month from today
    month_offset is how many months
    """
    return "-".join("%s" % i for i in get_year_month_and_days(month_offset))


def get_last_month(month_offset=0):
    """''
    get the last day of month from today
    month_offset is how many months
    """
    return "-".join("%s" % i for i in get_year_month_and_days(month_offset)[:2])


def get_year_month_and_days(month_offset=0):
    """
    @summary:
    ---------
    @param month_offset: 月份偏移量
    ---------
    @result: ('2019', '04', '30')
    """

    today = datetime.datetime.now()
    year, month = today.year, today.month

    this_year = int(year)
    this_month = int(month)
    total_month = this_month + month_offset
    if month_offset >= 0:
        if total_month <= 12:
            days = str(get_days_of_month(this_year, total_month))
            total_month = add_zero(total_month)
            return (year, total_month, days)
        else:
            i = total_month // 12
            j = total_month % 12
            if j == 0:
                i -= 1
                j = 12
            this_year += i
            days = str(get_days_of_month(this_year, j))
            j = add_zero(j)
            return (str(this_year), str(j), days)
    else:
        if (total_month > 0) and (total_month < 12):
            days = str(get_days_of_month(this_year, total_month))
            total_month = add_zero(total_month)
            return (year, total_month, days)
        else:
            i = total_month // 12
            j = total_month % 12
            if j == 0:
                i -= 1
                j = 12
            this_year += i
            days = str(get_days_of_month(this_year, j))
            j = add_zero(j)
            return (str(this_year), str(j), days)


def add_zero(n):
    return "%02d" % n


def get_month(month_offset=0):
    """''
    获取当前日期前后N月的日期
    if month_offset>0, 获取当前日期前N月的日期
    if month_offset<0, 获取当前日期后N月的日期
    date format = "YYYY-MM-DD"
    """
    today = datetime.datetime.now()
    day = add_zero(today.day)

    (y, m, d) = get_year_month_and_days(month_offset)
    arr = (y, m, d)
    if int(day) < int(d):
        arr = (y, m, day)
    return "-".join("%s" % i for i in arr)


@run_safe_model("format_date")
def format_date(date, old_format="", new_format="%Y-%m-%d %H:%M:%S"):
    """
    @summary: 格式化日期格式
    ---------
    @param date: 日期 eg：2017年4月17日 3时27分12秒
    @param old_format: 原来的日期格式 如 '%Y年%m月%d日 %H时%M分%S秒'
        %y 两位数的年份表示（00-99）
        %Y 四位数的年份表示（000-9999）
        %m 月份（01-12）
        %d 月内中的一天（0-31）
        %H 24小时制小时数（0-23）
        %I 12小时制小时数（01-12）
        %M 分钟数（00-59）
        %S 秒（00-59）
    @param new_format: 输出的日期格式
    ---------
    @result: 格式化后的日期，类型为字符串 如2017-4-17 03:27:12
    """
    if not date:
        return ""

    if not old_format:
        regex = "(\d+)"
        numbers = get_info(date, regex, allow_repeat=True)
        formats = ["%Y", "%m", "%d", "%H", "%M", "%S"]
        old_format = date
        for i, number in enumerate(numbers[:6]):
            if i == 0 and len(number) == 2:  # 年份可能是两位 用小%y
                old_format = old_format.replace(
                    number, formats[i].lower(), 1
                )  # 替换一次 '2017年11月30日 11:49' 防止替换11月时，替换11小时
            else:
                old_format = old_format.replace(number, formats[i], 1)  # 替换一次

    try:
        date_obj = datetime.datetime.strptime(date, old_format)
        if "T" in date and "Z" in date:
            date_obj += datetime.timedelta(hours=8)
            date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_str = datetime.datetime.strftime(date_obj, new_format)

    except Exception as e:
        log.error("日期格式化出错，old_format = %s 不符合 %s 格式" % (old_format, date))
        date_str = date

    return date_str


def transform_lower_num(data_str: str):
    num_map = {
        "一": "1",
        "二": "2",
        "两": "2",
        "三": "3",
        "四": "4",
        "五": "5",
        "六": "6",
        "七": "7",
        "八": "8",
        "九": "9",
        "十": "0",
    }
    pattern = f'[{"|".join(num_map.keys())}|零]'
    res = re.search(pattern, data_str)
    if not res:
        #  如果字符串中没有包含中文数字 不做处理 直接返回
        return data_str

    data_str = data_str.replace("0", "零")
    for n in num_map:
        data_str = data_str.replace(n, num_map[n])

    re_data_str = re.findall("\d+", data_str)
    for i in re_data_str:
        if len(i) == 3:
            new_i = i.replace("0", "")
            data_str = data_str.replace(i, new_i, 1)
        elif len(i) == 4:
            new_i = i.replace("10", "")
            data_str = data_str.replace(i, new_i, 1)
        elif len(i) == 2 and int(i) < 10:
            new_i = int(i) + 10
            data_str = data_str.replace(i, str(new_i), 1)
        elif len(i) == 1 and int(i) == 0:
            new_i = int(i) + 10
            data_str = data_str.replace(i, str(new_i), 1)

    return data_str.replace("零", "0")


@run_safe_model("format_time")
def format_time(release_time, date_format="%Y-%m-%d %H:%M:%S"):
    """
    >>> format_time("2个月前")
    '2021-08-15 16:24:21'
    >>> format_time("2月前")
    '2021-08-15 16:24:36'
    """
    release_time = transform_lower_num(release_time)
    release_time = release_time.replace("日", "天").replace("/", "-")

    if "年前" in release_time:
        years = re.compile("(\d+)\s*年前").findall(release_time)
        years_ago = datetime.datetime.now() - datetime.timedelta(
            days=int(years[0]) * 365
        )
        release_time = years_ago.strftime("%Y-%m-%d %H:%M:%S")

    elif "月前" in release_time:
        months = re.compile("(\d+)[\s个]*月前").findall(release_time)
        months_ago = datetime.datetime.now() - datetime.timedelta(
            days=int(months[0]) * 30
        )
        release_time = months_ago.strftime("%Y-%m-%d %H:%M:%S")

    elif "周前" in release_time:
        weeks = re.compile("(\d+)\s*周前").findall(release_time)
        weeks_ago = datetime.datetime.now() - datetime.timedelta(days=int(weeks[0]) * 7)
        release_time = weeks_ago.strftime("%Y-%m-%d %H:%M:%S")

    elif "天前" in release_time:
        ndays = re.compile("(\d+)\s*天前").findall(release_time)
        days_ago = datetime.datetime.now() - datetime.timedelta(days=int(ndays[0]))
        release_time = days_ago.strftime("%Y-%m-%d %H:%M:%S")

    elif "小时前" in release_time:
        nhours = re.compile("(\d+)\s*小时前").findall(release_time)
        hours_ago = datetime.datetime.now() - datetime.timedelta(hours=int(nhours[0]))
        release_time = hours_ago.strftime("%Y-%m-%d %H:%M:%S")

    elif "分钟前" in release_time:
        nminutes = re.compile("(\d+)\s*分钟前").findall(release_time)
        minutes_ago = datetime.datetime.now() - datetime.timedelta(
            minutes=int(nminutes[0])
        )
        release_time = minutes_ago.strftime("%Y-%m-%d %H:%M:%S")

    elif "前天" in release_time:
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=2)
        release_time = release_time.replace("前天", str(yesterday))

    elif "昨天" in release_time:
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        release_time = release_time.replace("昨天", str(yesterday))

    elif "今天" in release_time:
        release_time = release_time.replace("今天", get_current_date("%Y-%m-%d"))

    elif "刚刚" in release_time:
        release_time = get_current_date()

    elif re.search("^\d\d:\d\d", release_time):
        release_time = get_current_date("%Y-%m-%d") + " " + release_time

    elif not re.compile("\d{4}").findall(release_time):
        month = re.compile("\d{1,2}").findall(release_time)
        if month and int(month[0]) <= int(get_current_date("%m")):
            release_time = get_current_date("%Y") + "-" + release_time
        else:
            release_time = str(int(get_current_date("%Y")) - 1) + "-" + release_time

    # 把日和小时粘在一起的拆开
    template = re.compile("(\d{4}-\d{1,2}-\d{2})(\d{1,2})")
    release_time = re.sub(template, r"\1 \2", release_time)
    release_time = format_date(release_time, new_format=date_format)

    return release_time


def to_date(date_str, date_format="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.strptime(date_str, date_format)


def get_before_date(
    current_date,
    days,
    current_date_format="%Y-%m-%d %H:%M:%S",
    return_date_format="%Y-%m-%d %H:%M:%S",
):
    """
    @summary: 获取之前时间
    ---------
    @param current_date: 当前时间 str类型
    @param days: 时间间隔 -1 表示前一天 1 表示后一天
    @param days: 返回的时间格式
    ---------
    @result: 字符串
    """

    current_date = to_date(current_date, current_date_format)
    date_obj = current_date + datetime.timedelta(days=days)
    return datetime.datetime.strftime(date_obj, return_date_format)


def delay_time(sleep_time=60):
    """
    @summary: 睡眠  默认1分钟
    ---------
    @param sleep_time: 以秒为单位
    ---------
    @result:
    """

    time.sleep(sleep_time)


def format_seconds(seconds):
    """
    @summary: 将秒转为时分秒
    ---------
    @param seconds:
    ---------
    @result: 2天3小时2分49秒
    """

    seconds = int(seconds + 0.5)  # 向上取整

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    times = ""
    if d:
        times += "{}天".format(d)
    if h:
        times += "{}小时".format(h)
    if m:
        times += "{}分".format(m)
    if s:
        times += "{}秒".format(s)

    return times


################################################
def get_md5(*args):
    """
    @summary: 获取唯一的32位md5
    ---------
    @param *args: 参与联合去重的值
    ---------
    @result: 7c8684bcbdfcea6697650aa53d7b1405
    """

    m = hashlib.md5()
    for arg in args:
        m.update(str(arg).encode())

    return m.hexdigest()


def get_sha1(*args):
    """
    @summary: 获取唯一的40位值， 用于获取唯一的id
    ---------
    @param *args: 参与联合去重的值
    ---------
    @result: ba4868b3f277c8e387b55d9e3d0be7c045cdd89e
    """

    sha1 = hashlib.sha1()
    for arg in args:
        sha1.update(str(arg).encode())
    return sha1.hexdigest()  # 40位


def get_base64(data):
    if data is None:
        return data
    return base64.b64encode(str(data).encode()).decode("utf8")


def get_uuid(key1="", key2=""):
    """
    @summary: 计算uuid值
    可用于将两个字符串组成唯一的值。如可将域名和新闻标题组成uuid，形成联合索引
    ---------
    @param key1:str
    @param key2:str
    ---------
    @result:
    """

    uuid_object = ""

    if not key1 and not key2:
        uuid_object = uuid.uuid1()
    else:
        hash = md5(bytes(key1, "utf-8") + bytes(key2, "utf-8")).digest()
        uuid_object = uuid.UUID(bytes=hash[:16], version=3)

    return str(uuid_object)


def get_hash(text):
    return hash(text)


##################################################


def cut_string(text, length):
    """
    @summary: 将文本按指定长度拆分
    ---------
    @param text: 文本
    @param length: 拆分长度
    ---------
    @result: 返回按指定长度拆分后形成的list
    """

    text_list = re.findall(".{%d}" % length, text, re.S)
    leave_text = text[len(text_list) * length :]
    if leave_text:
        text_list.append(leave_text)

    return text_list


def get_random_string(length=1):
    random_string = "".join(random.sample(string.ascii_letters + string.digits, length))
    return random_string


def get_random_password(length=8, special_characters=""):
    """
    @summary: 创建随机密码 默认长度为8，包含大写字母、小写字母、数字
    ---------
    @param length: 密码长度 默认8
    @param special_characters: 特殊字符
    ---------
    @result: 指定长度的密码
    """

    while True:
        random_password = "".join(
            random.sample(
                string.ascii_letters + string.digits + special_characters, length
            )
        )
        if (
            re.search("[0-9]", random_password)
            and re.search("[A-Z]", random_password)
            and re.search("[a-z]", random_password)
        ):
            if not special_characters:
                break
            elif set(random_password).intersection(special_characters):
                break

    return random_password


def get_random_email(length=None, email_types: list = None, special_characters=""):
    """
    随机生成邮箱
    :param length: 邮箱长度
    :param email_types: 邮箱类型
    :param special_characters: 特殊字符
    :return:
    """
    if not length:
        length = random.randint(4, 12)
    if not email_types:
        email_types = [
            "qq.com",
            "163.com",
            "gmail.com",
            "yahoo.com",
            "hotmail.com",
            "yeah.net",
            "126.com",
            "139.com",
            "sohu.com",
        ]

    email_body = get_random_password(length, special_characters)
    email_type = random.choice(email_types)

    email = email_body + "@" + email_type
    return email


#################################


def dumps_obj(obj):
    return pickle.dumps(obj)


def loads_obj(obj_str):
    return pickle.loads(obj_str)


def get_method(obj, name):
    name = str(name)
    try:
        return getattr(obj, name)
    except AttributeError:
        log.error("Method %r not found in: %s" % (name, obj))
        return None


def switch_workspace(project_path):
    """
    @summary:
    ---------
    @param project_path:
    ---------
    @result:
    """

    os.chdir(project_path)  # 切换工作路经


############### 数据库相关 #######################
def format_sql_value(value):
    if isinstance(value, str):
        value = value.strip()

    elif isinstance(value, (list, dict)):
        value = dumps_json(value, indent=None)

    elif isinstance(value, (datetime.date, datetime.time)):
        value = str(value)

    elif isinstance(value, bool):
        value = int(value)

    return value


def list2str(datas):
    """
    列表转字符串
    :param datas: [1, 2]
    :return: (1, 2)
    """
    data_str = str(tuple(datas))
    data_str = re.sub(",\)$", ")", data_str)
    return data_str


def make_insert_sql(
    table, data, auto_update=False, update_columns=(), insert_ignore=False
):
    """
    @summary: 适用于mysql， oracle数据库时间需要to_date 处理（TODO）
    ---------
    @param table:
    @param data: 表数据 json格式
    @param auto_update: 使用的是replace into， 为完全覆盖已存在的数据
    @param update_columns: 需要更新的列 默认全部，当指定值时，auto_update设置无效，当duplicate key冲突时更新指定的列
    @param insert_ignore: 数据存在忽略
    ---------
    @result:
    """

    keys = ["`{}`".format(key) for key in data.keys()]
    keys = list2str(keys).replace("'", "")

    values = [format_sql_value(value) for value in data.values()]
    values = list2str(values)

    if update_columns:
        if not isinstance(update_columns, (tuple, list)):
            update_columns = [update_columns]
        update_columns_ = ", ".join(
            ["{key}=values({key})".format(key=key) for key in update_columns]
        )
        sql = (
            "insert%s into `{table}` {keys} values {values} on duplicate key update %s"
            % (" ignore" if insert_ignore else "", update_columns_)
        )

    elif auto_update:
        sql = "replace into `{table}` {keys} values {values}"
    else:
        sql = "insert%s into `{table}` {keys} values {values}" % (
            " ignore" if insert_ignore else ""
        )

    sql = sql.format(table=table, keys=keys, values=values).replace("None", "null")
    return sql


def make_update_sql(table, data, condition):
    """
    @summary: 适用于mysql， oracle数据库时间需要to_date 处理（TODO）
    ---------
    @param table:
    @param data: 表数据 json格式
    @param condition: where 条件
    ---------
    @result:
    """
    key_values = []

    for key, value in data.items():
        value = format_sql_value(value)
        if isinstance(value, str):
            key_values.append("`{}`={}".format(key, repr(value)))
        elif value is None:
            key_values.append("`{}`={}".format(key, "null"))
        else:
            key_values.append("`{}`={}".format(key, value))

    key_values = ", ".join(key_values)

    sql = "update `{table}` set {key_values} where {condition}"
    sql = sql.format(table=table, key_values=key_values, condition=condition)
    return sql


def make_batch_sql(
    table, datas, auto_update=False, update_columns=(), update_columns_value=()
):
    """
    @summary: 生产批量的sql
    ---------
    @param table:
    @param datas: 表数据 [{...}]
    @param auto_update: 使用的是replace into， 为完全覆盖已存在的数据
    @param update_columns: 需要更新的列 默认全部，当指定值时，auto_update设置无效，当duplicate key冲突时更新指定的列
    @param update_columns_value: 需要更新的列的值 默认为datas里边对应的值, 注意 如果值为字符串类型 需要主动加单引号， 如 update_columns_value=("'test'",)
    ---------
    @result:
    """
    if not datas:
        return

    keys = list(set([key for data in datas for key in data]))
    values_placeholder = ["%s"] * len(keys)

    values = []
    for data in datas:
        value = []
        for key in keys:
            current_data = data.get(key)
            current_data = format_sql_value(current_data)

            value.append(current_data)

        values.append(value)

    keys = ["`{}`".format(key) for key in keys]
    keys = list2str(keys).replace("'", "")

    values_placeholder = list2str(values_placeholder).replace("'", "")

    if update_columns:
        if not isinstance(update_columns, (tuple, list)):
            update_columns = [update_columns]
        if update_columns_value:
            update_columns_ = ", ".join(
                [
                    "`{key}`={value}".format(key=key, value=value)
                    for key, value in zip(update_columns, update_columns_value)
                ]
            )
        else:
            update_columns_ = ", ".join(
                ["`{key}`=values(`{key}`)".format(key=key) for key in update_columns]
            )
        sql = "insert into `{table}` {keys} values {values_placeholder} on duplicate key update {update_columns}".format(
            table=table,
            keys=keys,
            values_placeholder=values_placeholder,
            update_columns=update_columns_,
        )
    elif auto_update:
        sql = "replace into `{table}` {keys} values {values_placeholder}".format(
            table=table, keys=keys, values_placeholder=values_placeholder
        )
    else:
        sql = "insert ignore into `{table}` {keys} values {values_placeholder}".format(
            table=table, keys=keys, values_placeholder=values_placeholder
        )

    return sql, values


############### json相关 #######################


def key2underline(key: str, strict=True):
    """
    >>> key2underline("HelloWord")
    'hello_word'
    >>> key2underline("SHData", strict=True)
    's_h_data'
    >>> key2underline("SHData", strict=False)
    'sh_data'
    >>> key2underline("SHDataHi", strict=False)
    'sh_data_hi'
    >>> key2underline("SHDataHi", strict=True)
    's_h_data_hi'
    >>> key2underline("dataHi", strict=True)
    'data_hi'
    """
    regex = "[A-Z]*" if not strict else "[A-Z]"
    capitals = re.findall(regex, key)

    if capitals:
        for capital in capitals:
            if not capital:
                continue
            if key.startswith(capital):
                if len(capital) > 1:
                    key = key.replace(
                        capital, capital[:-1].lower() + "_" + capital[-1].lower(), 1
                    )
                else:
                    key = key.replace(capital, capital.lower(), 1)
            else:
                if len(capital) > 1:
                    key = key.replace(capital, "_" + capital.lower() + "_", 1)
                else:
                    key = key.replace(capital, "_" + capital.lower(), 1)

    return key.strip("_")


def key2hump(key):
    """
    下划线试变成首字母大写
    """
    return key.title().replace("_", "")


def format_json_key(json_data):
    json_data_correct = {}
    for key, value in json_data.items():
        key = key2underline(key)
        json_data_correct[key] = value

    return json_data_correct


def quick_to_json(text):
    """
    @summary: 可快速将浏览器上的header转为json格式
    ---------
    @param text:
    ---------
    @result:
    """

    contents = text.split("\n")
    json = {}
    for content in contents:
        if content == "\n":
            continue

        content = content.strip()
        regex = ["(:?.*?):(.*)", "(.*?):? +(.*)", "([^:]*)"]

        result = get_info(content, regex)
        result = result[0] if isinstance(result[0], tuple) else result
        try:
            json[result[0]] = eval(result[1].strip())
        except:
            json[result[0]] = result[1].strip()

    return json


##############################


def print_pretty(object):
    pprint(object)


def print_params2json(url):
    params_json = {}
    params = url.split("?")[-1].split("&")
    for param in params:
        key_value = param.split("=", 1)
        params_json[key_value[0]] = key_value[1]

    print(dumps_json(params_json))


def print_cookie2json(cookie_str_or_list):
    if isinstance(cookie_str_or_list, str):
        cookie_json = {}
        cookies = cookie_str_or_list.split("; ")
        for cookie in cookies:
            name, value = cookie.split("=")
            cookie_json[name] = value
    else:
        cookie_json = get_cookies_from_selenium_cookie(cookie_str_or_list)

    print(dumps_json(cookie_json))


###############################


def flatten(x):
    """flatten(sequence) -> list
    Returns a single, flat list which contains all elements retrieved
    from the sequence and all recursively contained sub-sequences
    (iterables).
    Examples:
    >>> [1, 2, [3,4], (5,6)]
    [1, 2, [3, 4], (5, 6)]
    >>> flatten([[[1,2,3], (42,None)], [4,5], [6], 7, (8,9,10)])
    [1, 2, 3, 42, None, 4, 5, 6, 7, 8, 9, 10]
    >>> flatten(["foo", "bar"])
    ['foo', 'bar']
    >>> flatten(["foo", ["baz", 42], "bar"])
    ['foo', 'baz', 42, 'bar']
    """
    return list(iflatten(x))


def iflatten(x):
    """iflatten(sequence) -> iterator
    Similar to ``.flatten()``, but returns iterator instead"""
    for el in x:
        if _is_listlike(el):
            for el_ in flatten(el):
                yield el_
        else:
            yield el


def _is_listlike(x):
    """
    >>> _is_listlike("foo")
    False
    >>> _is_listlike(5)
    False
    >>> _is_listlike(b"foo")
    False
    >>> _is_listlike([b"foo"])
    True
    >>> _is_listlike((b"foo",))
    True
    >>> _is_listlike({})
    True
    >>> _is_listlike(set())
    True
    >>> _is_listlike((x for x in range(3)))
    True
    >>> _is_listlike(six.moves.xrange(5))
    True
    """
    return hasattr(x, "__iter__") and not isinstance(x, (six.text_type, bytes))


###################


def re_def_supper_class(obj, supper_class):
    """
    重新定义父类
    @param obj: 类 如 class A: 则obj为A 或者 A的实例 a.__class__
    @param supper_class: 父类
    @return:
    """
    obj.__bases__ = (supper_class,)


###################
freq_limit_record = {}


def reach_freq_limit(rate_limit, *key):
    """
    频率限制
    :param rate_limit: 限制时间 单位秒
    :param key: 频率限制的key
    :return: True / False
    """
    if rate_limit == 0:
        return False

    msg_md5 = get_md5(*key)
    key = "rate_limit:{}".format(msg_md5)
    try:
        if get_redisdb().strget(key):
            return True

        get_redisdb().strset(key, time.time(), ex=rate_limit)
    except redis.exceptions.ConnectionError as e:
        # 使用内存做频率限制
        global freq_limit_record

        if key not in freq_limit_record:
            freq_limit_record[key] = time.time()
            return False

        if time.time() - freq_limit_record.get(key) < rate_limit:
            return True
        else:
            freq_limit_record[key] = time.time()

    return False


def dingding_warning(
    message, message_prefix=None, rate_limit=None, url=None, user_phone=None
):
    # 为了加载最新的配置
    rate_limit = rate_limit if rate_limit is not None else setting.WARNING_INTERVAL
    url = url or setting.DINGDING_WARNING_URL
    user_phone = user_phone or setting.DINGDING_WARNING_PHONE

    if not all([url, message]):
        return

    if reach_freq_limit(rate_limit, url, user_phone, message_prefix or message):
        log.info("报警时间间隔过短，此次报警忽略。 内容 {}".format(message))
        return

    if isinstance(user_phone, str):
        user_phone = [user_phone] if user_phone else []

    data = {
        "msgtype": "text",
        "text": {"content": message},
        "at": {"atMobiles": user_phone, "isAtAll": setting.DINGDING_WARNING_ALL},
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            url, headers=headers, data=json.dumps(data).encode("utf8")
        )
        result = response.json()
        response.close()
        if result.get("errcode") == 0:
            return True
        else:
            raise Exception(result.get("errmsg"))
    except Exception as e:
        log.error("报警发送失败。 报警内容 {}, error: {}".format(message, e))
        return False


def email_warning(
    message,
    title,
    message_prefix=None,
    email_sender=None,
    email_password=None,
    email_receiver=None,
    email_smtpserver=None,
    rate_limit=None,
):
    # 为了加载最新的配置
    email_sender = email_sender or setting.EMAIL_SENDER
    email_password = email_password or setting.EMAIL_PASSWORD
    email_receiver = email_receiver or setting.EMAIL_RECEIVER
    email_smtpserver = email_smtpserver or setting.EMAIL_SMTPSERVER
    rate_limit = rate_limit if rate_limit is not None else setting.WARNING_INTERVAL

    if not all([message, email_sender, email_password, email_receiver]):
        return

    if reach_freq_limit(
        rate_limit, email_receiver, email_sender, message_prefix or message
    ):
        log.info("报警时间间隔过短，此次报警忽略。 内容 {}".format(message))
        return

    if isinstance(email_receiver, str):
        email_receiver = [email_receiver]

    with EmailSender(
        username=email_sender, password=email_password, smtpserver=email_smtpserver
    ) as email:
        return email.send(receivers=email_receiver, title=title, content=message)


def linkedsee_warning(message, rate_limit=3600, message_prefix=None, token=None):
    """
    灵犀电话报警
    Args:
        message:
        rate_limit:
        message_prefix:
        token:

    Returns:

    """
    if not token:
        log.info("未设置灵犀token，不支持报警")
        return

    if reach_freq_limit(rate_limit, token, message_prefix or message):
        log.info("报警时间间隔过短，此次报警忽略。 内容 {}".format(message))
        return

    headers = {"servicetoken": token, "Content-Type": "application/json"}

    url = "http://www.linkedsee.com/alarm/zabbix"

    data = {"content": message}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response


def wechat_warning(
    message,
    message_prefix=None,
    rate_limit=None,
    url=None,
    user_phone=None,
    all_users: bool = None,
):
    """企业微信报警"""

    # 为了加载最新的配置
    rate_limit = rate_limit if rate_limit is not None else setting.WARNING_INTERVAL
    url = url or setting.WECHAT_WARNING_URL
    user_phone = user_phone or setting.WECHAT_WARNING_PHONE
    all_users = all_users if all_users is not None else setting.WECHAT_WARNING_ALL

    if isinstance(user_phone, str):
        user_phone = [user_phone] if user_phone else []

    if all_users is True or not user_phone:
        user_phone = ["@all"]

    if not all([url, message]):
        return

    if reach_freq_limit(rate_limit, url, user_phone, message_prefix or message):
        log.info("报警时间间隔过短，此次报警忽略。 内容 {}".format(message))
        return

    data = {
        "msgtype": "text",
        "text": {"content": message, "mentioned_mobile_list": user_phone},
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            url, headers=headers, data=json.dumps(data).encode("utf8")
        )
        result = response.json()
        response.close()
        if result.get("errcode") == 0:
            return True
        else:
            raise Exception(result.get("errmsg"))
    except Exception as e:
        log.error("报警发送失败。 报警内容 {}, error: {}".format(message, e))
        return False


def feishu_warning(message, message_prefix=None, rate_limit=None, url=None, user=None):
    """

    Args:
        message:
        message_prefix:
        rate_limit:
        url:
        user: {"open_id":"ou_xxxxx", "name":"xxxx"} 或 [{"open_id":"ou_xxxxx", "name":"xxxx"}]

    Returns:

    """
    # 为了加载最新的配置
    rate_limit = rate_limit if rate_limit is not None else setting.WARNING_INTERVAL
    url = url or setting.FEISHU_WARNING_URL
    user = user or setting.FEISHU_WARNING_USER

    if not all([url, message]):
        return

    if reach_freq_limit(rate_limit, url, user, message_prefix or message):
        log.info("报警时间间隔过短，此次报警忽略。 内容 {}".format(message))
        return

    if isinstance(user, dict):
        user = [user] if user else []

    at = ""
    if setting.FEISHU_WARNING_ALL:
        at = '<at user_id="all">所有人</at>'
    elif user:
        at = " ".join(
            [f'<at user_id="{u.get("open_id")}">{u.get("name")}</at>' for u in user]
        )

    data = {"msg_type": "text", "content": {"text": at + message}}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            url, headers=headers, data=json.dumps(data).encode("utf8")
        )
        result = response.json()
        response.close()
        if result.get("StatusCode") == 0:
            return True
        else:
            raise Exception(result.get("msg"))
    except Exception as e:
        log.error("报警发送失败。 报警内容 {}, error: {}".format(message, e))
        return False


def send_msg(msg, level="DEBUG", message_prefix=""):
    if setting.WARNING_LEVEL == "ERROR":
        if level.upper() != "ERROR":
            return

    if setting.DINGDING_WARNING_URL:
        keyword = "feapder报警系统\n"
        dingding_warning(keyword + msg, message_prefix=message_prefix)

    if setting.EMAIL_RECEIVER:
        title = message_prefix or msg
        if len(title) > 50:
            title = title[:50] + "..."
        email_warning(msg, message_prefix=message_prefix, title=title)

    if setting.WECHAT_WARNING_URL:
        keyword = "feapder报警系统\n"
        wechat_warning(keyword + msg, message_prefix=message_prefix)

    if setting.FEISHU_WARNING_URL:
        keyword = "feapder报警系统\n"
        feishu_warning(keyword + msg, message_prefix=message_prefix)


###################


def make_item(cls, data: dict):
    """提供Item类与原数据，快速构建Item实例
    :param cls: Item类
    :param data: 字典格式的数据
    """
    item = cls()
    for key, val in data.items():
        setattr(item, key, val)
    return item


###################


def aio_wrap(loop=None, executor=None):
    """
    wrap a normal sync version of a function to an async version
    """
    outer_loop = loop
    outer_executor = executor

    def wrap(fn):
        @wraps(fn)
        async def run(*args, loop=None, executor=None, **kwargs):
            if loop is None:
                if outer_loop is None:
                    loop = asyncio.get_event_loop()
                else:
                    loop = outer_loop
            if executor is None:
                executor = outer_executor
            pfunc = partial(fn, *args, **kwargs)
            return await loop.run_in_executor(executor, pfunc)

        return run

    return wrap


######### number ##########


def ensure_int(n):
    """
    >>> ensure_int(None)
    0
    >>> ensure_int(False)
    0
    >>> ensure_int(12)
    12
    >>> ensure_int("72")
    72
    >>> ensure_int('')
    0
    >>> ensure_int('1')
    1
    """
    if not n:
        return 0
    return int(n)


def ensure_float(n):
    """
    >>> ensure_float(None)
    0.0
    >>> ensure_float(False)
    0.0
    >>> ensure_float(12)
    12.0
    >>> ensure_float("72")
    72.0
    """
    if not n:
        return 0.0
    return float(n)


def import_cls(cls_info):
    module, class_name = cls_info.rsplit(".", 1)
    cls = importlib.import_module(module).__getattribute__(class_name)
    return cls
