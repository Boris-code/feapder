
# tools

`feapder.utils.tools`里封装了爬虫中常用的函数，目前共计**129**个，可通过阅读源码了解使用

## 举例

### 时间格式化

```python
from feapder.utils import tools

time = "昨天"

date = tools.format_time(time)
assert date == "2021-03-15 00:00:00"
```
