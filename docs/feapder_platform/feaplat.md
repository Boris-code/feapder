# 爬虫管理系统 - FEAPLAT

> 生而为虫，不止于虫

**feaplat**命名源于 feapder 与 platform 的缩写

读音： `[ˈfiːplæt] `

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/10/12/16655602840534.jpg)


## 特性

1. 支持部署任何程序，包括不限于`feapder`、`scrapy`
2. 支持集群管理，部署分布式爬虫可一键扩展进程数
3. 支持部署服务，且可自动实现服务负载均衡
4. 支持程序异常报警、重启、保活
5. 支持监控，监控内容可自定义
6. 支持4种定时调度模式
7. 自动从git仓库拉取最新的代码运行，支持指定分支
8. 支持多人协同
9. 支持浏览器渲染，支持有头模式。浏览器支持`playwright`、`selenium`
10. 支持弹性伸缩
12. 支持自定义worker镜像，如自定义java的运行环境、node运行环境等，即根据自己的需求自定义（feaplat分为`master-调度端`和`worker-运行任务端`）
13. docker一键部署，架设在docker swarm集群上

## 功能概览

### 1. 项目管理

添加/编辑项目

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/10/12/16655603474851.jpg)

- 支持 git和zip两种方式上传项目
- 根据requirements.txt自动安装依赖包 
- 可选择多个人参与项目

### 2. 任务管理

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/10/12/16655604191030.jpg)
![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/10/12/16655604736752.jpg)

- 支持一键启动多个任务实例（分布式爬虫场景或者需要启动多个进程的场景）
- 支持4种调度模式
- 标签：给任务分类使用
- 强制运行：（上一次任务没结束，本次是否运行，是则会停止上一次任务，然后运行本次调度）
- 异常重启：当部署的程序异常退出，是否自动重启，且会报警
    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/10/12/16655607031254.jpg)
- 支持限制程序运行的CPU、内存等。


### 3. 任务实例

一键部署了20份程序，每个程序独占一个进程，可从列表看每个进程部署到哪台服务器上了，运行状态是什么

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/10/12/16655608218525.jpg)

实时查看日志

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/10/12/16655618630971.jpg)

### 4. 爬虫监控

feaplat支持对feapder爬虫的运行情况进行监控，除了数据监控和请求监控外，用户还可自定义监控内容，详情参考[自定义监控](source_code/监控打点?id=自定义监控)

若scrapy爬虫或其他python脚本使用监控功能，也可通过自定义监控的功能来支持，详情参考[自定义监控](source_code/监控打点?id=自定义监控)

注：需 feapder>=1.6.6

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/10/12/16655595870715.jpg)

### 5. 报警

调度异常、程序异常自动报警
支持钉钉、企业微信、飞书、邮箱

![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2022/10/12/16655607031254.jpg)

## 为什么用feaplat爬虫管理系统

**稳！很稳！！相当稳！！！**

### 市面上的爬虫管理系统

![feapderd](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/23/feapderd.png)

worker节点常驻，且运行多个任务，不能弹性伸缩，任务之前会相互影响，稳定性得不到保障

### feaplat爬虫管理系统

![pic](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/23/pic.gif)

worker节点根据任务动态生成，一个worker只运行一个任务实例，任务做完worker销毁，稳定性高；多个服务器间自动均衡分配，弹性伸缩

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
或者使用国内 daocloud 一键安装命令
```
curl -sSL https://get.daocloud.io/docker | sh
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

输出举例如下

```shell
docker swarm join --token SWMTKN-1-1mix1x7noormwig1pjqzmrvgnw2m8zxqdzctqa8t3o8s25fjgg-9ot0h1gatxfh0qrxiee38xxxx 172.17.5.110:2377
```

**在需扩充的服务器上执行**

```shell
docker swarm join --token [token] [ip]
```

若服务器彼此之间不是内网，为公网环境，则需要将ip改成公网，且开放端口2377

开启并检查2377端口
```shell
firewall-cmd --zone=public --add-port=2377/tcp --permanent
firewall-cmd --reload
firewall-cmd --query-port=2377/tcp
```

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

如自定义python版本，安装常用的库等，需修改feaplat下的`feapder_dockerfile`

```
# 基于最新的版本，若需要自定义python版本，则要求feapder版本号>=2.4
FROM registry.cn-hangzhou.aliyuncs.com/feapderd/feapder:2.4

# 安装自定义的python版本，3.10.8
RUN set -ex \
    && wget https://www.python.org/ftp/python/3.10.8/Python-3.10.8.tgz \
    && tar -zxvf Python-3.10.8.tgz \
    && cd Python-3.10.8 \
    && ./configure prefix=/usr/local/python-3.10.8 \
    && make \
    && make install \
    && make clean \
    && rm -rf /Python-3.10.8* \
    # 配置软链接
    && ln -s /usr/local/python-3.10.8/bin/python3 /usr/bin/python3.10.8 \
    && ln -s /usr/local/python-3.10.8/bin/pip3 /usr/bin/pip3.10.8

# 删除之前的默认python版本
RUN set -ex \
    && rm -rf /usr/bin/python3 \
    && rm -rf /usr/bin/pip3 \
    && rm -rf /usr/bin/python \
    && rm -rf /usr/bin/pip

# 设置默认为python3.10.8
RUN set -ex \
    && ln -s /usr/local/python-3.10.8/bin/python3 /usr/bin/python \
    && ln -s /usr/local/python-3.10.8/bin/python3 /usr/bin/python3 \
    && ln -s /usr/local/python-3.10.8/bin/pip3 /usr/bin/pip \
    && ln -s /usr/local/python-3.10.8/bin/pip3 /usr/bin/pip3

# 将python3.10.8加入到环境变量
ENV PATH=$PATH:/usr/local/python-3.10.8/bin/

# 安装依赖
RUN pip3 install feapder \
    && pip3 install scrapy
    
# 安装node依赖包，内置的node为v10.15.3版本
# RUN npm install packageName -g

```

改好后要打包镜像，打包命令：
```
docker build -f feapder_dockerfile -t 镜像名:版本号 .
```
如
```
docker build -f feapder_dockerfile -t my_feapder:1.0 .
```

打包好后修改下 `.env`文件里的 SPIDER_IMAGE 的值即可如：
```
SPIDER_IMAGE=my_feapder:1.0
```

注：
1. 若有多个worker服务器，且没将镜像传到镜像服务，则需要手动将镜像推到其他服务器上，否则无法拉取此镜像运行
2. 若自定义了python版本，则需要添加挂载，否则feaplat上自动安装的依赖库不会保留。挂载方式：修改`docker-compose.yaml`的        SPIDER_RUN_ARGS参数。如
   ```
   SPIDER_RUN_ARGS=["--mount type=volume,source=feapder_python3.10,destination=/usr/local/python-3.10.8"]
   ```

## 价格

| 类型   | 价格   | 说明                  |
|------|------|---------------------|
| 试用版  | 0元   | 可部署20个任务，删除任务不可恢复额度 |
| 正式版 | 888元 | 有效期一年，可换绑服务器        |

**部署后默认为试用版，购买授权码后配置到系统里即为正式版**

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
