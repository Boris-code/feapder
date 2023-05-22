import asyncio

from feapder.utils import metrics

# 初始化打点系统
metrics.init(
    influxdb_host="localhost",
    influxdb_port="8086",
    influxdb_udp_port="8089",
    influxdb_database="feapder",
    influxdb_user="***",
    influxdb_password="***",
    influxdb_measurement="test_metrics",
    debug=True,
)


async def test_counter_async():
    for i in range(100):
        await metrics.aemit_counter("total count", count=100, classify="test5")
        for j in range(100):
            await metrics.aemit_counter("key", count=1, classify="test5")


def test_counter():
    for i in range(100):
        metrics.emit_counter("total count", count=100, classify="test5")
        for j in range(100):
            metrics.emit_counter("key", count=1, classify="test5")


def test_store():
    metrics.emit_store("total", 100, classify="cookie_count")


def test_time():
    metrics.emit_timer("total", 100, classify="time")


def test_any():
    metrics.emit_any(
        tags={"_key": "total", "_type": "any"}, fields={"_value": 100}, classify="time"
    )


if __name__ == "__main__":
    asyncio.run(test_counter_async())
    test_counter_async()
    test_store()
    test_time()
    test_any()
    metrics.close()
