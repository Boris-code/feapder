from feapder.utils import metrics

# 初始化打点系统
metrics.init()

metrics.emit_counter("key", count=1, classify="test")

metrics.close()
