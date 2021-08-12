from feapder.db.redisdb import RedisDB
import time
db = RedisDB.from_url("redis://localhost:6379")

# db.clear("test")
db.zincrby("test", 1.0, "a")
