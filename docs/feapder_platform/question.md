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


## 启动失败

> 以下列的是几种可能原因，可按照这个顺序排查，但不是所有步骤都需要走一遍

1. 查看后端日志，观察报错
    1. 若是docker版本问题，参考部署一节安装最新版本，
    2. 若是报 `This node is not a swarm manager`，则是部署环境没准备好，执行`docker swarm init`，可参考参考部署一节
2. 查看worker状态：
    ```
    docker service ps task_任务id --no-trunc
    ```
    看看error信息

4. 查看镜像`docker images`，若不存在爬虫镜像`registry.cn-hangzhou.aliyuncs.com/feapderd/feapder`，可能自动拉取失败了，可手动拉取，拉取命令：`docker pull registry.cn-hangzhou.aliyuncs.com/feapderd/feapder:版本号`，版本号在`.env`里查看
5. 重启docker服务，Centos对应的命令为：`service docker restart`，其他自行查资料

## 依赖包安装失败，可手动安装包

1. 在项目配置处将 requirements.txt 一栏置空，使其不自动安装依赖

    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16318840168908.jpg)


2. 添加一个常驻任务：执行命令可填写 `while true; do echo hello world; sleep 1; done`

    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16303761085876.jpg)

1. 查看容器id`docker ps`（若您有多台worker服务器，该任务会被随机分配到一台机器上，您需要在对应的机器上查看）

    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/17/16318842799082.jpg)
2. 进入容器 `docker exec -it 容器ID bash`

3. 接来下就和在centos服务器上操作一样了，你可以`pip`安装依赖

## 授权问题

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/02/21/16454346779741.jpg)

此问题为服务器时间和时区问题, 可以在服务器上输入 `date` ，命令检查时间及时区是否正确

正常应该为 `Mon Feb 21 17:03:11 CST 2022` 注意是 CST 不是 UTC

修改时区及矫正时间命令

```
# 改时区
rm -f /etc/localtime
ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# 校对时间
clock --hctosys
```

## 我搭建了个集群，如何让主节点不跑任务

在主节点上执行下面命令，将其设置成drain状态即可

    docker node update --availability drain 节点id
 
 ## Network 问题

attaching to network failed, make sure your network options are correct and check manager logs: context deadline exceeded
 ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2023/02/16/16765140608308.jpg)

1. 确定当前节点是不是Drain节点：docker node ls
    
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2023/02/16/16765145635622.jpg)
    
    是则继续往下看，不是则在评论区留言
    
1. 修复

    ```
    docker node update --availability active 节点id
    docker node update --availability drain 节点id
    ```    
    
原因是Drain节点，不能为其分配网络资源，需要先改成active，然后启动，之后在改回drain
