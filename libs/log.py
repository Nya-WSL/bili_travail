import os
import sys
import datetime
from loguru import logger

if not os.path.exists("logs"):
    os.mkdir("logs")

HOME_DIR = os.path.expanduser("~")

file_time = datetime.datetime.now().strftime("%Y%m%d")
file_name = os.path.join("logs", f"bili_travail_{file_time}.log")


def mask_home_dir(record):
    """将日志中的 HOME_DIR 替换为 ~"""
    msg = record.get("message", "")
    record["message"] = msg.replace(HOME_DIR, "[HOME_DIR]")


logger.remove()  # 移除默认 handler

logger.add(
    file_name,
    encoding="utf-8",
    enqueue=True,
    backtrace=True,
    diagnose=True,
    format="{time:%Y-%m-%d %H:%M:%S} [{level}]: {name} | {function}({line}): <level>{message}</level>",
)

logger = logger.patch(mask_home_dir)


# 全局异常捕获
def handle_exception(exc_type, exc_value, exc_traceback):
    if exc_type != KeyboardInterrupt:
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).error("未知错误！")
    else:
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).warning(
            "程序被用户中断"
        )


sys.excepthook = handle_exception