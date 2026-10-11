import re

from libs import i18n
from libs import log
from libs.i18n import t

logger = log.logger

def format_cd(seconds):
    minute, second = divmod(seconds, 60)
    hour, minute = divmod(minute, 60)
    return ("%02d:%02d:%02d" % (hour, minute, second))

def format_seconds(seconds, lang: str | None = None) -> str:
    """
    格式化时间

    :param seconds: 秒数
    :param lang: 指定语言，为空则使用当前语言
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
        parts.append(t("format.hours", lang=lang, hours=hours))
    if minutes > 0:  # 只有分钟 > 0 时才显示 "分"
        parts.append(t("format.minutes", lang=lang, minutes=minutes))
    if seconds > 0 or (hours == 0 and minutes == 0):  # 有秒或时分均为 0 时，才显示秒
        parts.append(t("format.seconds", lang=lang, seconds=seconds))
    return sign + "".join(parts)  # 返回结果，注意是字符串形式

# 时长单位模板 → 换算系数，解析顺序按系数从大到小（时 → 分 → 秒）
_UNIT_FACTORS = {"format.hours": 3600, "format.minutes": 60, "format.seconds": 1}
# 旧版本硬编码过的单位别名，历史数据里可能仍在，需与派生别名合并
_LEGACY_UNIT_ALIASES = {
    "format.hours": ("小时", "時間", "時", "时", "h"),
    "format.minutes": ("分", "m"),
    "format.seconds": ("秒", "s"),
}
# 单位正则缓存，与参与派生的语言集合绑定，运行中新增语言文件时自动重建
_rule_patterns: tuple[tuple[str, ...], list[tuple[re.Pattern, int]]] | None = None

def _build_rule_patterns() -> list[tuple[re.Pattern, int]]:
    """从各语言包的 format.* 模板派生「数字+单位」正则

    新增语言只需在 locales/ 放置语言包，解析别名自动跟随，无需改动本文件

    :return: [(正则, 换算系数)]，按时 → 分 → 秒排列
    """
    global _rule_patterns

    codes = tuple(i18n.available_languages())

    if _rule_patterns is not None and _rule_patterns[0] == codes:
        return _rule_patterns[1]

    aliases: dict[str, set[str]] = {key: set() for key in _UNIT_FACTORS}

    for code in codes:
        for key in _UNIT_FACTORS:
            template = i18n.raw(key, code)
            # "{hours}小时" → "小时"，"{hours} h" → "h"
            unit = re.sub(r"\{[^}]*\}", "", template).strip() if template else ""

            if unit:
                aliases[key].add(unit)

    for key, legacy in _LEGACY_UNIT_ALIASES.items():
        aliases[key].update(legacy)

    patterns: list[tuple[re.Pattern, int]] = []

    for key, factor in sorted(_UNIT_FACTORS.items(), key=lambda item: -item[1]):
        # 长单位优先，避免「時間」被「時」、「min」被「m」截断
        units = sorted(aliases[key], key=len, reverse=True)

        if units:
            patterns.append((re.compile(r"(\d+)\s*(?:" + "|".join(map(re.escape, units)) + r")", re.IGNORECASE), factor))

    _rule_patterns = (codes, patterns)
    return patterns

def rule_to_seconds(rule):
    """将规则字符串转换为秒数（format_seconds 的逆运算）

    礼物历史里的 rule 可能由不同抓取语言下的 format_seconds 写出（zh「1小时30分」、
    en「1h30m」、ja「1時間30分」），历史文件里会混着多种语言，所以各语言的单位都要认。
    单位别名从所有语言包的 format.hours / format.minutes / format.seconds 模板自动派生，
    新增语言只需放置语言包；旧版本硬编码过的别名（见 _LEGACY_UNIT_ALIASES）继续保留，
    保证历史数据仍可解析。数字与单位之间允许空格，且忽略大小写。

    :param rule: 规则字符串，非字符串返回 None
    :return: 秒数；无法识别的规则按 0 计入（如「清空」这类非时长规则）
    """
    if not isinstance(rule, str):
        return None
    rule = rule.strip()

    sign = 1
    if rule.startswith('-'):
        sign = -1
        rule = rule[1:]
    elif rule.startswith('+'):
        rule = rule[1:]

    total_seconds = 0

    # 从大到小逐个匹配并移除，避免短单位截断长单位
    for pattern, factor in _build_rule_patterns():
        match = pattern.search(rule)

        if match:
            total_seconds += int(match.group(1)) * factor
            rule = rule[:match.start()] + rule[match.end():]

    remaining = rule.strip()
    if remaining.isdigit():
        total_seconds += int(remaining)

    return sign * total_seconds

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