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

def page_styles(text_color=None):
    if text_color is None:
        # 默认使用子页面字体颜色
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
        </style>
        """,
        shared=True,
    )