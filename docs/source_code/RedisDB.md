# RedisDB

RedisDB支持**哨兵模式**、**集群模式**与单节点的**普通模式**，封装了操作redis的常用的方法

## 连接

> 若环境变量中配置了数据库连接方式或者setting中已配置，则可不传参 

### 普通模式

```python
from feapder.db.redisdb import RedisDB

db = RedisDB(ip_ports="localhost:6379", db=0, user_pass=None)
```

使用地址连接

```python
from feapder.db.redisdb import RedisDB

db = RedisDB.from_url("redis://[[username]:[password]]@[host]:[port]/[db]")
```

### 哨兵模式

```python
from feapder.db.redisdb import RedisDB

db = RedisDB(ip_ports="172.25.21.4:26379,172.25.21.5:26379,172.25.21.6:26379", db=0, user_pass=None, service_name="my_master")
```

注意：多个地址用逗号分隔，需传递`service_name`

对应setting配置文件，配置方式为：

```python
REDISDB_IP_PORTS = "172.25.21.4:26379,172.25.21.5:26379,172.25.21.6:26379"
REDISDB_USER_PASS = ""
REDISDB_DB = 0
REDISDB_SERVICE_NAME = "my_master"
```

### 集群模式

```python
from feapder.db.redisdb import RedisDB

db = RedisDB(ip_ports="172.25.21.4:26379,172.25.21.5:26379,172.25.21.6:26379", db=0, user_pass=None)
```

注意：多个地址用逗号分隔，不用传递`service_name`

对应setting配置文件，配置方式为：

```python
REDISDB_IP_PORTS = "172.25.21.4:26379,172.25.21.5:26379,172.25.21.6:26379"
REDISDB_USER_PASS = ""
REDISDB_DB = 0
```

## 方法：

详见源码，此处不一一列举， 源码：`feapder.db.redisdb`