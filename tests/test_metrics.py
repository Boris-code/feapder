from feapder import setting
from influxdb import InfluxDBClient


if __name__ == "__main__":
    influxdb_client = InfluxDBClient(
        host=setting.INFLUXDB_HOST,
        port=setting.INFLUXDB_PORT,
        udp_port=setting.INFLUXDB_UDP_PORT,
        database="feapder",
        use_udp=False,
        timeout=10,
        username="root",
        password="root",
    )

    r = influxdb_client.get_list_measurements()
    print(r)
    point = influxdb_client.get_list_series(measurement="task_23")
    print(point)