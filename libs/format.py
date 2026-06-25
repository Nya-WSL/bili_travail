from libs import log
logger = log.logger

def format_cd(seconds):
    minute, second = divmod(seconds, 60)
    hour, minute = divmod(minute, 60)
    return ("%02d:%02d:%02d" % (hour, minute, second))

def format_seconds(seconds) -> str:
    """
    格式化时间

    :param seconds: 秒数
    """

    # 如果输入不是数字，直接返回
    if not isinstance(seconds, (int, float)):
        logger.warning(f"{seconds} 不是int或float，跳过格式化")
        return str(seconds)

    # 处理符号：正数加 `+`，负数加 `-`，0 不加符号
    if seconds > 0:
        sign = "+"
    elif seconds < 0:
        sign = "-"
    else:
        sign = ""
    # 取绝对值计算
    seconds = abs(seconds)
    # 转换为小时、分钟和秒，转化为整数型格式
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    # 格式化输出
    parts = []
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:  # 只有分钟 > 0 时才显示 "分"
        parts.append(f"{minutes}分")
    if seconds > 0 or (hours == 0 and minutes == 0):  # 有秒或时分均为 0 时，才显示秒
        parts.append(f"{seconds}秒")
    return sign + "".join(parts)  # 返回结果，注意是字符串形式

def sort_dict(dictionary, type_order=None, sort_within_type=False):
    """
    高级排序：先按类型排序，再按值排序

    Args:
        dictionary: 要排序的字典
        type_order: 类型顺序, None: [int, str, list]
        sort_within_type: 是否在同一类型内进行排序
    """
    if type_order is None:
        type_order = [int, str, list]

    type_priority = {t: i for i, t in enumerate(type_order)}

    def sort_key(item):
        key, value = item
        value_type = type(value)
        type_rank = type_priority.get(value_type, len(type_order))

        if sort_within_type:
            # 在同一类型内，按值排序
            if value_type == int or value_type == str:
                return (type_rank, value)
            elif value_type == list:
                return (type_rank, str(value))  # 列表转换为字符串进行比较
            else:
                return (type_rank, str(value))
        else:
            # 只按类型排序
            return type_rank

    sorted_items = sorted(dictionary.items(), key=sort_key)
    return dict(sorted_items)