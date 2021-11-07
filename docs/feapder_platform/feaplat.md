# 爬虫管理系统 - FEAPLAT

> 生而为虫，不止于虫

**feaplat**命名源于 feapder 与 platform 的缩写

读音： `[ˈfiːplæt] `
’
## 为什么用feaplat爬虫管理系统

**市面上的爬虫管理系统**

![feapderd](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/23/feapderd.png)

需要先部署好master、worker节点，worker节点常驻，等待master的指令执行任务。一个worker节点里可能同时跑了多个爬虫，一旦一个爬虫内存泄露等原因，可能会引发worker节点崩溃，影响该节点里的全部任务。并且worker数量不能弹性伸缩，无法利用云原生的优势

**feaplat爬虫管理系统**

![pic](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/23/pic.gif)

根据配置的爬虫数动态生成worker，爬虫启动时才创建，爬虫结束时销毁。一个worker内只跑一个爬虫，各个爬虫或任务之间互不影响，稳定性强。系统架设在`docker swarm`集群上，一台服务器宕机，worker会自动迁移到其他服务器节点。

![-w1736](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/23/16270242301134.jpg)



## 特性

1. 爬虫管理系统不仅支持 `feapder`、`scrapy`，且**支持执行任何脚本**，可以把该系统理解成脚本托管的平台 。

2. 支持集群
3. 工作节点根据配置定时启动，执行完释放，不常驻
4. 一个worker内只运行一个爬虫，worker彼此之间隔离，互不影响。
5. 支持**管理员**和**普通用户**两种角色
6. 可自定义爬虫端镜像


## 功能概览

[点我观看视频](http://markdown-media.oss-cn-beijing.aliyuncs.com/爬虫管理平台完整版.mp4)

### 1. 项目管理

项目列表
![-w1786](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16254967791920.jpg)

添加/编辑项目
![-w1785](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16254968151490.jpg)

### 2. 任务管理

任务列表
![-w1791](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16254968630425.jpg)

定时支持 crontab、时间间隔、指定日期、只运行一次 四种方式。只运行一次的定时方式会在创建任务后立即运行
![-w1731](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16254968513292.jpg)

### 3. 任务实例

列表
![-w1785](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16254981090479.jpg)

日志
![-w1742](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16254983085371.jpg)


### 4. 用户管理

用户分为**管理员**和**普通用户**两种角色，管理员可看到全部项目，普通用户只可看到自己创建的项目，且只有管理员可看到用户管理面板

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/12/16260660857747.jpg)


### 5. 爬虫监控

feaplat支持对feapder爬虫的运行情况进行监控，除了数据监控和请求监控外，用户还可自定义监控内容，详情参考[自定义监控](source_code/监控打点?id=自定义监控)

若scrapy爬虫或其他python脚本使用监控功能，也可通过自定义监控的功能来支持，详情参考[自定义监控](source_code/监控打点?id=自定义监控)

注：需 feapder>=1.6.6

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/14/16316112326191.jpg)



## 部署

> 下面部署以centos为例， 其他平台docker安装方式可参考docker官方文档：https://docs.docker.com/compose/install/

### 1. 安装docker

删除旧版本（可选，需要重装升级时执行）

```shell
yum remove docker  docker-common docker-selinux docker-engine
```

安装：
```shell
yum install -y yum-utils device-mapper-persistent-data lvm2 && python2 /usr/bin/yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo && yum install docker-ce -y
```
国内用户推荐使用
```shell
yum install -y yum-utils device-mapper-persistent-data lvm2 && python2 /usr/bin/yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo && yum install docker-ce -y
```
启动
```shell
systemctl enable docker
systemctl start docker
```

### 2. 安装 docker swarm
    
    docker swarm init
    
    # 如果你的 Docker 主机有多个网卡，拥有多个 IP，必须使用 --advertise-addr 指定 IP
    docker swarm init --advertise-addr 192.168.99.100

### 3. 安装docker-compose

