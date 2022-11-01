# setting不生效问题

## 问题

以下面这个项目结构为例，在`spiders`目录下运行`spider_test.py`读取不到`setting.py`，所以`setting`的配置不生效。

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/11/01/16672715088563.jpg)

读取不到是因为python的环境变量问题，在spiders目录下运行，只会找spides目录下的文件

## 解决方式

### 方法1：在setting同级目录下运行

在main.py中导入spider_test， 然后运行main.py

### 方法2：设置工作区间

设置工作区间方式（以pycharm为例）：项目->右键->Mark Directory as -> Sources Root

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/11/01/16672717483410.jpg)

### 方法3：设置PYTHONPATH

以mac或linux举例，执行如下命令

```shell
export PYTHONPATH=$PYTHONPATH:/绝对路径/spider-project
```
注：这个命令设置的环境变量只在当前终端有效

然后即可在spiders目录下运行

```shell
python spider_test.py
```

window如何添加环境变量大家自行探索，搞定了可在评论区留言