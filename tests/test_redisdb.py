from feapder.db.redisdb import RedisDB

db = RedisDB(ip_ports="localhost:6379")

# db.zadd("test", list(range(10)), list(range(10)))

# db.zremrangebyscore("test", 1, 3)

db.zrem("test", [4, 0])