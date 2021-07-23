# 爬虫管理系统|FEAPDER

> 生而为虫，不止于虫

## 为什么用feapder爬虫管理系统

**市面上的爬虫管理系统**

![feapderd](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/23/feapderd.png)

需要先部署好master、worker节点，worker节点常驻，等待master的指令执行任务。一个worker节点里可能同时跑了多个爬虫，一旦一个爬虫内存泄露等原因，可能会引发worker节点崩溃，影响该节点里的全部任务。并且worker数量不能弹性伸缩，无法利用云原生的优势

**feapder爬虫管理系统**

![pic](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/23/pic.gif)

根据配置的爬虫数动态生成worker，爬虫启动时才创建，爬虫结束时销毁。

![-w1736](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/23/16270242301134.jpg)

系统架设在`docker swarm`集群上，正是因为worker的弹性伸缩，使系统的稳定性大大提升，一台服务器宕机，worker会自动迁移到其他服务器节点。若后续部署到阿里云的k8s上，在爬虫高峰期时，利用阿里云k8s自动伸缩机制，即可实现自动扩充服务器节点，爬虫高峰期过了自动释放服务器，降低成本

## 特性

1. **爬虫管理系统不仅支持 `feapder`、`scrapy`，且支持执行任何脚本，可以把该系统理解成脚本托管的平台** 。因为爬虫往往需要其他脚本辅助，如生产cookie脚本、搭建nodejs服务破解js，甚至是其他语言的脚本，本管理系统在设计之初就考虑到了这一点，因此可完美支持。

2. **支持集群**，工作节点根据配置定时启动，**执行完释放，不常驻**，节省服务器资源。一个爬虫实例一个节点，**彼此之间隔离**，互不影响。
3. 支持**管理员**和**普通用户**两种角色，管理员可看到全部项目，普通用户只可看到自己创建的项目。


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


## 部署

> 下面部署以centos为例， 其他平台部署可参考docker官方文档：https://docs.docker.com/compose/install/

### 1. 安装docker

删除旧版本（需要重装升级时执行）

```shell
yum remove docker  docker-common docker-selinux docker-engine
```

安装：
```shell
yum install -y yum-utils device-mapper-persistent-data lvm2 && python2 /usr/bin/yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo && yum install docker-ce -y
```

启动
```shell
systemctl enable docker
systemctl start docker
```

### 2. 安装 docker swarm

初始化
    
    docker swarm init
    
    # 如果你的 Docker 主机有多个网卡，拥有多个 IP，必须使用 --advertise-addr 指定 IP
    docker swarm init --advertise-addr 192.168.99.100

初始化后会提示如下：

```bash
> docker swarm init --advertise-addr 192.168.99.100
Swarm initialized: current node (za53ikuwzpr11ojuj4fgx8ys0) is now a manager.

To add a worker to this swarm, run the following command:

    docker swarm join --token SWMTKN-1-1ujljqjf3mli9r940vcdjd7clyrdfjkqyf8g4g6kapfvkjkj9e-41byjvvodfpk7nz4smfdq44w0 192.168.99.100:2377

To add a manager to this swarm, run 'docker swarm join-token manager' and follow the instructions.
```

### 3. 添加节点

添加其他服务器为节点时使用上面提示的 `docker swarm join --token [token] [ip]`命令 

### 4. 安装docker-compose

```python
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 5. 部署管理系统

#### 1. 下载项目

```shell
git clone https://github.com/Boris-code/feapder-platform.git
```

#### 2. 运行 

首次运行需拉取镜像，时间比较久，且运行可能会报错，再次运行下就好了

```shell
cd feapder-platform
docker-compose up
```

*运行起来会提示购买授权码，购买后继续*

#### 3. 修改配置

```shell
cd feapder-platform
vim .env
```

配置里有注释，注意必须修改下面两项

```shell
# 服务端部署的服务器所在的内网IP，用于爬虫节点通讯
BACKEND_IP=
# 授权码
AUTHORIZATION_CODE=
```

查看内网地址：

```shell
ifconfig
```
![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16255025919847.jpg)

`.env` 文件将常用的配置项列了出来，`docker-compose.yaml`引用。若需要更进一步的自定义配置，可修改`docker-compose.yaml`


#### 4. 后台运行
```shell 
docker-compose up -d
```

#### 5. 访问爬虫管理系统

默认地址：`http://localhost`
默认账密：admin / admin

端口修改在`.env`文件

#### 6. 停止

```shell
docker-compose stop
```

## 拉取私有项目

拉取私有项目需在git仓库里添加如下公钥

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCd/k/tjbcMislEunjtYQNXxz5tgEDc/fSvuLHBNUX4PtfmMQ07TuUX2XJIIzLRPaqv3nsMn3+QZrV0xQd545FG1Cq83JJB98ATTW7k5Q0eaWXkvThdFeG5+n85KeVV2W4BpdHHNZ5h9RxBUmVZPpAZacdC6OUSBYTyCblPfX9DvjOk+KfwAZVwpJSkv4YduwoR3DNfXrmK5P+wrYW9z/VHUf0hcfWEnsrrHktCKgohZn9Fe8uS3B5wTNd9GgVrLGRk85ag+CChoqg80DjgFt/IhzMCArqwLyMn7rGG4Iu2Ie0TcdMc0TlRxoBhqrfKkN83cfQ3gDf41tZwp67uM9ZN feapder@qq.com
```

或在`.env`文件里配置您的SSH私钥，然后在git仓库里添加您的公钥。

## 自定义爬虫节点

默认的爬虫节点只打包了`feapder`、`scrapy`框架，若需要其它环境，可基于`.env`文件里的`SPIDER_IMAGE`镜像自行构建

如将常用的python库打包到镜像
```
FROM registry.cn-hangzhou.aliyuncs.com/feapderd/feapder:[最新版本号]

# 安装依赖
RUN pip3 install feapder \
    && pip3 install scrapy

```

自己随便搞事情，搞完修改下 `.env`文件里的 SPIDER_IMAGE 的值即可

欢迎提PR，大家一起构建一个🐂的镜像


## 价格 119元

先部署运行，然后根据终端打印的日志 提供机器码和公网IP，联系作者微信购买授权码

![-w753](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16255499865415.jpg)

授权码与机器码或公网IP绑定，同一服务器或公网IP下永久使用。随着系统的逐渐完善，价格会逐步提升，已购买的用户可免费升级。

本人承诺不上传任何数据，切勿相信其他渠道的破解版，天上掉馅饼不一定是好事。

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
  
  加好友备注：feapder