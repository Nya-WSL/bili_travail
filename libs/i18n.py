import os
import locale as _locale
from pathlib import Path

import orjson

from .log import logger

DEFAULT_LANG = "zh-CN"
SUPPORTED_FALLBACK_ORDER = ["zh-CN"]
"""翻译回退顺序，逐层查找直至最后一个"""
LOCALES_DIR = Path("locales")
LANG_NAME_KEY = "__language_name__"

# 下拉展示顺序：内置语言在前，其余按语言代码升序
_ORDER = ["zh-CN", "en-US"]
# NiceGUI(Quasar) 支持的语言代码，未收录的语言回退英文
_UI_LANG_MAP = {"zh-CN": "zh-CN", "en-US": "en-US"}

_translations: dict[str, dict[str, str]] = {}
_current_lang = DEFAULT_LANG
_missing_keys: set[str] = set() # 已报告过的缺失key，避免重复打日志
_warned_missing_dir = False # 语言文件目录缺失或为空时只告警一次


def _load(lang: str) -> dict[str, str]:
    """加载语言文件并缓存，失败时缓存空字典"""

    if lang in _translations:
        return _translations[lang]

    path = LOCALES_DIR / f"{lang}.json"

    try:
        with open(path, "rb") as f:
            data = orjson.loads(f.read())

        if not isinstance(data, dict):
            logger.warning("语言文件内容不是字典，已忽略: {}", path)
            return {}

        _translations[lang] = data
    except Exception:
        # 失败时不写入缓存，文件恢复后下次调用会重新加载
        logger.opt(exception=True).warning("加载语言文件失败，将回退默认语言: {}", path)
        return {}

    return _translations[lang]


def _warn_missing_dir() -> None:
    """语言文件目录缺失或为空时只告警一次"""

    global _warned_missing_dir

    if _warned_missing_dir:
        return

    _warned_missing_dir = True
    logger.warning("未找到可用的语言文件，将回退默认语言: {}", LOCALES_DIR)


def available_languages() -> dict[str, str]:
    """
    扫描语言文件目录，获取可用语言

    :return dict: {语言代码: 母语名}，每次调用都会重新扫描目录
    """

    langs: dict[str, str] = {}

    if not LOCALES_DIR.exists():
        _warn_missing_dir()
        return {DEFAULT_LANG: DEFAULT_LANG}

    for path in sorted(LOCALES_DIR.glob("*.json")):
        code = path.stem
        langs[code] = _load(code).get(LANG_NAME_KEY, code)

    if not langs:
        _warn_missing_dir()
        return {DEFAULT_LANG: DEFAULT_LANG}

    ordered = {code: langs[code] for code in _ORDER if code in langs}
    ordered.update({code: name for code, name in sorted(langs.items()) if code not in _ORDER})

    return ordered


def detect_system_language() -> str:
    """
    检测系统语言

    :return str: 受支持的语言代码，检测失败时返回默认语言
    """

    try:
        if os.name == "nt":
            import ctypes

            # LANGID 主语言位：0x04=zh，0x09=en
            primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF

            if primary == 0x04:
                return "zh-CN"
            if primary == 0x09:
                return "en-US"

            return DEFAULT_LANG

        lang = (_locale.getlocale()[0] or os.environ.get("LANG", "")).lower()

        if lang.startswith("zh"):
            return "zh-CN"
        if lang.startswith("en"):
            return "en-US"

    except Exception:
        logger.warning("检测系统语言失败，使用默认语言")

    return DEFAULT_LANG


def resolve_language(value: str | None) -> str:
    """
    解析配置中的语言设置

    :param value: 配置值，auto 或空则跟随系统
    :return str: 语言代码
    """

    if not value or value == "auto":
        return detect_system_language()

    return value


def set_language(lang: str) -> None:
    """
    设置当前语言，不受支持时回退默认语言

    :param lang: 语言代码
    """

    global _current_lang

    if lang not in available_languages():
        logger.warning("语言 {} 不存在，回退为 {}", lang, DEFAULT_LANG)
        lang = DEFAULT_LANG

    _current_lang = lang
    _load(lang)


def get_language() -> str:
    """
    获取当前语言

    :return str: 语言代码
    """

    return _current_lang


def ui_language() -> str:
    """
    获取Quasar组件使用的语言代码

    :return str: 语言代码
    """

    return _UI_LANG_MAP.get(_current_lang, "en-US")


def t(key: str, **kwargs) -> str:
    """
    翻译文案，当前语言不存在时回退默认语言，仍不存在则返回key本身

    :param key: 文案key
    :param kwargs: 占位符参数
    :return str: 翻译后的文案
    """

    text = _load(_current_lang).get(key)

    if text is None:
        text = _load(DEFAULT_LANG).get(key)

    if text is None:
        if key not in _missing_keys:
            _missing_keys.add(key)
            logger.debug("缺少翻译: {}", key)

        return key

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            logger.warning("翻译占位符填充失败: {}", key)

    return text
