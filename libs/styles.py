import os
import libs.config as travail_config

from nicegui import ui

base_config = travail_config.Config()

_FORMATS = {
    'ttf': 'truetype',
    'woff2': 'woff2',
    'woff': 'woff',
}

_FONT_SRC = ", ".join(
    f"url('/static/fonts/custom-font.{ext}') format('{fmt}')"
    for ext, fmt in _FORMATS.items()
    if os.path.exists(f'static/fonts/custom-font.{ext}')
)


# ================================
# 颜色工具：按用户自定义配色派生界面用色
# ================================

def _to_rgb(color: str) -> tuple[int, int, int]:
    """解析 #RGB / #RRGGBB 形式的颜色，无法解析时返回黑色"""

    value = (color or "").strip().lstrip("#")

    if len(value) == 3:
        value = "".join(char * 2 for char in value)

    if len(value) != 6:
        return (0, 0, 0)

    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        return (0, 0, 0)


def _to_hex(rgb) -> str:
    """把 RGB 分量转回 #RRGGBB 字符串"""

    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(value)))) for value in rgb)


def _mix(color_a: str, color_b: str, ratio: float) -> str:
    """按比例混合两个颜色，ratio 为 color_b 的占比

    深色主题下由底色向文字色混出层级色，浅色主题下同理反向变化，无需区分主题。
    """

    a, b = _to_rgb(color_a), _to_rgb(color_b)
    return _to_hex(tuple(a[i] + (b[i] - a[i]) * ratio for i in range(3)))


