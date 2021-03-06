# BatchParser

BaseParser为BatchSpider的基类，用来定义任务下发与数据解析，是面向用户提供的接口

除了提供[BaseParser](source_code/BaseParser)所有接口外，还提供以下方法

## 方法详解

### 1. 添加任务 add_task

add_task, 每次执行start_monitor都会调用，且在init_task之前调用, 用于在批次爬虫启动前添加任务到数据库

```
class TestSpider(feapder.BatchSpider):
    def add_task(self):
        pass
```

### 2. 更新任务

#### 方法一：

一条条更新

```python
def update_task_state(self, task_id, state=1, **kwargs):
    """
    @summary: 更新任务表中任务状态，做完每个任务时代码逻辑中要主动调用
    调用方法为 yield lambda : self.update_task_state(task_id, state)
    ---------
    @param task_id: 任务id
    @param state: 任务状态
    ---------
    @result:
    """
```

举例说明

```
def parse(self, request, response):
    yield item  # 返回item， item会自动批量入库
    yield lambda : self.update_task_state(request.task_id, 1)
```

 在`yield item`后，调用`self.update_task_state`函数实现任务状态更新。
 
 这里为什么使用`yield lambda`方式呢？因为`yield item`后，item不会马上入库，会存在一个buffer中，批量入库，如果我们直接调用`self.update_task_state`更新任务状态，可能这时item还并未入库，如果此时程序意外退出，那么缓存中的这一部分item数据将会丢失，但是此时任务状态已更新，任务不会重做，这便会导致这个任务所对应的数据丢失
 
 `yield lambda`返回的是一个回调函数，这个函数并不会马上执行，系统会保证item入库后再执行，因此这么写的用意在于item入库后再更新任务状态
 
#### 方法二：

批量更新

```python
def update_task_batch(self, task_id, state=1, **kwargs):
    """
    批量更新任务 多处调用，更新的字段必须一致
    注意：需要 写成 yield update_task_batch(...) 否则不会更新
    @param task_id:
    @param state:
    @param kwargs:
    @return:
    """
```

举例说明

```python
def parse(self, request, response):
    yield item  # 返回item， item会自动批量入库
    yield self.update_task_batch(request.task_id, 1) # 更新任务状态为1
```

在`yield item`后调用`self.update_task_batch`实现批量更新

注意，批量更新必须使用 `yield`, 因为`update_task_batch`函数并未实现更新逻辑，只是返回了`UpdateItem`， `UpdateItem`与`Item`类似，只不过带有更新功能，框架会在Item入库后在调用`UpdateItem`实现批量更新。关于`UpdateItem`详解，请参考[UpdateItem]()

#### 两种方式选取

同一张表，若更新字段相同，推荐使用批量更新的方式，效率更高，若字段不同，用一条条更新的方式。因为批量更新，这一批的更新字段必须一致

比如当请求失败时，将任务更新为-1，同时标记失败原因，成功时将任务更新为1，写法如下：

```python
def parse(self, request, response):
    yield self.update_task_batch(request.task_id, 1) # 更新任务状态为1

def failed_request(self, request, response):
    """
    @summary: 超过最大重试次数的request
    ---------
    @param request:
    ---------
    @result: request / item / callback / None (返回值必须可迭代)
    """

    yield request
    yield lambda : self.update_task_state(request.task_id, -1, remark="失败原因") # 更新任务状态为-1
```

因任务失败时多更新了个remark字段，与任务成功时只更新state字段不同，因此需要将此更新操作单独拆出来，用`update_task_state`方式更新

### 3. 获取批次时间

示例：

    def parse(self, request, response):
        item = SpiderDataItem()  # 声明一个item
        item.batch_data = self.batch_date
        item.title = title  # 给item属性赋值
        yield item  # 返回item， item会自动批量入库
        
使用`self.batch_date`可获取当前批次时间，然后拼接到item入库

数据示例

| id | title | batch_date |
| --- | --- | --- |
| 1 | 百度一下 | 2021-01-01 |