"""运行时活动日志

记录本次运行期间的时间变化事件（礼物加减时、手动调整、连接状态），
供主界面「活动日志」展示。

记录写入 data/activity_log.json，程序启动时会由 main.init_storage() 把上一次
运行的日志备份到 data/history/ 后重新开始记录，因此文件里始终只有本次运行的数据。
"""

import datetime
import threading

import orjson

from libs.log import logger

LOG_PATH = "data/activity_log.json"
MAX_ENTRIES = 500  # 内存与文件中保留的最大条数，超出后丢弃最旧的记录

_lock = threading.Lock()
_entries: list[dict] = []
_dirty = False  # 是否有新记录等待界面刷新


def _now() -> datetime.datetime:
    return datetime.datetime.now()


def _save_locked() -> None:
    """把当前记录写入磁盘

    调用方需持有 _lock
    """

    try:
        with open(LOG_PATH, "wb+") as f:
            f.write(orjson.dumps({"entries": _entries}, option=orjson.OPT_INDENT_2))
    except Exception:
        logger.opt(exception=True).warning("写入活动日志失败")


def _add(entry: dict) -> dict:
    """追加一条记录并落盘"""

    global _dirty

    with _lock:
        _entries.append(entry)

        if len(_entries) > MAX_ENTRIES:
            del _entries[: len(_entries) - MAX_ENTRIES]

        _save_locked()
        _dirty = True

    logger.debug(f"[活动日志] {entry}")

    return entry


def log_gift(uname: str, gift: str, num: int, delta: float) -> dict:
    """记录礼物带来的时间变化

    :param uname: 送礼用户
    :param gift: 礼物名（与OBS投喂记录一致）
    :param num: 礼物数量
    :param delta: 本次变化秒数，正为加时负为减时
    """

    return _add({
        "ts": _now().timestamp(),
        "kind": "gift",
        "user": uname,
        "gift": gift,
        "num": int(num),
        "delta": float(delta),
    })


def log_manual(delta: float) -> dict:
    """记录一次手动加时/减时

    :param delta: 变化秒数，正为加时负为减时
    """

    return _add({
        "ts": _now().timestamp(),
        "kind": "manual",
        "delta": float(delta),
    })


def log_event(event: str, room: str | int | None = None) -> dict:
    """记录一条系统事件

    :param event: 事件名，界面按 log.event.{event} 取文案
    :param room: 相关房间号
    """

    return _add({
        "ts": _now().timestamp(),
        "kind": "system",
        "event": event,
        "room": str(room) if room else None,
    })


def snapshot() -> tuple[list[dict], float]:
    """获取用于展示的记录以及今日时间变化合计

    :return: (记录列表，最新的在前; 今日时间变化合计秒数)
    """

    with _lock:
        entries = list(reversed(_entries))

    today = _now().strftime("%Y-%m-%d")
    total = 0.0

    for entry in entries:
        delta = entry.get("delta")

        if not delta:
            continue

        if datetime.datetime.fromtimestamp(entry["ts"]).strftime("%Y-%m-%d") == today:
            total += float(delta)

    return entries, total


def clear() -> None:
    """清空当前记录（磁盘文件同步清空）"""

    global _dirty

    with _lock:
        _entries.clear()
        _save_locked()
        _dirty = True


def take_dirty() -> bool:
    """取出并清除「有新记录」标记，供界面按需刷新"""

    global _dirty

    with _lock:
        dirty, _dirty = _dirty, False

    return dirty
