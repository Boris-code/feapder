from feapder.db.mysqldb import MysqlDB


db = MysqlDB(
    ip="localhost", port=3306, db="feapder", user_name="feapder", user_pass="feapder123"
)
