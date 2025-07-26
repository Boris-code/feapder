from feapder.db.mysqldb import MysqlDB


db = MysqlDB(
    ip="localhost", port=3306, db="feapder", user_name="feapder", user_pass="feapder123", set_session=["SET time_zone='+08:00'"]
)

MysqlDB.from_url("mysql://feapder:feapder123@localhost:3306/feapder?charset=utf8mb4")

result = db.find("SELECT @@global.time_zone, @@session.time_zone, date_format(NOW(), '%Y-%m-%d %H:%i:%s')")
print(f"Database timezone info: {result}")