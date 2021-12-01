from feapder.utils import tools
from datetime import datetime


date = tools.format_time("昨天3:10")
print(date)

print(tools.format_date("2017年4月17日 3时27分12秒"))

date = tools.format_time("昨天")
print(date)

date = tools.format_time("2021-11-05 14:18:10")
print(date)

date = tools.format_time("1 年前")
print(date)


class C:
    pass


data = {"date": datetime.now(), "c": C()}
print(tools.dumps_json(data))
