## pr说明：
### 1、修改说明：
1.1、修改./templates/project_template/setting.py中第62行，
```python
# 原内容为：
custom_argument=["--ignore-certificate-errors"],  # 自定义浏览器渲染参数

# 修改后内容为：
custom_argument=["--ignore-certificate-errors", "--disable-blink-features=AutomationControlled"],  # 自定义浏览器渲染参数
```
1.2、替换stealth.min.js文件为最新文件，2022年4月24日生成；

### 2、修改原因：
　　Chrome 88版本及以后，单纯使用stealth.min.js文件已无法隐藏window.navigator.webdriver标识，在浏览器中会被对应检测到；

### 3、修改前后比对：
#### 3.1、下方为仅使用stealth.min.js文件时的情况：
**sannysoft网站检测情况：**
　　setting中未增加渲染参数前，使用https://bot.sannysoft.com网站检测时参数如下：
![](https://tva1.sinaimg.cn/large/e6c9d24ely1h1m066g8xrj21060u0tcy.jpg)

**浏览器内JS检查参数如下：**
![](https://tva1.sinaimg.cn/large/e6c9d24ely1h1m04xug60j21400d8dhj.jpg)

**使用示例网站七麦数据访问时效果如下（自动跳转404）：**
![](https://tva1.sinaimg.cn/large/e6c9d24ely1h1m0fhkzldj215v0u0mxw.jpg)
#### 3.2、下方为增加浏览器渲染参数后使用情况：
**sannysoft网站检测情况：**
　　setting中未增加渲染参数前，使用https://bot.sannysoft.com网站检测、以及JS检测时参数如下：
![](https://tva1.sinaimg.cn/large/e6c9d24ely1h1m0e5whaij21200u0aft.jpg)

**使用示例网站七麦数据访问时效果如下（可正常访问）：**
![](https://tva1.sinaimg.cn/large/e6c9d24ely1h1m0f6clrnj214h0u0dl8.jpg)
