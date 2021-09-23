# FEAPLAT使用说明

## 首次运行须知

1. 管理系统默认账号密码：admin / admin

2. 进入系统后，先到设置页面，配置服务端内网地址：

    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16318826920098.jpg)


    查看内网地址：
    
    ```shell
    ifconfig
    ```
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16255025919847.jpg)

## 添加项目

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16318800747189.jpg)

1. 使用git方式上传项目时，需要使用SSH协议，若拉取私有项目，可在feapder的设置页面添加 SSH 密钥。使用git方式，每次运行前会拉取默认分支最新的代码
2. 项目会被放到爬虫`worker`容器的根目录下 即 `/项目`
3. 工作路径：是指你的项目路径，比如下面的项目结构：
    
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/13/16315322995977.jpg)
    
    工作路径为 `/spider-project`，feaplat会把这个工作路径加到环境变量，同时会进入到这个目录，后续的代码执行命令都是在这个路径下运行的 
    
1. requirements.txt：用于安装依赖包，填写依赖包的绝对路径

## 运行

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16318807243830.jpg)

1. 启动命令：启动命令是在您添加项目时配置的工作路径下执行的
2. 定时类型：
    1. cron：crontab表达式，参考：https://tool.lu/crontab/
    2. interval：时间间隔
    3. date：指定日期
    4. once：立即运行，且只运行一次

## 爬虫监控

> 若您使用的是feapder爬虫或者使用了自定义打点，监控才会有对应的数据

1. 表名：以 task_id 命名
2. 保留策略：这是influxdb的概念，监控数据默认保留180天，滚动更新，这个保留策略为`feapder_180d`，同时也被设置成了默认策略`default`。所以直接用`default`就可以。

## 系统设置

1. GIT_SSH_PRIVATE_KEY：可以在自己的笔记本上使用`cat .ssh/id_rsa`查看，然后把内容复制到进来。不了解git ssh协议的，自行查资料