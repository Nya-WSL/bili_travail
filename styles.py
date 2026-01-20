# third-party modules
from nicegui import ui

def page_styles():
    ui.add_head_html(
        """
        <style>
        @font-face {
            font-family: 'Custom Font';
            src: url('/static/fonts/custom-font.woff2') format('woff2'),
                url('/static/fonts/custom-font.woff') format('woff'),
                url('/static/fonts/custom-font.ttf') format('truetype');
            font-display: swap; /* 优化加载体验 */
            }

        body {
            font-family: "Custom Font", sans-serif;
            }
        </style>
    """,
        shared=True,
    )
