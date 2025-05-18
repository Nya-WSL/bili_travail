import os
import sys
import logging
import datetime

if not os.path.exists("logs"):
    os.mkdir("logs")

file_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# LEVEL: DEBUG INFO WARNING ERROR CRITICAL
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=os.path.join("logs", f"bili_travail_{file_time}.log"),
                    encoding="utf-8"
                    )

# 全局异常处理钩子
def handle_exception(exc_type, exc_value, exc_traceback):
    logging.error(
        "未知错误！",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

sys.excepthook = handle_exception

logger = logging