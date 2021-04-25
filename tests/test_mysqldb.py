from feapder.db.mysqldb import MysqlDB


db = MysqlDB(
    ip="localhost", port=3306, db="feapder", user_name="feapder", user_pass="feapder123"
)

MysqlDB.from_url("mysql://feapder:feapder123@localhost:3306/feapder?charset=utf8mb4")