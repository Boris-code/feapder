import builtins
import inspect

import pytest

from feapder.db.redisdb import RedisDB


def test_redis_version_floor_synced():
    with open("feapder/requirements.txt", "r", encoding="utf-8") as f:
        requirements = f.read()
    with open("setup.py", "r", encoding="utf-8") as f:
        setup_content = f.read()
    assert "redis>=4.1.0" in requirements
    assert "redis>=4.1.0" in setup_content


def test_cluster_import_error_message(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "redis.cluster":
            raise ImportError("mock cluster import error")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="请安装 redis>=4.1.0"):
        RedisDB(ip_ports="127.0.0.1:6379,127.0.0.1:6380", db=0, service_name="")


def test_sdelete_breaks_when_cursor_zero():
    class FakeRedis:
        def __init__(self):
            self.calls = []
            self._scan_result = [(1, ["a", "b"]), (0, ["c"])]
            self._index = 0

        def ping(self):
            return True

        def sscan(self, table, cursor=0, count=500):
            result = self._scan_result[self._index]
            self._index += 1
            return result

        def srem(self, table, item):
            self.calls.append((table, item))

    db = RedisDB.__new__(RedisDB)
    db._RedisDB__redis = FakeRedis()
    db.sdelete("test_set")
    assert db._RedisDB__redis.calls == [("test_set", "a"), ("test_set", "b"), ("test_set", "c")]


def test_current_status_uses_tokenized_execute_command():
    source = inspect.getsource(RedisDB.current_status)
    assert 'execute_command("KEYS", "*")' in source
    assert 'execute_command("TYPE", key)' in source
    assert 'execute_command("MEMORY", "USAGE", key)' in source