def _luminance(color: str) -> float:
    """颜色的相对亮度，用于挑选对比色"""

    r, g, b = (value / 255 for value in _to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def theme_colors() -> dict[str, str]:
    """按配置文件生成主界面用色

    :return dict: 基础色与由底色/文字色派生出的层级色
    """

    bg = base_config.get('color', 'bg_color', '#141219')
    text = base_config.get('color', 'main_text_color', '#F2F0F5')
    accent = base_config.get('color', 'btn_color', '#F2529A')
    time_color = base_config.get('color', 'time_color', '#F2529A')

    return {
        "bg": bg,
        "text": text,
        "time": time_color,
        "accent": accent,
        "accent_on": "#12111A" if _luminance(accent) > 0.55 else "#FFFFFF",
        "surface": _mix(bg, text, 0.06),
        "surface_2": _mix(bg, text, 0.13),
        "border": _mix(bg, text, 0.20),
        "muted": _mix(bg, text, 0.58),
        "ok": "#4ADE80",
    }


# ================================
# 组件样式
# ================================

# 分区分块、分段控件、按钮、输入框、活动日志等主界面样式，颜色一律取自 :root 上的设计变量
_COMPONENT_CSS = """
/* 页面根容器：主界面自行管理内边距 */
.nicegui-content { padding: 0 !important; gap: 0 !important; }

.bt-app { padding: 12px 14px 10px; }
.bt-app ::-webkit-scrollbar { width: 6px; height: 6px; }
.bt-app ::-webkit-scrollbar-thumb { background: var(--bt-border); border-radius: 3px; }
.bt-app ::-webkit-scrollbar-track { background: transparent; }

/* 顶栏 */
.bt-topbar { gap: 8px; }
.bt-seg.q-tabs {
    background: var(--bt-surface) !important;
    border: 1px solid var(--bt-border);
    border-radius: 12px;
    padding: 3px;
    min-height: 0 !important;
}
.bt-seg .q-tab {
    min-height: 30px !important;
    padding: 0 10px !important;
    border-radius: 9px;
    color: var(--bt-muted) !important;
}
.bt-seg .q-tab--active { background: var(--bt-surface-2) !important; color: var(--bt-text) !important; }
.bt-seg .q-tab__indicator { display: none !important; }
/* 图标与文字并排，不堆叠 */
.bt-seg .q-tab__content {
    flex-direction: row !important;
    align-items: center;
    justify-content: center;
    gap: 5px;
    padding: 0 !important;
    min-width: 0 !important;
}
.bt-seg .q-tab__label { color: inherit !important; font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
.bt-seg .q-tab__icon { font-size: 16px; }

/* 房间徽标 */
.bt-badge { background: var(--bt-surface); border: 1px solid var(--bt-border); border-radius: 12px; padding: 5px 10px; }
.bt-badge-text { color: var(--bt-text); font-size: 12px; font-weight: 600; }
.bt-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--bt-muted); }
.bt-dot--on { background: var(--bt-ok); }

/* 文字 */
.bt-caps { color: var(--bt-text) !important; font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
.bt-label { color: var(--bt-muted) !important; font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.bt-muted { color: var(--bt-muted) !important; }
.bt-log-total { color: var(--bt-accent) !important; font-size: 12px; font-weight: 700; }
.bt-link { color: var(--bt-muted) !important; font-size: 12px !important; min-height: 0 !important; padding: 0 4px !important; }

/* 面板 */
.bt-panels, .bt-panel { background: transparent !important; }
.bt-panel { padding: 0 !important; }

/* 倒计时 */
.bt-timer { width: 100%; text-align: center; font-size: 64px; font-weight: 800; line-height: 1.15; color: var(--bt-time); }

/* 按钮 */
.bt-btn {
    border-radius: 12px !important;
    min-height: 38px !important;
    padding: 0 14px !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    letter-spacing: .04em;
    box-shadow: none !important;
    color: #FFFFFF !important;
    white-space: nowrap;
}
.bt-btn--square { width: 40px !important; min-width: 40px !important; padding: 0 !important; }
.bt-btn--accent { background: var(--bt-accent) !important; }
.bt-btn--surface { background: var(--bt-surface-2) !important; border: 1px solid var(--bt-border); }
.bt-btn--outline { background: transparent !important; border: 1px solid var(--bt-border); }
.bt-btn .q-icon { font-size: 20px; }
.bt-btn--wide { width: 100% !important; }

/* 时长框：折叠显示当前时分秒，点击展开为输入框 */
.bt-time-box {
    min-height: 38px;
    padding: 0 10px;
    background: var(--bt-surface-2);
    border: 1px solid var(--bt-border);
    border-radius: 12px;
    cursor: pointer;
    transition: border-color .15s ease;
}
.bt-time-box:hover { border-color: var(--bt-accent); }
.bt-time-text { color: var(--bt-text) !important; font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; }

/* 输入框 */
.bt-num .q-field__control, .bt-input .q-field__control, .bt-select .q-field__control {
    background: var(--bt-surface-2) !important;
    border: 1px solid var(--bt-border);
    border-radius: 12px;
}
.bt-input .q-field__control { padding: 0 10px; }
.bt-num .q-field__native, .bt-num .q-field__input,
.bt-input .q-field__native, .bt-input .q-field__input,
.bt-select .q-field__native, .bt-select .q-field__input { font-size: 13px; }
.bt-num .q-field__native, .bt-num .q-field__input { text-align: center; }

/* 字段文字：Quasar 输入类控件默认深色字，在深色底上看不清，统一跟随自定义配色
   （下拉选项弹层在页面外，由下面的 .q-menu 规则单独固定为黑字） */
.q-field__native, .q-field__input { color: var(--bt-text) !important; }
.q-field__label { color: var(--bt-muted) !important; }
.q-field__marginal, .q-field__suffix { color: var(--bt-muted) !important; }

/* 下拉选项弹层：Quasar 默认白底，字色固定为黑色，否则跟随页面配色会看不见 */
.q-menu { background: #FFFFFF !important; }
.q-menu .q-item, .q-menu .q-item__label,
.q-menu .q-field__native, .q-menu .q-field__input { color: #000000 !important; }
.q-menu .q-item--active { color: #000000 !important; font-weight: 700; }
.q-menu .q-item.q-manual-focusable--focused { background: rgba(0, 0, 0, .06) !important; }

/* 弹窗卡片不得超过窗口宽度，避免窄窗口（主窗口 560px）下内容被裁切 */
.q-dialog__inner > .q-card { max-width: calc(100vw - 32px) !important; }

/* 折叠分区 */
.bt-section { border-bottom: 1px solid var(--bt-border); }
.bt-section-head { padding: 12px 2px; cursor: pointer; border-radius: 8px; }
.bt-section-head:hover { background: var(--bt-surface); }
.bt-section-icon, .bt-chevron { color: var(--bt-muted) !important; font-size: 18px; }
.bt-chevron { transition: transform .15s ease; }
.bt-chevron--open { transform: rotate(90deg); }
.bt-section-body { padding: 0 2px 14px; }

/* 设置行 */
.bt-row { border-bottom: 1px solid var(--bt-border); padding: 6px 2px; }
.bt-row:last-of-type { border-bottom: none; }
.bt-row-label { color: var(--bt-text) !important; font-size: 13px; }
.bt-card { background: var(--bt-surface); border: 1px solid var(--bt-border); border-radius: var(--bt-radius, 14px); padding: 14px; }

/* 活动日志 */
.bt-log-row { border-bottom: 1px solid var(--bt-border); padding: 7px 2px; }
.bt-log-time { color: var(--bt-muted) !important; font-size: 12px; width: 40px; }
.bt-log-title { color: var(--bt-text) !important; font-size: 13px; font-weight: 700; }
.bt-log-detail { color: var(--bt-muted) !important; font-size: 11px; }
.bt-log-delta { color: var(--bt-accent) !important; font-size: 13px; font-weight: 700; }
"""


def app_styles() -> None:
    """注入主界面设计变量与组件样式

    变量取自用户自定义配色，界面组件只引用变量，因此换配色无需改组件代码。
    """

    colors = theme_colors()

    variables = "\n".join(f"    --bt-{name.replace('_', '-')}: {value};" for name, value in colors.items())

    ui.add_head_html(
        f"""
        <style>
        :root {{
{variables}
        }}
        {_COMPONENT_CSS}
        </style>
        """,
        shared=True,
    )


# ================================
# 关于 / 礼物统计 / 更新日志：保持重设计前的浅色卡片外观
# 这几处是阅读类内容，不跟随主界面配色，避免深色主题下跟着变暗
# ================================

DOC_BG = "#FCFCFA"
DOC_TEXT = "#4A4A4A"

_doc_styles_added = False


def doc_styles() -> None:
    """注入浅色文档卡片样式，整个进程只注入一次"""

    global _doc_styles_added

    if _doc_styles_added:
        return

    _doc_styles_added = True

    ui.add_head_html(
        f"""
        <style>
        .q-card.bt-doc-card {{
            background-color: {DOC_BG} !important;
            color: {DOC_TEXT};
        }}
        </style>
        """,
        shared=True,
    )


def page_styles(text_color=None):
    if text_color is None:
        # 默认使用OBS字体颜色
        text_color = base_config.get('color', 'text_color', '#4A4A4A')

    ui.add_head_html(
        f"""
        <style>
        @font-face {{
            font-family: 'Custom Font';
            src: {_FONT_SRC};
            font-display: swap;
        }}

        body {{
            font-family: "Custom Font", sans-serif;
            color: {text_color};
        }}

        /* 倒计时数字使用等宽数字并预留固定宽度，避免秒数变化时标签宽度跳动 */
        .countdown-display {{
            font-variant-numeric: tabular-nums;
            font-feature-settings: "tnum" 1;
            min-width: 8ch;
            justify-content: center;
            text-align: center;
        }}
        </style>
        """,
        shared=True,
    )
