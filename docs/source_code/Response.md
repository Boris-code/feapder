

# Response

Response 对 requests 返回的response进行了封装，因此支持response所有方法

## 功能点

### 1. 智能解码

Response 对返回的文本进行了智能解码，可解决绝大多数乱码问题

### 2. 智能转为绝对连接

若网页源码里的连接是相对连接，会自动转为绝对连接

### 3. 支持xpath选择器

例如：

定位a标签连接，返回SelectorList
```python
response.xpath("//a/@href")
```

取第一个连接文本

```python
response.xpath("//a/@href").extract_first()
```

取全部连接文本列表
```python
response.xpath("//a/@href").extract()
```

### 4. 支持css选择器

例如：

定位a标签连接，返回SelectorList
```python
response.css("a::attr(href)")
```

取第一个连接文本

```python
response.css("a::attr(href)").extract_first()
```

取全部连接文本列表
```python
response.css("a::attr(href)").extract()
```

### 5. 支持正则

获取全部
```python
def re(self, regex, replace_entities=False):
    """
    @summary: 正则匹配
    ---------
    @param regex: 正则或者re.compile
    @param replace_entities: 为True时 去掉&nbsp;等字符， 转义&quot;为 " 等， 会使网页结构发生变化。如在网页源码中提取json， 建议设置成False
    ---------
    @result: 列表
    """
```

获取第一个
```python
def re_first(self, regex, default=None, replace_entities=False):
    """
    @summary: 正则匹配
    ---------
    @param regex: 正则或者re.compile
    @param default: 未匹配到， 默认值
    @param replace_entities: 为True时 去掉&nbsp;等字符， 转义&quot;为 " 等， 会使网页结构发生变化。如在网页源码中提取json， 建议设置成False
    ---------
    @result: 第一个值或默认值
    """
```

例如获取全部连接：

```
response.re("<a.*?href='(.*?)'")
```

### 6. 支持BeautifulSoup

默认的features为`html.parser`

```python
def bs4(self, features="html.parser"):
    pass
```

例如获取标题：

```python
response.bs4().title
```


### 7. 定位混用

xpath、css两种定位方式可混用，如：

```
response.css("a").xpath("./@href").extract()
```

### 8. 取文本

取文本有两种方式

方式1：这种直接取的源码

```
response.text
```

方式2：这种会将源码转为dom树，然后获取转换之后的文本

```
response.extract()
```

如：网页源码`<a class='page-numbers'...`  会被处理成`<a class="page-numbers"`

### 9. 取json

```
response.json
```

### 10. 查看下载内容

```
response.open()
```

这个函数会打开浏览器，渲染下载内容，方便查看下载内容是否与数据源一致

### 11. 更新response.text的值

```
response.text = ""
```
常用于浏览器渲染模式，如页面有变化，可以取最新的页面内容更新到response.text里，然后使用response的选择器提取内容

### 12. 将普通response转为feapder.Response

```
response = feapder.Response(response)
```

### 13. 将源码转为feapder.Response

```
response = feapder.Response.from_text(text=html, url="", cookies={}, headers={})
```

url是网页的地址，用来将html里的链接转为绝对链接，若不提供，则无法转换

示例：
```
import feapder

html = "<a href='/666'>hello word</a>"
response = feapder.Response.from_text(text=html, url="https://www.feapder.com", cookies={}, headers={})
print(response.xpath("//a/@href").extract_first())

输出：https://www.feapder.com/666
```

### 14. 序列化与反序列化

序列化 

    response_dict = response.to_dict

反序列化 

    feapder.Response.from_dict(response_dict)
    

### 其他

其他方法与requests的response一致，但有如下差异

## 差异

feapder.Response 与 requests的response有以下几点差异，使用时需要注意

### 1. json方法

获取json数据时，常规的response写法如下：

```
response.json()
```

feapder.Response写法如下

```
response.json
```

做到了与response.text使用方式保持一致

### 2. 设置编码

常规的response写法如下：

```
response.enconding="utf-8"
```

feapder.Response写法如下
```
response.code="utf-8"
```
做了简化，不过`response.enconding`也支持

### 3. 解码方式(二进制转字符串方式)


解码方式有3种 `strict`、`replace`、`ignore`

1. strict：严格模式，一旦有某个字符解不出来，就会报错
2. replace：替换模式，某个字符解不出来时，替换为乱码字符
3. ignore：忽略模式，某个字符解不出来时，忽略这个字符

例如：

```shell
>>>content = b'\xe4\x3f\xa0\xe5\xa5\xbd'
>>>str(content, errors='replace')
'�?�好'
>>>str(content, errors='strict')
Traceback (most recent call last):
  File "/Users/Boris/workspace/feapder/venv2/lib/python3.6/site-packages/IPython/core/interactiveshell.py", line 3343, in run_code
    exec(code_obj, self.user_global_ns, self.user_ns)
  File "<ipython-input-11-a129a2aa6283>", line 1, in <module>
    str(content, errors='strict')
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe4 in position 0: invalid continuation byte
>>>str(content, errors='ignore')
'?好'
```

常规的response在解码时，使用了`replace`模式，这样会导致数据中可能混杂着乱码，我们不能及时发现.

feapder.Response默认使用了`strict`默认，一旦某个字符解析失败，就会抛异常，防止乱码混入。然后通过人工指定编码，解决乱码问题。

若想修改feapder.Response的解码方式，可通过如下方式指定

```
response.encoding_errors = "strict"  # strict / replace / ignore
```


