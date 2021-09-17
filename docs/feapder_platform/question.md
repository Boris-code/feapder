# FEAPLAT常见问题

## 常用命令

1. 运行：`docker-compose up -d`
2. 停止：`docker-compose stop`
3. 查看后端日志：`docker logs -f feapder_backend`
4. 查看爬虫日志：
    1. 查看爬虫实例：`docker service ps task_任务id`
    2. 查看爬虫实例日志：`docker service logs -n 行数 -f ID`

    举例：
    
    ```
    docker service ps task_9
    ```
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16318829484192.jpg)
    
    ```
    docker service logs -n 20 -f u6qhyu2dauiu
    ```
    
6. 查看正在运行的容器：`docker ps` 
5. 进入容器：`docker exec -it 容器ID bash`
    

## 修改端口

默认端口如下：

```
# 前端端口
FRONT_PORT=6385
# 后端端口
BACKEND_PORT=8000
# MYSQL端口
MYSQL_PORT=33306
# REDIS 端口
REDIS_PORT=6379
# 监控系统端口配置
INFLUXDB_PORT_TCP=8086
INFLUXDB_PORT_UDP=8089
```

通过 `vim .env` 敲击`i` 进入编辑模式，修改完按 `esc`退出编辑，敲击 `:wq` 保存


## 首次运行须知

1. 首次运行时，检查下后端日志，看是否运行成功，或报mysql连接错误，重启一次即可解决。这是因为第一次初始化环境，可能后端先于mysql运行了。

2. 管理系统默认账号密码：admin / admin

3. 进入系统后，先到设置页面，配置服务端内网地址：

    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16318826920098.jpg)


    查看内网地址：
    
    ```shell
    ifconfig
    ```
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16255025919847.jpg)

## 启动失败

> 以下列的是几种可能原因，可按照这个顺序排查，但不是所有步骤都需要走一遍

1. 查看后端日志，观察报错，若是docker版本问题，参考部署一节安装最新版本
2. 查看镜像`docker images`，若不存在爬虫镜像`registry.cn-hangzhou.aliyuncs.com/feapderd/feapder`，可能自动拉取失败了，可手动拉取，拉取命令：`docker pull registry.cn-hangzhou.aliyuncs.com/feapderd/feapder:版本号`，版本号在`.env`里查看
3. 重启docker服务，Centos对应的命令为：`service docker restart`，其他自行查资料

## 提示运行成功，但无任务实例

查看不到任务实例的原因可能是服务端内网地址配置错误了，爬虫实例没注册进来。可通过常用命令里的查看爬虫日志看具体问题

## 依赖包安装失败，可手动安装包

1. 在项目配置处将 requirements.txt 一栏置空，使其不自动安装依赖

    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16318840168908.jpg)


2. 添加一个常驻任务：执行命令可填写 `while true; do echo hello world; sleep 1; done`

    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16303761085876.jpg)

1. 查看容器id`docker ps`（若您有多台worker服务器，该任务会被随机分配到一台机器上，您需要在对应的机器上查看）

    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16318842799082.jpg)
2. 进入容器 `docker exec -it 容器ID bash`

5. 接来下就和在centos服务器上操作一样了，你可以`pip`安装依赖