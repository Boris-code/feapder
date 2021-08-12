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
    sql = '''
    SELECT sum("_count") FROM "task_23" WHERE ("classify" = 'document') AND time >= now() - 24h and time <= now() GROUP BY time(60s), "_key" fill(0)
    '''
    datas = influxdb_client.query(sql)
    print(datas)