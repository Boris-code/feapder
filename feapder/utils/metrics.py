import concurrent.futures
import json
import os
import queue
import random
import socket
import threading
import time
from collections import Counter
from typing import Any

from influxdb import InfluxDBClient

from feapder import setting
from feapder.utils.log import log
from feapder.utils.tools import aio_wrap, ensure_float, ensure_int

_inited_pid = None
# this thread should stop running in the forked process
_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="metrics"
)


class MetricsEmitter:
    def __init__(
        self,
        influxdb,
        *,
        batch_size=10,
        max_timer_seq=0,
        emit_interval=10,
        retention_policy=None,
        ratio=1.0,
        debug=False,
        add_hostname=False,
        max_points=10240,
        default_tags=None,
        time_precision="s",
    ):
        """
        Args:
            influxdb: influxdb instance
            batch_size: 打点的批次大小
            max_timer_seq: 每个时间间隔内最多收集多少个 timer 类型点, 0 表示不限制
            emit_interval: 最多等待多长时间必须打点
            retention_policy: 对应的 retention policy
            ratio: store 和 timer 类型采样率，比如 0.1 表示只有 10% 的点会留下
            debug: 是否打印调试日志
            add_hostname: 是否添加 hostname 作为 tag
            max_points: 本地 buffer 最多累计多少个点
            time_precision: 打点精度 默认 s
        """
        self.pending_points = queue.Queue()
        self.batch_size = batch_size
        self.influxdb: InfluxDBClient = influxdb
        self.tagkv = {}
        self.max_timer_seq = max_timer_seq
        self.lock = threading.Lock()
        self.hostname = socket.gethostname()
        self.last_emit_ts = time.time()  # 上次提交时间
        self.emit_interval = emit_interval  # 提交间隔
        self.max_points = max_points
        self.retention_policy = retention_policy  # 支持自定义保留策略
        self.debug = debug
        self.add_hostname = add_hostname
        self.ratio = ratio
        self.default_tags = default_tags or {}
        self.time_precision = time_precision

    def define_tagkv(self, tagk, tagvs):
        self.tagkv[tagk] = set(tagvs)

    def _point_tagset(self, p):
        return f"{p['measurement']}-{sorted(p['tags'].items())}-{p['time']}"

    def _accumulate_points(self, points):
        """
        对于处于同一个 key 的点做聚合

          - 对于 counter 类型，同一个 key 的值(_count)可以累加
          - 对于 store 类型，不做任何操作，influxdb 会自行覆盖
          - 对于 timer 类型，通过添加一个 _seq 值来区分每个不同的点
        """
        counters = {}  # 临时保留 counter 类型的值
        timer_seqs = Counter()  # 记录不同 key 的 timer 序列号
        new_points = []

        for point in points:
            point_type = point["tags"].get("_type", None)
            tagset = self._point_tagset(point)

            # counter 类型全部聚合，不做丢弃
            if point_type == "counter":
                if tagset not in counters:
                    counters[tagset] = point
                else:
                    counters[tagset]["fields"]["_count"] += point["fields"]["_count"]
            elif point_type == "timer":
                if self.max_timer_seq and timer_seqs[tagset] > self.max_timer_seq:
                    continue
                # 掷一把骰子，如果足够幸运才打点
                if self.ratio < 1.0 and random.random() > self.ratio:
                    continue
                # 增加 _seq tag，以便区分不同的点
                point["tags"]["_seq"] = timer_seqs[tagset]
                timer_seqs[tagset] += 1
                new_points.append(point)
            else:
                if self.ratio < 1.0 and random.random() > self.ratio:
                    continue
                new_points.append(point)

        # 把累加得到的 counter 值添加进来
        new_points.extend(counters.values())
        return new_points

    def _get_ready_emit(self, force=False):
        """
        把当前 pending 的值做聚合并返回
        """
        if self.debug:
            log.info("got %s raw points", self.pending_points.qsize())

        # 从 pending 中读取点, 设定一个最大值，避免一直打点，一直获取
        points = []
        while len(points) < self.max_points or force:
            try:
                points.append(self.pending_points.get_nowait())
            except queue.Empty:
                break

        # 聚合点
        points = self._accumulate_points(points)

        if self.debug:
            log.info("got %s point", len(points))
            log.info(json.dumps(points, indent=4))

        return points

    def emit(self, point=None, force=False):
        """
        1. 添加新点到 pending
        2. 如果符合条件，尝试聚合并打点
        3. 更新打点时间

        :param point:
        :param force: 强制提交所有点 默认False
        :return:
        """
        if point:
            self.pending_points.put(point)

        # 判断是否需要提交点 1、数量 2、间隔 3、强力打点
        if not (
            force
            or self.pending_points.qsize() >= self.max_points  # noqa: W503
            or time.time() - self.last_emit_ts > self.emit_interval  # noqa: W503
        ):
            return

        # 需要打点，读取可以打点的值, 确保只有一个线程在做点的压缩
        with self.lock:
            points = self._get_ready_emit(force=force)

            if not points:
                return
            try:
                self.influxdb.write_points(
                    points,
                    batch_size=self.batch_size,
                    time_precision=self.time_precision,
                    retention_policy=self.retention_policy,
                )
            except Exception:
                log.exception("error writing points")

            self.last_emit_ts = time.time()

    def flush(self):
        if self.debug:
            log.info("start draining points %s", self.pending_points.qsize())
        self.emit(force=True)

    def close(self):
        self.flush()
        try:
            self.influxdb.close()
        except Exception as e:
            log.exception(e)

    def make_point(self, measurement, tags: dict, fields: dict, timestamp=None):
        """
        默认的时间戳是"秒"级别的
        """
        tags = tags.copy() if tags else {}
        tags.update(self.default_tags)
        fields = fields.copy() if fields else {}
        if timestamp is None:
            timestamp = int(time.time())
        # 支持自定义hostname
        if self.add_hostname and "hostname" not in tags:
            tags["hostname"] = self.hostname
        point = dict(measurement=measurement, tags=tags, fields=fields, time=timestamp)
        if self.tagkv:
            for tagk, tagv in tags.items():
                if tagv not in self.tagkv[tagk]:
                    raise ValueError("tag value = %s not in %s", tagv, self.tagkv[tagk])
        return point

    def get_counter_point(
        self,
        measurement: str,
        key: str = None,
        count: int = 1,
        tags: dict = None,
        timestamp: int = None,
    ):
        """
        counter 不能被覆盖
        """
        tags = tags.copy() if tags else {}
        if key is not None:
            tags["_key"] = key
        tags["_type"] = "counter"
        count = ensure_int(count)
        fields = dict(_count=count)
        point = self.make_point(measurement, tags, fields, timestamp=timestamp)
        return point

    def get_store_point(
        self,
        measurement: str,
        key: str = None,
        value: Any = 0,
        tags: dict = None,
        timestamp=None,
    ):
        tags = tags.copy() if tags else {}
        if key is not None:
            tags["_key"] = key
        tags["_type"] = "store"
        fields = dict(_value=value)
        point = self.make_point(measurement, tags, fields, timestamp=timestamp)
        return point

    def get_timer_point(
        self,
        measurement: str,
        key: str = None,
        duration: float = 0,
        tags: dict = None,
        timestamp=None,
    ):
        tags = tags.copy() if tags else {}
        if key is not None:
            tags["_key"] = key
        tags["_type"] = "timer"
        fields = dict(_duration=ensure_float(duration))
        point = self.make_point(measurement, tags, fields, timestamp=timestamp)
        return point

    def emit_any(self, *args, **kwargs):
        point = self.make_point(*args, **kwargs)
        self.emit(point)

    def emit_counter(self, *args, **kwargs):
        point = self.get_counter_point(*args, **kwargs)
        self.emit(point)

    def emit_store(self, *args, **kwargs):
        point = self.get_store_point(*args, **kwargs)
        self.emit(point)

    def emit_timer(self, *args, **kwargs):
        point = self.get_timer_point(*args, **kwargs)
        self.emit(point)


