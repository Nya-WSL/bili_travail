# third-party modules
from nicegui import ui
import os

def check_font_file_exists():
    formats = {
        'ttf': 'truetype',
        'woff2': 'woff2',
        'woff': 'woff',
    }

    fonts = {}

    for extension, font_format in formats.items():
        if os.path.exists(f'static/fonts/custom-font.{extension}'):
            fonts[extension] = font_format
    return fonts

def page_styles():
    ui.add_head_html(
        f"""
        <style>
        @font-face {{
            font-family: 'Custom Font';
            src: {", ".join(f"url('/static/fonts/custom-font.{extension}') format('{font_format}')" for extension, font_format in check_font_file_exists().items())};
            font-display: swap; /* 优化加载体验 */
            }}

        body {{
            font-family: "Custom Font", sans-serif;
            }}
        </style>
    """,
        shared=True,
    )
