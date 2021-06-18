from feapder.utils import tools

times = [
    '十',
    '十一',
    '二十一',
    "二零一五年十一月三日十三点五十四分十1秒",
        ]
for i in times:
    date = tools.transform_lower_num(i)
    print(i,date)



date = tools.format_time("昨天3:10")
print(date)
# assert date == "2021-03-15 00:00:00"



date = tools.format_time("昨天 3:10")
print(date)

date = tools.format_time("2021-11-5 14:18:10")
print(date)


date = tools.format_time("1 年前")
print(date)