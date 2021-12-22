# 用户池使用说明

用户池分为三种，使用场景如下
1. `GuestUserPool`：游客用户池，用于从不需要登录的页面获取cookie
2. `NormalUserPool`：普通用户池，管理大量账号的信息，从需要登录的页面获取cookie
3. `GoldUserPool`：昂贵的用户池，用于账号单价较高，需要限制使用频率、使用时间的场景

## GuestUserPool使用方式
> 环境：redis

### 导包
```
from typing import Optional

from feapder.network.user_pool import GuestUser
from feapder.network.user_pool import GuestUserPool
```

### 默认的用户池
使用webdriver访问page_url生产cookie
```
user_pool = GuestUserPool(
    "test:user_pool", page_url="https://www.baidu.com"
)

```

### 自定义登录方法
```
class CustomGuestUserPool(GuestUserPool):
    def login(self) -> Optional[GuestUser]:
        # 此处为假数据，正常需通过网站获取cookie
        user = GuestUser(
            user_agent="xxx",
            proxies="yyy",
            cookies={"some_key": "some_value{}".format(time.time())},
        )
        return user

user_pool = CustomGuestUserPool(
    "test:user_pool", min_users=10, keep_alive=True
)
```

### 获取用户
无用户时会先登录生产用户
```
user = user_pool.get_user(block=True)
print("取到user：", user)
print("cookie：", user.cookies)
print("user_agent：", user.user_agent)
print("proxies：", user.proxies)

```
### 删除用户
```
user_pool.del_user(user.user_id)
```

### 维护一定数量的用户
run方法需单独起一个进程调用，此进程会常驻，当用户数不足时会及时补充
```
user_pool.run()
```

## NormalUserPool使用方式
> 环境：redis、mysql

### 导包
```
from feapder.network.user_pool import NormalUser
from feapder.network.user_pool import NormalUserPool
```

### 自定义登录的方法
```
class CustomNormalUserPool(NormalUserPool):
    def login(self, user: NormalUser) -> NormalUser:
        # 此处为假数据，正常需通过登录网站获取cookie
        username = user.username
        password = user.password

        # 登录获取cookie
        cookie = "xxx"
        user.cookies = cookie

        return user

user_pool = CustomNormalUserPool(
    "test:user_pool",
    table_userbase="test_userbase",
    login_retry_times=0,
    keep_alive=True,
)
```
- table_userbase 为mysql里存储用户信息的表，此表会自动创建，需手动录入用户账密

    例如：

    ![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/12/22/16401504359853.jpg)



### 获取用户
无用户时会先登录生产用户
```
user = user_pool.get_user()
print("取到user：", user)
print("cookie：", user.cookies)
print("user_agent：", user.user_agent)
print("proxies：", user.proxies)

```
### 删除用户
```
user_pool.del_user(user.user_id)
```

### 维护一定数量的用户
run方法需单独起一个进程调用，此进程会常驻，当用户数不足时会及时补充
```
user_pool.run()
```

### 标记账号被封
以后不再使用
```
user_pool.tag_user_locked(user.user_id)
```

## GoldUserPool使用方式
> 环境：redis

### 导包
```
from feapder.network.user_pool import GoldUser
from feapder.network.user_pool import GoldUserPool
```

### 定义用户信息
```
users = [
    GoldUser(
        username="zhangsan",
        password="1234",
        max_use_times=10,
        use_interval=5,
    ),
    GoldUser(
        username="lisi",
        password="1234",
        max_use_times=10,
        use_interval=5,
        login_interval=50,
    ),
]
```

### 自定义登录的方法
```
class CustomGoldUserPool(GoldUserPool):
    def login(self, user: GoldUser) -> GoldUser:
        # 此处为假数据，正常需通过登录网站获取cookie
        username = user.username
        password = user.password

        # 登录获取cookie
        cookie = "zzzz"
        user.cookies = cookie

        return user

user_pool = CustomGoldUserPool(
    "test:user_pool",
    users=users,
    keep_alive=True,
)
```

### 获取用户
无用户时会先登录生产用户
```
user = user_pool.get_user()
print("取到user：", user)
print("cookie：", user.cookies)
print("user_agent：", user.user_agent)
print("proxies：", user.proxies)

```

### 获取指定用户
无用户时会先登录生产用户
```
user = user_pool.get_user(username="用户名")
print("取到user：", user)
print("cookie：", user.cookies)
print("user_agent：", user.user_agent)
print("proxies：", user.proxies)

```

### 删除用户
```
user_pool.del_user(user.user_id)
```

### 维护一定数量的用户
run方法需单独起一个进程调用，此进程会常驻，当用户数不足时会及时补充
```
user_pool.run()
```

### 用户延时使用
```
user_pool.delay_use(user.user_id, delay_seconds)
```

### 用户独占使用
某个用户被指定的爬虫独占使用，独占时间内其他爬虫不可使用
```
user = user_pool.get_user(
    username="用户名",
    used_for_spider_name="爬虫名"
)
```