# feaplat 部署定位

feaplat 是 feapder 生态的爬虫管理系统。用户提到 feaplat、平台部署、平台调度、平台上不跑任务时，先做只读定位，不要直接改 spider 代码或本地启动方式。

## 只读定位顺序

1. 确认平台运行的是哪个项目包、哪个入口文件、哪个命令参数。
2. 读取项目 `main.py`，确认 `ArgumentParser` 参数和实际 spider 构造。
3. 读取目标 spider，确认继承类型：`AirSpider`、`Spider`、`TaskSpider`、`BatchSpider`。
4. 读取 `setting.py` 和 spider `__custom_setting__`，按配置优先级判断实际 Redis/MySQL/pipeline 配置。
5. 确认 master/worker 是否都运行：
   - `TaskSpider` / `BatchSpider` 下发任务通常需要 `start_monitor_task()`。
   - worker 采集需要 `start()`。
6. 检查 Redis 队列和失败队列 key 是否有数据：
   - `{redis_key}:z_requests`
   - `{redis_key}:z_failed_requests`
   - `{redis_key}:s_failed_items`
   - `{redis_key}:h_spider_status`
7. 检查 MySQL 任务表和批次记录表：
   - `task_table`
   - `task_state`
   - `batch_record_table`
8. 检查日志中真实报错、配置值、入口参数和工作目录。
9. 区分平台问题、配置问题、队列问题、数据库连接问题和 spider 解析代码问题。

## 常见判断

- 平台上“不跑任务”不等于 spider 代码错，可能是 master 没下发、worker 没启动、`redis_key` 不一致、任务表状态不对、配置没加载或包版本不是最新。
- 平台部署后配置不生效时，优先确认平台注入的环境变量、项目 `setting.py`、spider `__custom_setting__`、工作目录和运行入口。
- `BatchSpider` 本批次未结束时，下一批通常不会开始；先查批次记录和任务表状态。
- 不要为了平台问题直接把 feapder 代码改成 `requests` 脚本；AI 判断必须脱离 feapder 时，也要先说明原因、影响、替代方案，并明确请求用户授权。

## 输出建议

先给用户一个定位清单和要读取/执行的只读命令。只有确认根因在代码或配置文件后，再做最小改动。
