# FEAPLAT使用说明

## 首次运行须知

1. 管理系统默认账号密码：admin / admin

## 添加项目

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16318800747189.jpg)

1. 使用git方式上传项目时，需要使用SSH协议，若拉取私有项目，可在feaplat的设置页面添加 SSH 密钥。使用git方式，每次运行前会拉取默认分支最新的代码
2. 项目会被放到爬虫`worker`容器的根目录下 即 `/项目文件`
3. 工作路径：是指你的项目路径，比如下面的项目结构：
    
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/13/16315322995977.jpg)
    
    工作路径为 `/spider-project`，feaplat会进入到这个目录，后续的代码执行命令都是在这个路径下运行的 
    
1. requirements.txt：用于安装依赖包，填写依赖包的绝对路径

## 运行

1. 启动命令：启动命令是在您添加项目时配置的工作路径下执行的
2. 定时类型：
    1. cron：crontab表达式，参考：https://tool.lu/crontab/
    2. interval：时间间隔
    3. date：指定日期
    4. once：立即运行，且只运行一次

## 示例

1. 准备项目，项目结构如下：
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/10/16/16343707944750.jpg)
2. 压缩后上传：（推荐使用 `feapder zip` 命令压缩）
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/10/16/16343709590040.jpg)
   - 工作路径：上传的项目会被放到docker里的根目录下（跟你本机项目路径没关系），然后解压运行。因`feapder_demo.zip`解压后为`feapder_demo`，所以工作路径配置`/feapder_demo`
   - 本项目没依赖，可以不配置`requirements.txt`
   - 若需要第三放库，则在项目下创建requirements.txt文件，把依赖库写进去，然后路径指向这个文件即可，如`/feaplat_demo/requirements.txt`
1. 点击项目进入任务列表，添加任务
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/10/16/16343712604864.jpg)
   启动命令的执行位置是在上面配置的工作路径下执行的，定时类型为once时点击确认添加会自动执行
1. 查看任务实例：
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/10/16/16343720658671.jpg)
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/10/16/16343720862217.jpg)
    
   可以看到已经运行完毕 
   
## git方式拉取私有项目

拉取私有项目需在git仓库里添加如下公钥

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCd/k/tjbcMislEunjtYQNXxz5tgEDc/fSvuLHBNUX4PtfmMQ07TuUX2XJIIzLRPaqv3nsMn3+QZrV0xQd545FG1Cq83JJB98ATTW7k5Q0eaWXkvThdFeG5+n85KeVV2W4BpdHHNZ5h9RxBUmVZPpAZacdC6OUSBYTyCblPfX9DvjOk+KfwAZVwpJSkv4YduwoR3DNfXrmK5P+wrYW9z/VHUf0hcfWEnsrrHktCKgohZn9Fe8uS3B5wTNd9GgVrLGRk85ag+CChoqg80DjgFt/IhzMCArqwLyMn7rGG4Iu2Ie0TcdMc0TlRxoBhqrfKkN83cfQ3gDf41tZwp67uM9ZN feapder@qq.com
```

或在系统设置页面配置您的SSH私钥，然后在git仓库里添加您的公钥，例如：
![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/10/19/16346353514967.jpg)

注意，公私钥加密方式为RSA，其他的可能会有问题

生成RSA公私钥方式如下：
```shell
ssh-keygen -t rsa -C "备注" -f 生成路径/文件名
```
如：
`ssh-keygen -t rsa -C "feaplat" -f id_rsa`
然后一路回车，不要输密码
![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/11/17/16371210640228.jpg)
最终生成 `id_rsa`、`id_rsa.pub` 文件，复制`id_rsa.pub`文件内容到git仓库，复制`id_rsa`文件内容到feaplat爬虫管理系统



## 爬虫监控

> 若您使用的是feapder爬虫或者使用了自定义打点，监控才会有对应的数据

1. 表名：以 task_id 命名
2. 保留策略：这是influxdb的概念，监控数据默认保留180天，滚动更新，这个保留策略为`feapder_180d`，同时也被设置成了默认策略`default`。所以直接用`default`就可以。

## 系统设置

1. GIT_SSH_PRIVATE_KEY：可以在自己的笔记本上使用`cat .ssh/id_rsa`查看，然后把内容复制到进来。不了解git ssh协议的，自行查资料

## 更新版本

```
git pull
docker-compose up -d
```
依次执行以上命令即可
