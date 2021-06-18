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



# date = tools.format_time(time)
# print(date)
# assert date == "2021-03-15 00:00:00"


