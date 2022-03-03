# 爬虫管理系统 - FEAPLAT

> 生而为虫，不止于虫

**feaplat**命名源于 feapder 与 platform 的缩写

读音： `[ˈfiːplæt] `

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/09/14/16316112326191.jpg)

## 特性

1. 支持任何python脚本，包括不限于`feapder`、`scrapy`
2. 支持浏览器渲染，支持有头模式。浏览器支持`playwright`、`selenium`
3. 支持部署服务，可自动负载均衡
4. 支持服务器集群管理
5. 支持监控，监控内容可自定义
6. 支持起多个实例，如分布式爬虫场景
7. 支持弹性伸缩
8. 支持4种定时启动方式
9. 支持自定义worker镜像，如自定义java的运行环境、机器学习环境等，即根据自己的需求自定义（feaplat分为`master-调度端`和`worker-运行任务端`）
10. docker一键部署，架设在docker swarm集群上


## 为什么用feaplat爬虫管理系统

**市面上的爬虫管理系统**

![feapderd](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/23/feapderd.png)

worker节点常驻，且运行多个任务，不能弹性伸缩，任务之前会相互影响，稳定性得不到保障

**feaplat爬虫管理系统**

![pic](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/23/pic.gif)

worker节点根据任务动态生成，一个worker只运行一个任务实例，任务做完worker销毁，稳定性高；多个服务器间自动均衡分配，弹性伸缩


## 功能概览

### 1. 项目管理

添加/编辑项目
![-w1785](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/06/16254968151490.jpg)

### 2. 任务管理

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/03/03/16463109796998.jpg)


### 3. 任务实例

日志
![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/03/03/16463117042527.jpg)


### 4. 爬虫监控

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
| 免费版  | 0元   | 可部署2个任务                      |
| 绑定版  | 188元 | 同一公网IP或机器码下永久使用 |
| 非绑定版 | 288元 | 永久使用                          |

**所有版本功能一致，均可免费更新，永久使用**

购买方式：添加微信 `boris_tm`

随着功能的完善，价格会逐步调整

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
