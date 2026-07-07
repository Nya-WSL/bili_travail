import os
import re
import orjson
import datetime
import itertools

from nicegui import ui, app

from libs import log
from libs import gift
from libs import styles
from libs.format import format_cd, format_seconds, sort_dict

logger = log.logger

# 与main.py共享的模块级变量
capture_cd_gift_list_show = None
capture_cd_rank_list_show = None
capture_cd_is_created = False
refresh_capture_cd = False

async def capture_cd_page(get_notes_func, init_config_func, base_config, gift_manager: gift.BiliGiftManager):
    """倒计时预览页面"""
    global capture_cd_gift_list_show, capture_cd_rank_list_show, capture_cd_is_created, refresh_capture_cd

    styles.page_styles()  # 加载自定义样式

    config = base_config.load()

    # 检查是否需要刷新页面
    def check_cd_refresh():
        global refresh_capture_cd

        if refresh_capture_cd:
            if not base_config.get("bool", "show_capture_gift_list", False):
                if scroll_card.visible:
                    scroll_card.set_visibility(False)
            else:
                scroll_card.set_visibility(True)

            refresh_capture_cd = False
            gift_card.clear()

            with gift_card:
                with open("data/gifts.json", "rb") as f:
                    gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

                if os.path.exists("data/special.json"):
                    with open("data/special.json", "rb") as f:
                        special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
                else:
                    special = {}

                if gifts != {}:
                    gifts = sort_dict(dictionary=gifts, sort_within_type=True)
                    for k, v in gifts.items():
                        gift_element("normal", k, v)

                if special != {}:
                    special = sort_dict(dictionary=special, type_order=[str, list], sort_within_type=True)
                    for k, v in special.items():
                        if type(v) == list:
                            gift_element("list", k, v)
                        else:
                            gift_element("special", k, v)

    def change_gift_element(v_type, k, v):
        """修改礼物列表UI元素"""
        with open("data/gift_img.json", "rb") as f:
            gift_img = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        if v_type == "normal":
            gift_img_avatar.set_source(gift_img.get(k, ""))
            k_label.set_text(k)
            v_label.set_text(format_seconds(v))
            k_label.classes(replace="text-3xl font-extrabold")
            v_label.classes(replace="text-3xl font-extrabold")

        if v_type == "list":
            gift_img_avatar.set_source(gift_img.get(k, ""))
            k_label.set_text(k)
            v_label.set_text(f"{format_seconds(v[0])} ~ {format_seconds(v[1])}")
            k_label.classes(replace="text-base font-extrabold")
            v_label.classes(replace="text-base font-extrabold")

        if v_type == "special":
            if v == "clear":
                v = "清空"
            if v == "double":
                v = "加倍"
            if v == "half":
                v = "减半"

            gift_img_avatar.set_source(gift_img.get(k, ""))
            k_label.set_text(k)
            v_label.set_text(v)
            k_label.classes(replace="text-3xl font-extrabold")
            v_label.classes(replace="text-3xl font-extrabold")

    def short_gift_element():
        """将礼物列表处理为简洁模式"""
        with open("data/gifts.json", "rb") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/special.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        gifts.update(special)  # 合并加减时和特殊玩法
        gifts = sort_dict(dictionary=gifts, sort_within_type=True)  # 对字典按值的类型排序
        k = next(iter(gifts))  # 字典第一个礼物名称
        v = gifts[k]  # 字典第一个礼物的值
        cycle_items = itertools.cycle(gifts.items())

        def change(items):
            k, v = next(items)
            if type(v) == list:
                change_gift_element("list", k, v)
            elif isinstance(v, (int, float)):
                change_gift_element("normal", k, v)
            else:
                change_gift_element("special", k, v)

        # 初始化第一个礼物元素
        if type(v) == list:
            gift_element("list", k, v)
        elif isinstance(v, (int, float)):
            gift_element("normal", k, v)
        else:
            gift_element("special", k, v)

        def timer_handler() -> ui.timer:
            timer = ui.timer(base_config.get("num", "short_time", 5), lambda: change(cycle_items))  # pyright: ignore[reportArgumentType]
            return timer

        timer_handler()
        app.on_disconnect(lambda: timer_handler().cancel())

    def gift_element(v_type, k, v):
        global gift_img_avatar, k_label, v_label

        with open("data/gift_img.json", "rb") as f:
            gift_img = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        if v_type == "normal":
            with ui.row().classes('w-full'):
                with ui.avatar(color=None):
                    gift_img_avatar = ui.image(gift_img.get(k, ""))
                k_label = ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                ui.space()
                v_label = ui.label(format_seconds(v)).classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]

        if v_type == "list":
            with ui.row().classes('w-full'):
                with ui.avatar(color=None):
                    gift_img_avatar = ui.image(gift_img.get(k, ""))
                k_label = ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                ui.space()
                v_label = ui.label(f"{format_seconds(v[0])} ~ {format_seconds(v[1])}").classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]

        if v_type == "special":
            with ui.row().classes('w-full'):
                with ui.avatar(color=None):
                    gift_img_avatar = ui.image(gift_img.get(k, ""))
                k_label = ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                ui.space()
                if v == "clear":
                    v = "清空"
                if v == "double":
                    v = "加倍"
                if v == "half":
                    v = "减半"
                v_label = ui.label(v).classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]

    capture_cd_is_created = True

    if not os.path.exists("data/gifts.json") or not os.path.exists("data/gift_img.json"):
        if base_config.get("general", "auth_code") != None:
            await init_config_func()

    with open("data/gifts.json", "rb") as f:
        gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

    if os.path.exists("data/special.json"):
        with open("data/special.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
    else:
        special = {}

    with ui.card(align_items="center").classes("bg-transparent w-full").style("box-shadow: None; left: 50%; transform: translate(-50%, 0%);"):
        if not config['bool']['borderless_cd']:  # type: ignore[index]
            ui.badge(outline=True, color="", text_color=config['color']['time_color']).bind_text_from(app.storage.general, "countdown_time", lambda x: format_cd(x)).classes("text-8xl")  # type: ignore[arg-type]
        else:
            ui.label().bind_text_from(app.storage.general, "countdown_time", lambda x: format_cd(x)).classes("text-8xl").style(f"color: {config['color']['time_color']}")  # type: ignore[index]

        ui.separator()

        await get_notes_func()

        if not base_config.get("bool", "short_list", False):
            with ui.card(align_items="center").classes("bg-transparent").style("box-shadow: None; max-width: 710px;") as gift_card:
                if gifts != {}:
                    gifts = sort_dict(dictionary=gifts, sort_within_type=True)
                    for k, v in gifts.items():
                        gift_element("normal", k, v)

                if special != {}:
                    special = sort_dict(dictionary=special, type_order=[str, list], sort_within_type=True)
                    for k, v in special.items():
                        if type(v) == list:
                            gift_element("list", k, v)
                        else:
                            gift_element("special", k, v)
        else:
            short_gift_element()

        def capture_cd_gift_list_show(name, gift, num, time, message):
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

                if "倍" in time:
                    tmp_time = app.storage.general["countdown_time"]
                    if re.search(r"-2\^(\d+)倍", time):
                        for _ in range(num):
                            tmp_time -= tmp_time / 2
                        time = format_seconds(float(f"-{app.storage.general['countdown_time'] - tmp_time}"))
                    else:
                        for _ in range(num):
                            tmp_time += tmp_time
                        time = format_seconds(tmp_time - app.storage.general["countdown_time"])

                gift_history["cd"].append({
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
                    for data in gift_history["cd"][-int(config["num"]["capture_gift_list_number"]):]:  # pyright: ignore[reportIndexIssue, reportArgumentType]
                        with ui.row().classes("w-full"):
                            gift_user = data["name"]
                            gift_num = data["num"]
                            gift_rule = data["rule"]
                            gift_name = data["gift"]
                            gift_img = data["url"]
                            gift_time = data["time"]

                            ui.label(f"{gift_time}").classes("text-xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                            ui.label(f"{gift_user}").classes("text-xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                            with ui.avatar(color="").classes("w-6 h-6"):
                                if gift_name not in ["舰长", "提督", "总督"]:
                                    if message:
                                        ui.image(gift_img)
                                    else:
                                        ui.image(gifts.get(gift_name, ""))
                                else:
                                    ui.image(gifts.get(gift_name, ""))
                            ui.label(f"x{gift_num}").classes("text-xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                            ui.space()
                            ui.label(gift_rule).classes("text-xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]

                capture_gift_scroll.scroll_to(percent=1, duration=0.5)
                capture_cd_rank_list_show()

        def capture_cd_rank_list_show():
            def rule_to_seconds(rule):
                """将规则字符串转换为秒数"""
                if not isinstance(rule, str):
                    return None
                rule = rule.strip()

                sign = 1
                if rule.startswith('-'):
                    sign = -1
                    rule = rule[1:]
                elif rule.startswith('+'):
                    rule = rule[1:]

                hours = 0
                minutes = 0
                seconds = 0

                hour_match = re.search(r'(\d+)(?:小时|时)', rule)
                if hour_match:
                    hours = int(hour_match.group(1))
                    rule = rule.replace(hour_match.group(0), '')

                minute_match = re.search(r'(\d+)分', rule)
                if minute_match:
                    minutes = int(minute_match.group(1))
                    rule = rule.replace(minute_match.group(0), '')

                second_match = re.search(r'(\d+)秒', rule)
                if second_match:
                    seconds = int(second_match.group(1))
                    rule = rule.replace(second_match.group(0), '')

                remaining = rule.strip()
                if remaining.isdigit():
                    seconds += int(remaining)

                total_seconds = hours * 3600 + minutes * 60 + seconds
                return sign * total_seconds

            if not base_config.get("bool", "show_capture_rank_list", False):
                rank_card.set_visibility(False)
            else:
                rank_card.set_visibility(True)
                capture_rank_scroll.clear()

            if not os.path.exists("data/gift_history.json"):
                return

            with open("data/gift_history.json", "rb") as f:
                gift_history = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

            rank_dict = {}

            for i in gift_history["cd"]:
                if not i["name"] in rank_dict:
                    rank_dict[i["name"]] = 0
                seconds = rule_to_seconds(i["rule"])
                if seconds is not None:
                    rank_dict[i["name"]] += seconds

            with capture_rank_scroll:
                trophy_color = ["#FFD43B", "#C0C0C0", "#CD7F32"]
                for name, seconds in sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)[:3]:
                    with ui.row().classes("w-full"):
                        ui.icon("emoji_events", size="30px", color=trophy_color[0])
                        trophy_color.pop(0)
                        ui.label(f"{name}").classes("text-xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                        ui.space()
                        ui.label(format_seconds(seconds)).classes("text-xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]

            capture_rank_scroll.scroll_to(percent=1, duration=0.5)

        with ui.card(align_items="stretch").classes("bg-transparent w-full").style("box-shadow: None; max-width: 350px;") as rank_card:
            with ui.scroll_area().classes('h-40 w-full') as capture_rank_scroll:
                ui.label().set_visibility(False)

        capture_cd_rank_list_show()

        with ui.card(align_items="stretch").classes("bg-transparent w-full").style("box-shadow: None; max-width: 450px;") as scroll_card:
            with ui.scroll_area().classes('h-32 w-full') as capture_gift_scroll:
                ui.label().set_visibility(False)

    ui.timer(5, callback=lambda: check_cd_refresh())