_emitter: MetricsEmitter = None
_measurement: str = None


def init(
    *,
    influxdb_host=None,
    influxdb_port=None,
    influxdb_udp_port=None,
    influxdb_database=None,
    influxdb_user=None,
    influxdb_password=None,
    influxdb_measurement=None,
    retention_policy=None,
    retention_policy_duration="180d",
    emit_interval=60,
    batch_size=10,
    debug=False,
    use_udp=False,
    timeout=10,
    time_precision="s",
    **kwargs,
):
    """
    打点监控初始化
    Args:
        influxdb_host:
        influxdb_port:
        influxdb_udp_port:
        influxdb_database:
        influxdb_user:
        influxdb_password:
        influxdb_measurement: 存储的表，也可以在打点的时候指定
        retention_policy: 保留策略
        retention_policy_duration: 保留策略过期时间
        emit_interval: 打点最大间隔
        batch_size: 打点的批次大小
        debug: 是否开启调试
        use_udp: 是否使用udp协议打点
        timeout: 与influxdb建立连接时的超时时间
        time_precision: 打点精度 默认秒
        **kwargs: 可传递MetricsEmitter类的参数

    Returns:

    """
    global _inited_pid, _emitter
    if _inited_pid == os.getpid():
        return

    influxdb_host = influxdb_host or setting.INFLUXDB_HOST
    influxdb_port = influxdb_port or setting.INFLUXDB_PORT
    influxdb_udp_port = influxdb_udp_port or setting.INFLUXDB_UDP_PORT
    influxdb_database = influxdb_database or setting.INFLUXDB_DATABASE
    influxdb_user = influxdb_user or setting.INFLUXDB_USER
    influxdb_password = influxdb_password or setting.INFLUXDB_PASSWORD
    _measurement = influxdb_measurement or setting.INFLUXDB_MEASUREMENT
    retention_policy = (
        retention_policy or f"{influxdb_database}_{retention_policy_duration}"
    )

    if not all(
        [
            influxdb_host,
            influxdb_port,
            influxdb_udp_port,
            influxdb_database,
            influxdb_user,
            influxdb_password,
            setting.INFLUXDB_MEASUREMENT,
        ]
    ):
        return

    influxdb_client = InfluxDBClient(
        host=influxdb_host,
        port=influxdb_port,
        udp_port=influxdb_udp_port,
        database=influxdb_database,
        use_udp=use_udp,
        timeout=timeout,
        username=influxdb_user,
        password=influxdb_password,
    )
    # 创建数据库
    if influxdb_database:
        try:
            influxdb_client.create_database(influxdb_database)
            influxdb_client.create_retention_policy(
                retention_policy,
                retention_policy_duration,
                replication="1",
                default=True,
            )
        except Exception as e:
            log.error("metrics init falied: {}".format(e))
            return

    _emitter = MetricsEmitter(
        influxdb_client,
        debug=debug,
        batch_size=batch_size,
        time_precision=time_precision,
        retention_policy=retention_policy,
        emit_interval=emit_interval,
        **kwargs,
    )
    _inited_pid = os.getpid()
    log.info("metrics init successfully")


