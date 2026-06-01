import collections
from queue import Queue

from feapder.buffer.item_buffer import ItemBuffer
from feapder.buffer.request_buffer import RequestBuffer
from feapder.core.collector import Collector
from feapder.core.scheduler import Scheduler
from feapder.core.runtime_state import RuntimeState
from feapder.network.item import Item


class FakeRedis:
    def __init__(self, count=0):
        self.count = count

    def zget_count(self, table):
        return self.count


class FakeDoneComponent:
    def __init__(self, idle=True):
        self._idle = idle

    def is_idle(self):
        return self._idle


def build_collector(local_count=0, backend_count=0, busy=False):
    collector = object.__new__(Collector)
    collector._state = RuntimeState()
    collector._db = FakeRedis(backend_count)
    collector._tab_requests = "test:z_requests"
    collector._todo_requests = Queue()
    collector._is_collector_task = busy
    for i in range(local_count):
        collector._todo_requests.put({"request_obj": i, "request_redis": str(i)})
    return collector


def build_request_buffer(request_count=0, delete_count=0, flushing=False):
    buffer = object.__new__(RequestBuffer)
    buffer._state = RuntimeState()
    buffer._requests_deque = collections.deque(range(request_count))
    buffer._del_requests_deque = collections.deque(range(delete_count))
    buffer._is_adding_to_db = flushing
    return buffer


def build_item_buffer(item_count=0, flushing=False):
    buffer = object.__new__(ItemBuffer)
    buffer._state = RuntimeState()
    buffer._items_queue = Queue()
    buffer._is_adding_to_db = flushing
    for i in range(item_count):
        buffer._items_queue.put(i)
    return buffer


def test_collector_pending_count_includes_local_queue_first():
    collector = build_collector(local_count=2, backend_count=5)

    assert collector.pending_count() == 2
    assert collector.is_idle() is False


def test_collector_pending_count_uses_backend_when_local_empty():
    collector = build_collector(local_count=0, backend_count=3)

    assert collector.pending_count() == 3
    assert collector.is_idle() is False


def test_collector_idle_when_not_collecting_and_empty():
    collector = build_collector(local_count=0, backend_count=0, busy=False)

    assert collector.pending_count() == 0
    assert collector.is_idle() is True


def test_request_buffer_pending_count_includes_writes_and_deletes():
    buffer = build_request_buffer(request_count=2, delete_count=1)

    assert buffer.pending_count() == 3
    assert buffer.is_idle() is False


def test_request_buffer_idle_when_empty_and_not_flushing():
    buffer = build_request_buffer(request_count=0, delete_count=0, flushing=False)

    assert buffer.pending_count() == 0
    assert buffer.is_idle() is True


def test_item_buffer_idle_when_queue_empty_and_not_flushing():
    buffer = build_item_buffer(item_count=0, flushing=False)

    assert buffer.pending_count() == 0
    assert buffer.is_idle() is True


def test_item_buffer_not_idle_while_flushing():
    buffer = build_item_buffer(item_count=0, flushing=True)

    assert buffer.is_idle() is False


def test_scheduler_uses_component_idle_methods(monkeypatch):
    monkeypatch.setattr("feapder.core.scheduler.tools.delay_time", lambda seconds: None)
    scheduler = object.__new__(Scheduler)
    scheduler._collector = FakeDoneComponent(idle=True)
    scheduler._parser_controls = [FakeDoneComponent(idle=True)]
    scheduler._item_buffer = FakeDoneComponent(idle=True)
    scheduler._request_buffer = FakeDoneComponent(idle=True)

    assert scheduler.all_thread_is_done() is True


def test_scheduler_waits_for_busy_parser(monkeypatch):
    monkeypatch.setattr("feapder.core.scheduler.tools.delay_time", lambda seconds: None)
    scheduler = object.__new__(Scheduler)
    scheduler._collector = FakeDoneComponent(idle=True)
    scheduler._parser_controls = [FakeDoneComponent(idle=False)]
    scheduler._item_buffer = FakeDoneComponent(idle=True)
    scheduler._request_buffer = FakeDoneComponent(idle=True)

    assert scheduler.all_thread_is_done() is False


def test_component_run_resets_stop_state_before_loop(monkeypatch):
    collector = build_collector(local_count=0, backend_count=0)
    collector._state.request_stop()
    calls = {"count": 0}

    def stop_after_one_input():
        calls["count"] += 1
        collector._state.request_stop()

    monkeypatch.setattr(collector, "_Collector__input_data", stop_after_one_input)

    collector.run()

    assert calls["count"] == 1
    assert collector.is_stopped() is True


def test_request_buffer_not_idle_during_delete_only_flush():
    class InspectingDB:
        def __init__(self, buffer):
            self.buffer = buffer
            self.idle_during_zrem = None

        def zrem(self, table, values):
            self.idle_during_zrem = self.buffer.is_idle()

    buffer = build_request_buffer(request_count=0, delete_count=1, flushing=False)
    buffer._table_request = "test:z_requests"
    buffer._db = InspectingDB(buffer)

    buffer.flush()

    assert buffer._db.idle_during_zrem is False
    assert buffer.is_idle() is True


def test_request_buffer_marks_noop_flush_attempt_busy_while_checking_queue():
    class InspectingEmptyDeque:
        def __init__(self, buffer):
            self.buffer = buffer
            self.busy_observations = []

        def __bool__(self):
            self.busy_observations.append(self.buffer.is_adding_to_db())
            return False

        def __len__(self):
            return 0

        def popleft(self):
            raise AssertionError("empty queue should not be popped")

    buffer = build_request_buffer(request_count=0, delete_count=0, flushing=False)
    buffer._requests_deque = InspectingEmptyDeque(buffer)

    buffer.flush()

    assert buffer._requests_deque.busy_observations
    assert all(buffer._requests_deque.busy_observations)
    assert buffer.is_idle() is True


def test_request_buffer_flush_resets_flag_when_zadd_raises():
    class ExplodingDB:
        def zadd(self, table, values, prioritys=0):
            raise RuntimeError("write failed")

    request = type(
        "FakeRequest",
        (),
        {
            "priority": 300,
            "filter_repeat": False,
            "url": "https://example.com",
            "to_dict": {"url": "https://example.com"},
        },
    )()
    buffer = build_request_buffer(request_count=0, delete_count=0, flushing=False)
    buffer._db = ExplodingDB()
    buffer._table_request = "test:z_requests"
    buffer._table_failed_request = "test:z_failed_requests"
    buffer._requests_deque.append(request)

    buffer.flush()

    assert buffer.is_adding_to_db() is False


def test_item_buffer_flush_resets_flag_when_export_raises(monkeypatch):
    monkeypatch.setattr("feapder.buffer.item_buffer.setting.ITEM_FILTER_ENABLE", False)
    item = Item(title="boom")
    buffer = build_item_buffer(item_count=0, flushing=False)
    buffer._items_queue.put(item)
    buffer._redis_key = "test"
    buffer._task_table = None
    buffer._item_tables = {}
    buffer._item_update_keys = {}
    buffer._item_pipelines = {}
    buffer._pipelines = []
    buffer._have_mysql_pipeline = True
    buffer._mysql_pipeline = None
    buffer.export_retry_times = 0
    buffer.export_falied_times = 0

    def raise_export(table, datas, is_update=False, update_keys=(), used_pipelines=None):
        raise RuntimeError("export failed")

    buffer._ItemBuffer__export_to_db = raise_export

    buffer.flush()

    assert buffer.is_adding_to_db() is False
