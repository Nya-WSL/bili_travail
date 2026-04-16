import os
import re
import sys
import datetime
import traceback
from loguru import logger

if not os.path.exists("logs"):
    os.mkdir("logs")

HOME_DIR = os.path.expanduser("~")

file_time = datetime.datetime.now().strftime("%Y%m%d")
file_name = os.path.join("logs", f"bili_travail_{file_time}.log")


def mask_home_dir(record=None, exc_traceback=None):
    """将日志中的 HOME_DIR 脱敏"""
    if record:
        msg = record.get("message", "")
        record["message"] = msg.replace(HOME_DIR, "[HOME_DIR]")
        return record

    if exc_traceback:
        exc_traceback = exc_traceback.replace(HOME_DIR, "[HOME_DIR]")
        return exc_traceback


def mask_phone_num(record=None, exc_traceback=None):
    """将日志中疑似电话的信息脱敏"""
    if record:
        msg = record.get("message", "")
        record["message"] = re.sub(r"1[3-9]\d{9}", "*" * 11, msg)
        record["message"] = re.sub(r"0[0-9]\d{9}", "*" * 11, record["message"])
        record["message"] = re.sub(r"\d{3}-\d{4}-\d{4}", "***-****-****", record["message"])
        record["message"] = re.sub(r"\d{3} \d{4} \d{4}", "*** **** ****", record["message"])
        record["message"] = re.sub(r"\d{4} \d{4}", "**** ****", record["message"])
        record["message"] = re.sub(r"\d{3}-\d{8}", "***-********", record["message"])
        record["message"] = re.sub(r"\d{4}-\d{4}", "****-****", record["message"])
        return record

    if exc_traceback:
        exc_traceback = re.sub(r"1[3-9]\d{9}", "*" * 11, exc_traceback)
        exc_traceback = re.sub(r"0[0-9]\d{9}", "*" * 11, exc_traceback)
        exc_traceback = re.sub(r"\d{3}-\d{4}-\d{4}", "***-****-****", exc_traceback)
        exc_traceback = re.sub(r"\d{3} \d{4} \d{4}", "*** **** ****", exc_traceback)
        exc_traceback = re.sub(r"\d{4} \d{4}", "**** ****", exc_traceback)
        exc_traceback = re.sub(r"\d{3}-\d{8}", "***-********", exc_traceback)
        exc_traceback = re.sub(r"\d{4}-\d{4}", "****-****", exc_traceback)
        return exc_traceback


logger.remove()  # 移除默认 handler

logger.add(
    file_name,
    encoding="utf-8",
    enqueue=True,  # 改为同步写入，确保即使程序崩溃也不会丢失日志
    backtrace=True,
    diagnose=True,
    format="{time:%Y-%m-%d %H:%M:%S} [{level}]: {name} | {function}({line}): <level>{message}</level>",
)

def mask_rule(logger):
    """添加脱敏规则"""
    logger = logger.patch(mask_home_dir)
    logger = logger.patch(mask_phone_num)

    return logger

logger = mask_rule(logger)

# 注册清理函数，确保程序退出时日志被写入磁盘
def cleanup_logs():
    """程序退出时确保日志写入磁盘"""
    try:
        logger.complete()
    except:
        pass

import atexit
atexit.register(cleanup_logs)

# 全局异常捕获
def handle_exception(exc_type, exc_value, exc_traceback):
    # 用户主动中断，不记录日志
    if exc_type == KeyboardInterrupt:
        return

    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_str = "".join(tb_lines)

    tb_str = mask_home_dir(exc_traceback=tb_str)
    tb_str = mask_phone_num(exc_traceback=tb_str)

    # 先尝试写入日志文件
    try:
        logger.opt(exception=False).error(
            "未知错误！\n{}", tb_str
        )

        # 在异常处理完成后，立即刷新日志
        logger.complete()
    except Exception:
        # 如果日志系统失败，尝试直接写入文件
        try:
            with open(file_name, "a", encoding="utf-8") as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp} [CRITICAL]: 异常处理器日志系统失败\n")
                f.write(f"异常类型: {exc_type.__name__}\n")
                f.write(f"异常信息: {exc_value}\n")
                f.write(f"堆栈跟踪:\n{tb_str}\n")
                f.write("=" * 80 + "\n")
        except:
            pass  # 所有的日志方式都失败了，只能放弃


sys.excepthook = handle_exception