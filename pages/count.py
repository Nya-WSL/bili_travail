import orjson

from nicegui import ui
from libs import log
from libs import styles
from libs.i18n import t

logger = log.logger

def count_page():
    styles.page_styles() # 加载自定义样式
    ui.query('body').style(f'background: url("static/bg_vita.png") fixed')
    try:
        with open("data/gift_statistics.json", "rb") as f:
            count = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        if count == {}:
            raise Exception("No data")
    except Exception as e:
        logger.warning(f"读取 gift_statistics 失败，使用占位数据: {e}")
        count = {
            "占位礼物": {
                "num": 0,
                "price": 0,
                "user": ["user1", "user2"]
            }
        }

    with ui.card(align_items="center").classes("w-80").style("top: 50%; left: 50%; transform: translate(-50%);"):
    # with ui.scroll_area().classes('absolute-center w-80 h-96'):
        for gift, value in count.items():
            with ui.row():
                ui.label(gift + ": ")
                ui.label(t("count.gift_unit", num=value["num"], price=value["price"] * value["num"]))
            ui.label(t("count.senders"))
            for i in value["user"]:
                ui.label(i)
            ui.separator()
        ui.label(t("count.total", num=sum([value['num'] for value in count.values()]), price=int(sum([value['price'] * value['num'] for value in count.values()]))))