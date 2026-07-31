import orjson

from nicegui import ui
from libs import log
from libs import styles

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
                ui.label(str(value["num"]) + "个 / " + str(value["price"] * value["num"]) + "电池")
            ui.label("送礼用户")
            for i in value["user"]:
                ui.label(i)
            ui.separator()
        ui.label(f"总计：{sum([value['num'] for value in count.values()])}个礼物 / {int(sum([value['price'] * value['num'] for value in count.values()]))}电池")