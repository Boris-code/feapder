# -*- coding: utf-8 -*-
"""
Created on 2018-07-26 11:40:28
---------
@summary:
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import datetime
import os
import re
import time
from urllib.parse import urlparse, urlunparse, urljoin

from bs4 import UnicodeDammit
from requests.cookies import RequestsCookieJar
from requests.models import Response as res

from feapder.network.selector import Selector
from feapder.utils.log import log
from feapder.utils.tools import is_have_chinese, http_content_type_encoding, html_body_declared_encoding, memoizemethod_noargs

FAIL_ENCODING = "ISO-8859-1"

# html 源码中的特殊字符，需要删掉，否则会影响etree的构建
SPECIAL_CHARACTERS = [
    "[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]"  # 移除控制字符 全部字符列表 https://zh.wikipedia.org/wiki/%E6%8E%A7%E5%88%B6%E5%AD%97%E7%AC%A6
]

SPECIAL_CHARACTER_PATTERNS = [
    re.compile(special_character) for special_character in SPECIAL_CHARACTERS
]


class Response(res):
    def __init__(self, response):
        super(Response, self).__init__()
        self.__dict__.update(response.__dict__)

        self._cached_selector = None
        self._cached_text = None
        self._cached_json = None
        self._encoding = None

        self.code = None
        self.encoding_errors = "strict"  # strict / replace / ignore

    @classmethod
    def from_dict(cls, response_dict):
        """
        利用字典获取Response对象
        @param response_dict: 原生的response.__dict__
        @return:
        """
        cookie_jar = RequestsCookieJar()
        cookie_jar.update(other=response_dict["cookies"])
        response_dict["cookies"] = cookie_jar

        response_dict["elapsed"] = datetime.timedelta(
            0, 0, response_dict["elapsed"]
        )  # 耗时
        response_dict["connection"] = None
        response_dict["_content_consumed"] = True

        response = res()
        response.__dict__.update(response_dict)
        return cls(response)

    @property
    def to_dict(self):
        response_dict = {
            "_content": self.content,
            "cookies": self.cookies.get_dict(),
            "encoding": self.encoding,
            "headers": self.headers,
            "status_code": self.status_code,
            "elapsed": self.elapsed.microseconds,  # 耗时
            "url": self.url,
        }

        return response_dict

    def __setattr__(self, key, value):
        if key == "code":
            if not self.__dict__.get("custom_text"):
                self.__dict__["_cached_selector"] = None
                self.__dict__["_cached_text"] = None
                self.__dict__["_cached_json"] = None
            self.__dict__[key] = value

        elif key == "text":
            self.__dict__["_cached_text"] = value
            self.__dict__["_cached_selector"] = None
            self.__dict__["custom_text"] = True

        elif key == "json":
            self.__dict__["_cached_json"] = value
            self.__dict__["custom_text"] = True

        else:
            self.__dict__[key] = value

    @property
    def encoding(self):
        """
            @author: artio
        :return:
        """
        return self._encoding or \
               self._headers_encoding() or \
               self._body_declared_encoding() or \
               self.apparent_encoding

    @encoding.setter
    def encoding(self, val):
        self._encoding = val

    @memoizemethod_noargs
    def _headers_encoding(self):
        """
            从headers获取头部charset编码
            解析charset借鉴的scrapy
            application/json 逻辑借鉴了requests.encoding逻辑
        :return:
        """
        content_type = self.headers.get('Content-Type', '') or self.headers.get('content-type', '')
        return http_content_type_encoding(content_type) or 'utf-8' if 'application/json' in content_type else None

    @memoizemethod_noargs
    def _body_declared_encoding(self):
        """
            从html xml等获取<meta charset="编码">
            借鉴的scrapy
        :return:
        """

        return html_body_declared_encoding(self.content)

    def _get_html(self):
        if self.encoding != FAIL_ENCODING:
            # return response as a unicode string
            # html = super(Response, self).text
            html = self.__text

        else:
            # don't attempt decode, return response in bytes
            html = self.content
            html = self._get_unicode_html(html)
            if not is_have_chinese(html):
                self.encoding = "gb2312"
                html = self.text

        return html or ""

    def _get_unicode_html(self, html):
        if isinstance(html, str):
            return html

        if not html:
            return html

        converted = UnicodeDammit(html, is_html=True)
        if not converted.unicode_markup:
            raise Exception(
                "Failed to detect encoding of article HTML, tried: %s"
                % ", ".join(converted.tried_encodings)
            )

        html = converted.unicode_markup
        return html

    def _make_absolute(self, link):
        """Makes a given link absolute."""
        try:

            link = link.strip()

            # Parse the link with stdlib.
            parsed = urlparse(link)._asdict()

            # If link is relative, then join it with base_url.
            if not parsed["netloc"]:
                return urljoin(self.url, link)

            # Link is absolute; if it lacks a scheme, add one from base_url.
            if not parsed["scheme"]:
                parsed["scheme"] = urlparse(self.url).scheme

                # Reconstruct the URL to incorporate the new scheme.
                parsed = (v for v in parsed.values())
                return urlunparse(parsed)

        except Exception as e:
            log.error(
                "Invalid URL <{}> can't make absolute_link. exception: {}".format(
                    link, e
                )
            )

        # Link is absolute and complete with scheme; nothing to be done here.
        return link

    def _absolute_links(self, text):
        regexs = [
            r'(<(?i)a.*?href\s*?=\s*?["\'])(.+?)(["\'])',  # a
            r'(<(?i)img.*?src\s*?=\s*?["\'])(.+?)(["\'])',  # img
            r'(<(?i)link.*?href\s*?=\s*?["\'])(.+?)(["\'])',  # css
            r'(<(?i)script.*?src\s*?=\s*?["\'])(.+?)(["\'])',  # js
        ]

        for regex in regexs:

            def replace_href(text):
                # html = text.group(0)
                link = text.group(2)
                absolute_link = self._make_absolute(link)

                # return re.sub(regex, r'\1{}\3'.format(absolute_link), html) # 使用正则替换，个别字符不支持。如该网址源代码http://permit.mep.gov.cn/permitExt/syssb/xxgk/xxgk!showImage.action?dataid=0b092f8115ff45c5a50947cdea537726
                return text.group(1) + absolute_link + text.group(3)

            text = re.sub(regex, replace_href, text, flags=re.S)

        return text

    def _del_special_character(self, text):
        """
        删除特殊字符
        """
        for special_character_pattern in SPECIAL_CHARACTER_PATTERNS:
            text = special_character_pattern.sub("", text)

        return text

    @property
    def __text(self):
        """Content of the response, in unicode.

        If Response.encoding is None, encoding will be guessed using
        ``chardet``.

        The encoding of the response content is determined based solely on HTTP
        headers, following RFC 2616 to the letter. If you can take advantage of
        non-HTTP knowledge to make a better guess at the encoding, you should
        set ``r.encoding`` appropriately before accessing this property.
        """

        # Try charset from content-type
        content = None
        encoding = self.encoding

        if not self.content:
            return str("")

        # Fallback to auto-detected encoding.
        if self.encoding is None:
            encoding = self.apparent_encoding

        # Decode unicode from given encoding.
        try:
            content = str(self.content, encoding, errors=self.encoding_errors)
        except (LookupError, TypeError):
            # A LookupError is raised if the encoding was not found which could
            # indicate a misspelling or similar mistake.
            #
            # A TypeError can be raised if encoding is None
            #
            # So we try blindly encoding.
            content = str(self.content, errors=self.encoding_errors)

        return content

    @property
    def text(self):
        if self._cached_text is None:
            if self.code:
                self.encoding = self.code
                # self._cached_text = super(Response, self).text
                self._cached_text = self.__text

            else:
                self._cached_text = self._get_html()

            self._cached_text = self._absolute_links(self._cached_text)
            self._cached_text = self._del_special_character(self._cached_text)

        return self._cached_text

    @property
    def json(self, **kwargs):
        if self._cached_json is None:
            self.encoding = self.code or "utf-8"
            self._cached_json = super(Response, self).json(**kwargs)

        return self._cached_json

    @property
    def content(self):
        content = super(Response, self).content
        return content

    @property
    def is_html(self):
        content_type = self.headers.get("Content-Type", "")
        if "text/html" in content_type:
            return True
        else:
            return False

    @property
    def selector(self):
        if self._cached_selector is None:
            self._cached_selector = Selector(self.text)
        return self._cached_selector

    def extract(self):
        return self.selector.get()

    def xpath(self, query, **kwargs):
        return self.selector.xpath(query, **kwargs)

    def css(self, query):
        return self.selector.css(query)

    def re(self, regex, replace_entities=False):
        """
        @summary: 正则匹配
        注意：网页源码<a class='page-numbers'...  会被处理成<a class="page-numbers" ； 写正则时要写<a class="(.*?)"。 但不会改非html的文本引号格式
        为了使用方便，正则单双引号自动处理为不敏感
        ---------
        @param regex: 正则或者re.compile
        @param replace_entities: 为True时 去掉&nbsp;等字符， 转义&quot;为 " 等， 会使网页结构发生变化。如在网页源码中提取json， 建议设置成False
        ---------
        @result: 列表
        """

        # 将单双引号设置为不敏感
        if isinstance(regex, str):
            regex = re.sub("['\"]", "['\"]", regex)

        return self.selector.re(regex, replace_entities)

    def re_first(self, regex, default=None, replace_entities=False):
        """
        @summary: 正则匹配
        注意：网页源码<a class='page-numbers'...  会被处理成<a class="page-numbers" ； 写正则时要写<a class="(.*?)"。 但不会改非html的文本引号格式
        为了使用方便，正则单双引号自动处理为不敏感
        ---------
        @param regex: 正则或者re.compile
        @param default: 未匹配到， 默认值
        @param replace_entities: 为True时 去掉&nbsp;等字符， 转义&quot;为 " 等， 会使网页结构发生变化。如在网页源码中提取json， 建议设置成False
        ---------
        @result: 第一个值或默认值
        """

        # 将单双引号设置为不敏感
        if isinstance(regex, str):
            regex = re.sub("['\"]", "['\"]", regex)

        return self.selector.re_first(regex, default, replace_entities)

    def __del__(self):
        self.close()

    def open(self, delete_temp_file=False):
        with open(
            "temp.html", "w", encoding=self.code or self.encoding, errors="replace"
        ) as html:
            self.encoding_errors = "replace"
            html.write(self.text)

        os.system("open temp.html")

        if delete_temp_file:
            time.sleep(1)
            os.remove("temp.html")
