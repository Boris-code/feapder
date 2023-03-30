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


for i in range(1000):
    metrics.emit_counter("total count", count=1000, classify="test5")
    for j in range(1000):
        metrics.emit_counter("key", count=1, classify="test5")

metrics.close()