def emit_any(
    tags: dict,
    fields: dict,
    *,
    classify: str = None,
    measurement: str = None,
    timestamp=None,
):
    if not _emitter:
        return

    if classify:
        tags = tags or {}
        tags["classify"] = classify
    measurement = measurement or _measurement
    _emitter.emit_any(measurement, tags, fields, timestamp)


def emit_counter(
    key: str = None,
    count: int = 1,
    *,
    classify: str = None,
    tags: dict = None,
    measurement: str = None,
    timestamp: int = None,
):
    if not _emitter:
        return

    if classify:
        tags = tags or {}
        tags["classify"] = classify
    measurement = measurement or _measurement
    _emitter.emit_counter(measurement, key, count, tags, timestamp)


def emit_timer(
    key: str = None,
    duration: float = 0,
    *,
    classify: str = None,
    tags: dict = None,
    measurement: str = None,
    timestamp=None,
):
    if not _emitter:
        return

    if classify:
        tags = tags or {}
        tags["classify"] = classify
    measurement = measurement or _measurement
    _emitter.emit_timer(measurement, key, duration, tags, timestamp)


def emit_store(
    key: str = None,
    value: Any = 0,
    *,
    classify: str = None,
    tags: dict = None,
    measurement: str,
    timestamp=None,
):
    if not _emitter:
        return

    if classify:
        tags = tags or {}
        tags["classify"] = classify
    measurement = measurement or _measurement
    _emitter.emit_store(measurement, key, value, tags, timestamp)


def flush():
    if not _emitter:
        return
    _emitter.flush()


def close():
    if not _emitter:
        return
    _emitter.close()


aemit_counter = aio_wrap(executor=_executor)(emit_counter)
aemit_store = aio_wrap(executor=_executor)(emit_store)
aemit_timer = aio_wrap(executor=_executor)(emit_timer)
