from feapder.utils import tools

time = "昨天"

date = tools.format_time(time)
assert date == "2021-03-15 00:00:00"