```shell
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```
国内用户推荐使用
```shell
sudo curl -L "https://get.daocloud.io/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 4. 部署feaplat爬虫管理系统
#### 预备项
安装git(1.8.3的版本已够用)
```shell
yum -y install git
```
#### 1. 下载项目

gitub
```shell
git clone https://github.com/Boris-code/feaplat.git
```
gitee
```shell
git clone https://gitee.com/Boris-code/feaplat.git
```

#### 2. 运行 

首次运行需拉取镜像，时间比较久，且运行可能会报错，再次运行下就好了

```shell
cd feaplat
docker-compose up -d
```

- 若端口冲突，可修改.env文件，参考[常见问题](feapder_platform/question?id=修改端口)

- 首次运行时，检查下后端日志，看是否运行成功，若报mysql连接错误，重启一次即可解决。这是因为第一次初始化环境，可能后端先于mysql运行了。
    - 查看后端日志命令：`docker logs -f feapder_backend`
    - 重启命令：`docker-compose restart`

#### 3. 访问爬虫管理系统

默认地址：`http://localhost`
默认账密：admin / admin

- 若未成功，参考[常见问题](feapder_platform/question)
- 使用说明，参考[使用说明](feapder_platform/usage)

#### 4. 停止（可选）

```shell
docker-compose stop
```

### 5. 添加服务器（可选）

> 用于搭建集群，扩展爬虫（worker）节点服务器

#### 1. 安装docker

参考部署步骤1

#### 2. 部署

在master服务器（feaplat爬虫管理系统所在服务器）执行下面命令，查看token

```shell
docker swarm join-token worker
```

**在需扩充的服务器上执行**

```shell
docker swarm join --token [token] [ip]
```

这条命令用于将该台服务器加入集群节点

#### 3. 验证是否成功

在master服务器（feaplat爬虫管理系统所在服务器）执行下面命令

```shell
docker node ls
```

若打印结果包含刚加入的服务器，则添加服务器成功

#### 4. 下线服务器（可选）

在需要下线的服务器上执行

```shell
docker swarm leave
```

## 拉取私有项目

拉取私有项目需在git仓库里添加如下公钥

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCd/k/tjbcMislEunjtYQNXxz5tgEDc/fSvuLHBNUX4PtfmMQ07TuUX2XJIIzLRPaqv3nsMn3+QZrV0xQd545FG1Cq83JJB98ATTW7k5Q0eaWXkvThdFeG5+n85KeVV2W4BpdHHNZ5h9RxBUmVZPpAZacdC6OUSBYTyCblPfX9DvjOk+KfwAZVwpJSkv4YduwoR3DNfXrmK5P+wrYW9z/VHUf0hcfWEnsrrHktCKgohZn9Fe8uS3B5wTNd9GgVrLGRk85ag+CChoqg80DjgFt/IhzMCArqwLyMn7rGG4Iu2Ie0TcdMc0TlRxoBhqrfKkN83cfQ3gDf41tZwp67uM9ZN feapder@qq.com
```

或在系统设置页面配置您的SSH私钥，然后在git仓库里添加您的公钥，例如：
![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/10/19/16346353514967.jpg)


## 自定义爬虫镜像

默认的爬虫镜像只打包了`feapder`、`scrapy`框架，若需要其它环境，可基于`.env`文件里的`SPIDER_IMAGE`镜像自行构建

如将常用的python库打包到镜像
```
FROM registry.cn-hangzhou.aliyuncs.com/feapderd/feapder:[最新版本号]

# 安装依赖
RUN pip3 install feapder \
    && pip3 install scrapy

```

自己随便搞事情，搞完修改下 `.env`文件里的 SPIDER_IMAGE 的值即可


## 价格


| 类型   | 价格  | 说明                            |
|------|-----|-------------------------------|
| 免费版  | 0元   | 可部署10个任务                      |
| 绑定版  | 168元 | 同一公网IP或机器码下永久使用 |
| 非绑定版 | 268元 | 永久使用                          |

**所有版本功能一致，均可免费更新，永久使用**

已买绑定版的用户可半价购买非绑定版

购买方式：添加微信 `boris_tm`

## 学习交流

<table border="0"> 
    <tr> 
     <td> 知识星球：17321694 </td> 
     <td> 作者微信： boris_tm </td> 
     <td> QQ群号：750614606 </td> 
    </tr> 
    <tr> 
    <td> <img src="http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/02/16/zhi-shi-xing-qiu.jpeg" width=250px>
 </td> 
     <td> <img src="http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/12/er-wei-ma.jpeg" width="250px" /> </td> 
     <td> <img src="http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/12/16260897330897.jpg" width="250px" /> </td> 
    </tr> 
  </table> 
  
  加好友备注：feaplat
