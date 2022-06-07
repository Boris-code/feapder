# -*- coding: utf-8 -*-
"""
Created on 2021/3/4 11:26 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from feapder import Request, Response


def test_selector():
    request = Request("https://www.baidu.com?a=1&b=2", data={}, params=None)
    response = request.get_response()
    print(response)

    print(response.xpath("//a/@href"))
    print(response.css("a::attr(href)"))
    print(response.css("a::attr(href)").extract_first())

    content = response.re("<a.*?href='(.*?)'")
    print(content)


def test_from_text():
    text = """    <script src="./lib/docsify/lib/docsify.min.js"></script>
        <script src="./lib/docsify/lib/plugins/ga.js"></script>
        <script src="./lib/docsify/lib/plugins/search.js"></script>
        <script src="./lib/docsify-copy-code/dist/docsify-copy-code.min.js"></script>
        <script src="./lib/prismjs/components/prism-bash.js"></script>
        <script src="./lib/prismjs/components/prism-java.js"></script>
        <script src="./lib/prismjs/components/prism-sql.js"></script>
        <script src="./lib/prismjs/components/prism-yaml.js"></script>
        <script src="./lib/prismjs/components/prism-python.js"></script>
        <script src="//cdn.jsdelivr.net/npm/docsify/lib/plugins/zoom-image.min.js"></script>"""

    resp = Response.from_text(text=text, url="http://feapder.com/#/README")
    print(resp.text)
    print(resp)
    print(resp.xpath("//script"))
