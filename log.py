import os
import sys
import logging as log
import datetime
from loguru import logger as logging

if not os.path.exists("logs"):
    os.mkdir("logs")

file_time = datetime.datetime.now().strftime("%Y%m%d")

# LEVEL: DEBUG INFO WARNING ERROR CRITICAL
log.basicConfig(level=log.DEBUG,
                    format='%(asctime)s [%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=os.path.join("logs", f"bili_travail_{file_time}.log"),
                    encoding="utf-8"
                    )

logging.remove()  # 移除默认的日志处理器
logging.add(
    os.path.join("logs", f"bili_travail_{file_time}.log"),
    encoding="utf-8",
    enqueue=True,
    backtrace=True,
    level="DEBUG",
    format='{time:%Y-%m-%d %H:%M:%S} [{level}]: {name} | {function}({line}): <level>{message}</level>'
    )

# 全局异常处理钩子
def handle_exception(exc_type, exc_value, exc_traceback):
    log.error(
        "未知错误！",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

sys.excepthook = handle_exception

logger = logging