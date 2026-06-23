from nicegui import ui
import os

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

def page_styles():
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
        }}
        </style>
        """,
        shared=True,
    )