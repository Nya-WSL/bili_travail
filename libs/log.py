import os
import re
import sys
import threading
import datetime
import traceback
import asyncio

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
    enqueue=True,
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

# 全局异常捕获
def _log_traceback(tb_str: str) -> None:
    """统一将脱敏后的堆栈信息写入日志"""
    tb_str = mask_home_dir(exc_traceback=tb_str)
    tb_str = mask_phone_num(exc_traceback=tb_str)

    if "KeyboardInterrupt" not in tb_str:
        logger.opt(exception=False).error("未知错误！\n{}", tb_str)
    else:
        logger.opt(exception=False).warning("程序被用户中断\n{}", tb_str)


def handle_exception(exc_type, exc_value, exc_traceback):
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_str = "".join(tb_lines)
    _log_traceback(tb_str)


def handle_thread_exception(args):
    """捕获子线程中未被 try...except 包裹的异常"""
    try:
        exc_type, exc_value, exc_traceback = args.exc_type, args.exc_value, args.exc_traceback
    except AttributeError:
        exc_type, exc_value, exc_traceback = sys.exc_info()
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_str = "".join(tb_lines)
    _log_traceback(tb_str)


def handle_asyncio_exception(loop, context):
    """捕获 asyncio 任务/协程中未被 try...except 包裹的异常"""
    try:
        exception = context.get("exception")
        if exception is None:
            # 没有异常对象（如取消、句柄错误等），记录上下文信息（先脱敏）
            ctx_str = str(context.get("message", context))
            ctx_str = mask_home_dir(exc_traceback=ctx_str)
            ctx_str = mask_phone_num(exc_traceback=ctx_str)
            logger.opt(exception=False).error("asyncio 异常：{}", ctx_str)
            return
        tb_lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
        tb_str = "".join(tb_lines)
        _log_traceback(tb_str)
    except Exception:
        # 兜底：即使 context 解析失败也先脱敏再记录
        ctx_str = str(context)
        ctx_str = mask_home_dir(exc_traceback=ctx_str)
        ctx_str = mask_phone_num(exc_traceback=ctx_str)
        logger.opt(exception=False).error("asyncio 异常：{}", ctx_str)


sys.excepthook = handle_exception

# 捕获子线程中的未捕获异常
threading.excepthook = handle_thread_exception


def install_asyncio_handler(loop=None):
    """为事件循环安装全局异常处理器，捕获任务中未被 try...except 包裹的异常。

    NiceGUI 等框架的 ui.run 会在内部创建新的事件循环，
    需在其启动回调（如 @app.on_startup）内调用本函数，传入当前运行循环。
    """
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                return
    if loop is not None and not loop.is_closed():
        loop.set_exception_handler(handle_asyncio_exception)


# 尽力为已存在的默认事件循环安装（若当时存在运行中的循环）
install_asyncio_handler()