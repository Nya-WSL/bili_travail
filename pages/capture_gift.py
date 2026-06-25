import os
import orjson
import datetime

from nicegui import ui, app
from libs import log
from libs import styles

logger = log.logger

# 与main.py共享的模块级变量
capture_challenge_gift_list_show = None
capture_gift_is_created = False
refresh_capture_gift = False


async def capture_gift_page(get_notes_func, init_config_func, base_config):
    """投喂挑战预览页面"""
    global capture_challenge_gift_list_show, capture_gift_is_created, refresh_capture_gift

    styles.page_styles()  # 加载自定义样式
    config = base_config.load()

    def check_gift_refresh():
        global refresh_capture_gift

        if not base_config.get("bool", "show_capture_gift_list", False):
            if scroll_card.visible:
                scroll_card.set_visibility(False)
        else:
            scroll_card.set_visibility(True)

        if refresh_capture_gift:
            refresh_capture_gift = False
            ui.navigate.reload()

    capture_gift_is_created = True

    if not os.path.exists("data/gifts_count.json") or not os.path.exists("data/gift_img.json"):
        if not base_config.get("general", "auth_code") is None:
            await init_config_func()

    with open("data/gifts_count.json", "rb") as f:
        gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

    with open("data/gift_img.json", "rb") as f:
        gift_img = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

    if os.path.exists("data/special_count.json"):
        with open("data/special_count.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
    else:
        special = {}

    with ui.card(align_items="center").classes("bg-transparent").style("box-shadow: None; left: 50%; transform: translate(-50%, 0%);"):
        with ui.row():
            ui.label("总计").classes("text-4xl").style(f"color: {config['color']['text_color']}").classes("text-5xl")  # type: ignore[index]
            ui.label().bind_text_from(app.storage.general, "gift_challenge_count").style(f"color: {config['color']['text_color']}").classes("text-5xl")  # type: ignore[index]
            ui.label().bind_text_from(app.storage.general, "gift_challenge_unit").style(f"color: {config['color']['text_color']}").classes("text-5xl")  # type: ignore[index]
            ui.label().bind_text_from(app.storage.general, "gift_challenge_text").style(f"color: {config['color']['text_color']}").classes("text-5xl")  # type: ignore[index]

        ui.separator()

        await get_notes_func()  # 获取公告信息

        if gifts != {}:
            for k, v in gifts.items():
                with ui.row().classes('w-full'):
                    with ui.avatar(color=None):
                        ui.image().bind_source_from(gift_img, k)
                    ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                    ui.space()
                    if v < 0:
                        ui.label(f"{int(v)}{app.storage.general['gift_challenge_unit']}").classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                    else:
                        ui.label(f"+{int(v)}{app.storage.general['gift_challenge_unit']}").classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]

        if special != {}:
            for k, v in special.items():
                if type(v) == list:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                        ui.space()
                        if v[1] < 0:
                            ui.label(f"{int(v[0])} ~ {int(v[1])}{app.storage.general['gift_challenge_unit']}").classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                        elif v[0] < 0 and v[1] != 0:
                            ui.label(f"{int(v[0])} ~ +{v[1]}{app.storage.general["gift_challenge_unit"]}").classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                        elif v[0] < 0 and v[1] == 0:
                            ui.label(f"{int(v[0])} ~ {v[1]}{app.storage.general["gift_challenge_unit"]}").classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                        elif v[0] == 0 and v[1] == 0:
                            ui.label(f"{v[0]} ~ {v[1]}{app.storage.general["gift_challenge_unit"]}").classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                        elif v[0] == 0 and v[1] != 0:
                            ui.label(f"{v[0]} ~ +{v[1]}{app.storage.general["gift_challenge_unit"]}").classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                        else:
                            ui.label(f"+{v[0]} ~ +{v[1]}{app.storage.general["gift_challenge_unit"]}").classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                else:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                        ui.space()
                        if v == "clear":
                            v = "清空"
                        if v == "double":
                            v = "加倍"
                        if v == "half":
                            v = "减半"
                        ui.label(v).classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]

        def capture_challenge_gift_list_show(name, gift, num, time, message):
            if not base_config.get("bool", "show_capture_gift_list", False):
                scroll_card.set_visibility(False)
            else:
                scroll_card.set_visibility(True)
                capture_gift_scroll.clear()

                if not os.path.exists("data/gift_history.json"):
                    gift_history = {
                        "cd": [],
                        "challenge": []
                    }
                    with open("data/gift_history.json", "wb+") as f:
                        f.write(orjson.dumps(gift_history, option=orjson.OPT_INDENT_2))

                with open("data/gift_history.json", "rb") as f:
                    gift_history = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
                with open("data/gift_img.json", "rb") as f:
                    gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

                gift_history["challenge"].append({
                    "name": name,
                    "gift": gift,
                    "num": num,
                    "rule": time,
                    "url": message.gift_icon if message else gifts.get(gift, ""),
                    "time": datetime.datetime.now().strftime('%H:%M:%S')
                })

                with open("data/gift_history.json", "wb+") as f:
                    f.write(orjson.dumps(gift_history, option=orjson.OPT_INDENT_2))

                with capture_gift_scroll:
                    for data in gift_history["challenge"][-int(config["num"]["capture_gift_list_number"]):]:  # pyright: ignore[reportIndexIssue, reportArgumentType]
                        with ui.row().classes("w-full"):
                            gift_user = data["name"]
                            gift_num = data["num"]
                            gift_rule = data["rule"]
                            gift_name = data["gift"]
                            gift_img = data["url"]

                            ui.label(f"{gift_user}").classes("text-xl font-extrabold")
                            with ui.avatar(color="").classes("w-6 h-6"):
                                if gift_name not in ["舰长", "提督", "总督"]:
                                    if message:
                                        ui.image(gift_img)
                                    else:
                                        ui.image(gifts.get(gift_name, ""))
                                else:
                                    ui.image(gifts.get(gift_name, ""))
                            ui.label(f"x{gift_num}").classes("text-xl font-extrabold")
                            ui.label(gift_rule).classes("text-xl font-extrabold")

                capture_gift_scroll.scroll_to(percent=1, duration=0.5)

        with ui.card(align_items="stretch").classes("bg-transparent w-full").style("box-shadow: None;") as scroll_card:
            with ui.scroll_area().classes('h-32 w-full') as capture_gift_scroll:
                ui.label().set_visibility(False)

    ui.timer(5, callback=lambda: check_gift_refresh())
