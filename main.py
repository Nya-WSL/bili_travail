# Local Packages
import gift as get_gift
import log as cmd_log
from blivedm import blivedm
import blivedm.blivedm.models.web as web_models

# Third Party Packages
import os
import json
import shutil
import random
import asyncio
import aiohttp
import requests
import datetime
import http.cookies
from typing import *
from nicegui import ui, app

version = "0.15.0-beta"

app.storage.general.indent = True
app.add_static_files('/static', 'static')
port = 65000
refresh_capture_cd = False
refresh_capture_gift = False
b_connect_status = False
cd_status = False

# init config
if not os.path.exists("config.json"):
    if not os.path.exists("config.example.json"):
        with open("config.json", "w+", encoding="utf-8") as f:
            config = {
    "room_id": "",
    "show_zero": False,
    "SESSDATA": "",
    "background_image": [
        "https://nya-wsl.com/images/image001.png",
        "https://nya-wsl.com/images/image002.png",
        "https://nya-wsl.com/images/image003.png",
        "static/sample1.png",
        "static/sample2.png"
    ],
    "color": "#5898d4",
    "text_color": "#000000",
    "local_text": False
}
            json.dump(config, f, indent=4, ensure_ascii=False)
    else:
        shutil.copy("config.example.json", "config.json")

# init when the data folder does not exist
if not os.path.exists("data"):
    os.mkdir("data")
# download guard images
#     guard = {
#         "舰长": "guard-level-3.png",
#         "提督": "guard-level-2.png",
#         "总督": "guard-level-1.png"
# }
#     url = "https://nya-wsl.com/images/bili_travail/"
#     for k,v in guard.items():
#         try:
#             with open(f"data/{v}", "wb") as f:
#                 f.write(requests.get(url + k).content)
#         except:
#             print(f"Failed to download {url + k}")

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# init gift list
if not os.path.exists("data/gifts.json"):
    if config["room_id"] != "":
        room_id = config["room_id"]
        get_gift.get_gift(room_id, json_path="data/gifts_img.json", h5_path=f"data/{room_id}.html", write=False, write_time=True)
    else:
        get_gift.init_gift("data/gifts_img.json", "data/gifts.json")

# init special gift
if not os.path.exists("data/special.json"):
    with open("data/special.json", "w+", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

# cmd log
cmd_log.start_log(version)
cmd_log.version_log(version)

# handler
async def start_handler():
    global client

    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # 直播间ID的取值看直播间URL
    ROOM_ID = config["room_id"]

    # 这里填一个已登录账号的cookie的SESSDATA字段的值。不填也可以连接，但是收到弹幕的用户名会打码，UID会变成0
    SESSDATA = config["SESSDATA"]

    session: Optional[aiohttp.ClientSession] = None

    try:
        cookies = http.cookies.SimpleCookie()
        cookies['SESSDATA'] = SESSDATA
        cookies['SESSDATA']['domain'] = 'bilibili.com'

        session = aiohttp.ClientSession()
        session.cookie_jar.update_cookies(cookies)

        room_id = ROOM_ID
        client = blivedm.BLiveClient(room_id, session=session)
        handler = BiliHandler()
        client.set_handler(handler)
        client.start()

        try:
            await client.join()
        finally:
            await client.stop_and_close()

    finally:
        await session.close()


class BiliHandler(blivedm.BaseHandler):
    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        # print(f'[{client.room_id}]-[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]: 触发心跳')
        # heartbeat_status = f"[{client.room_id}]-[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]: 触发心跳"
        print(f'[INFO] [{client.room_id}]-[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]: 触发心跳')

    # def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
    #     print(f'[{client.room_id}] {message.uname}：{message.msg}')

    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        # print(f'[{client.room_id}] {message.uname} 赠送{message.gift_name}x{message.num}'
        #       f' （{message.coin_type}瓜子x{message.total_coin}）')

        gift = message.gift_name
        num = message.num
        result = ""
        if b_connect_status:
            if count_status_switch.value:
                if os.path.exists("data/gifts_count.json"):
                    with open("data/gifts_count.json", "r", encoding="utf-8") as f:
                        gifts = json.load(f)
                    with open("data/special_count.json", "r", encoding="utf-8") as f:
                        special = json.load(f)

                    if gift not in gifts:
                        if gift not in special:
                            gifts[gift] = 0
                            with open("data/gifts_count.json", "w+", encoding="utf-8") as f:
                                json.dump(gifts, f, indent=4, ensure_ascii=False)
                    if gift in special:
                        if special[gift] == "double":
                            changed_num = int(gift_count.text) * (2 * int(num))
                            result = f"礼物：{gift}\n数量：{num}\n加减：{changed_num}\n总数量："
                        if special[gift] == "clear":
                            changed_num = 0
                            result = f"礼物：{gift}\n数量：{num}\n加减：{changed_num - int(gift_count.text)}\n总数量："
                        if type(special[gift]) == list:
                                random_num = random.randint(special[gift][0], special[gift][1])
                                changed_num = int(gift_count.text) + random_num
                                result = f"礼物：{gift}\n数量：{num}\n加减：{random_num}\n总数量："
                    else:
                        changed_num = (gifts[gift] * int(num)) + int(gift_count.text)
                        result = f"礼物：{gift}\n数量：{num}\n总数量："
                    gift_count.set_text(changed_num)
                    print(result, changed_num)

            if cd_status:
                if os.path.exists("data/gifts_count.json"):
                    with open("data/gifts.json", "r", encoding="utf-8") as f:
                        gifts = json.load(f)
                    with open("data/special.json", "r", encoding="utf-8") as f:
                        special = json.load(f)

                    tmp_time = countdown_timer.get_tmp_time()

                    if gift not in gifts:
                        if gift not in special:
                            gifts[gift] = 0
                            with open("data/gifts.json", "w+", encoding="utf-8") as f:
                                json.dump(gifts, f, indent=4, ensure_ascii=False)
                    if gift in special:
                        if special[gift] == "double":
                            changed_time = tmp_time * (2 * int(num))
                            result = f"礼物：{gift}\n数量：{num}\n加时：{changed_time}秒\nurl:{message.gift_img}\n总时长："
                        if special[gift] == "clear":
                            changed_time = 3
                            result = f"礼物：{gift}\n数量：{num}\n加时：{changed_time - tmp_time}秒\nurl:{message.gift_img}\n总时长："
                        if type(special[gift]) == list:
                            random_time = random.randint(special[gift][0], special[gift][1])
                            changed_time = tmp_time + random_time
                            result = f"礼物：{gift}\n数量：{num}\n加时：{random_time}秒\nurl:{message.gift_img}\n总时长："
                    else:
                        changed_time = (gifts[gift] * int(num)) + tmp_time
                        result = f"礼物：{gift}\n数量：{num}\n加时：{gifts[gift] * int(num)}秒\n总时长："

                    countdown_timer.set_time(changed_time)
                    hour, minute = divmod(changed_time, 3600)
                    minute, second = divmod(minute, 60)
                    print(result, "%02d:%02d:%02d" % (hour, minute, second))


    # def _on_buy_guard(self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage):
    #     print(f'[{client.room_id}] {message.username} 上舰，guard_level={message.guard_level}')

    def _on_user_toast_v2(self, client: blivedm.BLiveClient, message: web_models.UserToastV2Message):
        with open("data/gifts.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)
        with open("data/special.json", "r", encoding="utf-8") as f:
            special = json.load(f)

        tmp_time = countdown_timer.get_tmp_time()
        gift = message.guard_level
        if gift == 1:
            gift = "总督"
        elif gift == 2:
            gift = "提督"
        elif gift == 3:
            gift = "舰长"
        else:
            gift = "神秘物种"
        num = message.num
        result = ""

        if b_connect_status:
            if gift not in gifts:
                if gift not in special:
                    gifts[gift] = 0
                    with open("data/gifts.json", "w+", encoding="utf-8") as f:
                        json.dump(gifts, f, indent=4, ensure_ascii=False)
            if gift in special:
                if special[gift] == "double":
                    changed_time = tmp_time * (2 * int(num))
                    result = f"礼物：{gift}\n数量：{num}\n加时：{changed_time}秒\nurl:{message.gift_img}\n总时长："
                if special[gift] == "clear":
                    changed_time = 3
                    result = f"礼物：{gift}\n数量：{num}\n加时：{changed_time - tmp_time}秒\nurl:{message.gift_img}\n总时长："
                if type(special[gift]) == list:
                    random_time = random.randint(special[gift][0], special[gift][1] + 1)
                    changed_time = tmp_time + random_time
                    result = f"礼物：{gift}\n数量：{num}\n加时：{random_time}秒\nurl:{message.gift_img}\n总时长："
            else:
                changed_time = (gifts[gift] * int(num)) + tmp_time
                result = f"礼物：{gift}\n数量：{num}\n加时：{gifts[gift] * int(num)}秒\n总时长："

            countdown_timer.set_time(changed_time)
            hour, minute = divmod(changed_time, 3600)
            minute, second = divmod(minute, 60)
            print(result, "%02d:%02d:%02d" % (hour, minute, second))


    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
    #     print(f'[{client.room_id}] 醒目留言 ¥{message.price} {message.uname}：{message.message}')
        return {"price": message.price}

    # def _on_interact_word(self, client: blivedm.BLiveClient, message: web_models.InteractWordMessage):
    #     if message.msg_type == 1:
    #         print(f'[{client.room_id}] {message.username} 进入房间')


class CountdownTimer:
    def __init__(self, start_time):
        self._start_time = start_time
        self._remaining_time = start_time
        self._paused = False
        self._running = False
        self._paused_event = asyncio.Event()
        self._paused_event.set()  # Initially not paused
        self._task = None

    # async def write_to_file(self):
    #     async with aiofiles.open("time.txt", "w+", encoding="utf-8") as f:
    #         await f.write(str(self._remaining_time))

    def get_tmp_time(self):
        return float(self._remaining_time)

    async def _run(self, label):
        while self._running and self._remaining_time > 0:
            if self._paused:
                await self._paused_event.wait()  # Wait until unpaused
            start_button.disable()
            cancel_button.enable()
            pause_button.enable()
            self._remaining_time -= 1
            # await self.write_to_file()
            minute, second = divmod(self._remaining_time, 60)
            hour, minute = divmod(minute, 60)
            label.set_text("%02d:%02d:%02d" % (hour, minute, second))
            print("剩余时间：%02d:%02d:%02d" % (hour, minute, second))
            await asyncio.sleep(1)

        if self._remaining_time <= 0:
            label.set_text("00:00:00")
            start_button.enable()
            cancel_button.disable()

    def start(self, label):
        global cd_status
        if not self._running:
            self._running = True
            self._remaining_time = self._start_time  # Reset to initial time
            if self._remaining_time != 0:
                self._task = asyncio.create_task(self._run(label))
                input_hour.set_value(0)
                input_minute.set_value(0)
                input_second.set_value(0)
                cd_status = True
            else:
                ui.notify("请输入时间", type="negative")

    async def pause(self):
        global cd_status
        if self._running and not self._paused:
            self._paused = True
            self._paused_event.clear()  # Pause the timer
            resume_button.enable()
            pause_button.disable()
            cd_status = False

    def resume(self):
        global cd_status
        if self._running and self._paused:
            self._paused = False
            self._paused_event.set()  # Resume the timer
            pause_button.enable()
            resume_button.disable()
            cd_status = True

    async def stop(self, label):
        global cd_status
        if self._running:
            self._running = False
            self._remaining_time = self._start_time  # Reset the timer
            if self._task:
                self._task.cancel()
            label.set_text("00:00:00")
            start_button.enable()
            cancel_button.disable()
            pause_button.disable()
            resume_button.disable()
            cd_status = False

    def set_time(self, time):
        # 如果计时器正在运行，首先停止它
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()

        # 更新起始时间和剩余时间
        self._start_time = time + 1
        self._remaining_time = time + 1

        # 更新 UI 上的显示
        hour, minute = divmod(self._remaining_time, 3600)
        minute, second = divmod(minute, 60)
        time_badge.set_text("%02d:%02d:%02d" % (hour, minute, second))

        # 如果计时器没有运行，则重新启动计时器
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run(time_badge))


# GUI
def gift():

    def cd_setting_dialog():
        def show():
            if status.value == "add" or status.value == "sub":
                time.set_visibility(True)
            else:
                time.set_visibility(False)
            if status.value == "random":
                min.set_visibility(True)
                max.set_visibility(True)
            else:
                min.set_visibility(False)
                max.set_visibility(False)
            if status.value == "double" or status.value == "clear" or status.value == "random":
                time.disable()
            else:
                time.enable()
            if status.value == "delete":
                time.disable()

        def run():
            global refresh_capture_cd
            with open("data/gifts.json", "r+", encoding="utf-8") as f:
                gifts = json.load(f)
            with open("data/special.json", "r", encoding="utf-8") as f:
                special = json.load(f)
            if status.value == "add":
                gifts[gift_name.value] = int(time.value)
                if gift_name.value in special:
                    special.pop(gift_name.value)
                result = f'添加成功，{gift_name.value} | +{time.value}秒'
            elif status.value == "sub":
                gifts[gift_name.value] = float(f"-{time.value}")
                if gift_name.value in special:
                    special.pop(gift_name.value)
                result = f'添加成功，{gift_name.value} | -{time.value}秒'
            elif status.value == "double":
                special[gift_name.value] = "double"
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                result = f'添加成功，{gift_name.value} | 双倍'
            elif status.value == "clear":
                special[gift_name.value] = "clear"
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                result = f'添加成功，{gift_name.value} | 清空(缓冲3秒)'
            elif status.value == "random":
                try:
                    if min.value <= max.value:
                        special[gift_name.value] = [int(min.value), int(max.value)]
                    else:
                        ui.notify("盲盒的值必须最小数<=最大数", type="negative")
                        return
                except TypeError:
                    ui.notify("盲盒的值为空", type="negative")
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                result = f'添加成功，{gift_name.value} | {min.value} ~ {max.value}秒随机'
            elif status.value == "delete":
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                if gift_name.value in special:
                    special.pop(gift_name.value)
                result = f'删除成功 → {gift_name.value}'

            with open("data/gifts.json", "w+", encoding="utf-8") as f:
                json.dump(gifts, f, ensure_ascii=False, indent=4)
            with open("data/special.json", "w+", encoding="utf-8") as f:
                json.dump(special, f, ensure_ascii=False, indent=4)
            ui.notify(result, type="positive")
            refresh_capture_cd = True
            cd_dialog.close()

        def reset():
            global refresh_capture
            with open("data/gifts.json", "r+", encoding="utf-8") as f:
                gifts = json.load(f)
            with open("data/special.json", "r+", encoding="utf-8") as f:
                special = json.load(f)
            for k in gifts.keys():
                gifts[k] = 0
            special = {}
            with open("data/gifts.json", "w+", encoding="utf-8") as f:
                json.dump(gifts, f, ensure_ascii=False, indent=4)
            with open("data/special.json", "w+", encoding="utf-8") as f:
                json.dump(special, f, ensure_ascii=False, indent=4)
            refresh_capture = True
            cd_dialog.close()

        def gift_list_fun():
            with open("data/gifts.json", "r", encoding="utf-8") as f:
                gifts = json.load(f)
            with open("data/special.json", "r", encoding="utf-8") as f:
                special = json.load(f)
            ui.label("设置预览").classes("text-2xl text-blue").style("font-size: 20px")
            # ui.separator()
            for k,v in gifts.items():
                if config["show_zero"]:
                    with ui.row().classes('w-full'):
                        ui.label(k)
                        ui.space()
                        ui.label(f"{v}秒")
                else:
                    if v != 0:
                        with ui.row().classes('w-full'):
                            ui.label(k)
                            ui.space()
                            ui.label(f"{v}秒")
            if special != {}:
                for k,v in special.items():
                    if type(v) == list:
                        with ui.row().classes('w-full'):
                            ui.label(k)
                            ui.space()
                            ui.label(f"{v[0]} ~ {v[1]}秒")
                    else:
                        with ui.row().classes('w-full'):
                            ui.label(k)
                            ui.space()
                            if v == "clear":
                                v = "清空"
                            if v == "double":
                                v = "加倍"
                            ui.label(v)
            ui.separator()

        with ui.dialog() as cd_dialog, ui.card(align_items="center"):
            with open("data/gifts.json", "r", encoding="utf-8") as f:
                gifts = json.load(f)
            gift_list_fun()
            with ui.row(align_items="center"):
                gifts_name = []
                for k,v in gifts.items():
                    gifts_name.append(k)
                gift_name = ui.select(label="礼物选择", options=gifts_name).style("width: 200px")

            status = ui.toggle(options={"add": "加时", "sub": "减时", "double": "加倍", "clear": "清空", "random": "盲盒", "delete": "删除"}, on_change=lambda: show()).classes('items-center')
            with ui.row():
                min = ui.number("盲盒最小数(秒)", value=0)
                max = ui.number("盲盒最大数(秒)", value=0)
                time = ui.number(label="时长(秒)", value=0)
                time.set_visibility(False)
                min.set_visibility(False)
                max.set_visibility(False)
            with ui.row():
                ui.button('提交', on_click=lambda: run())
                ui.button("重置", on_click=lambda: reset())
                ui.button('关闭', on_click=lambda: cd_dialog.close())

        cd_dialog.open()


    def gift_count_setting_dialog():
        global gift_play_unit
        global gift_play_text
        def show():
            if status.value == "add" or status.value == "sub":
                number.set_visibility(True)
            else:
                number.set_visibility(False)
            if status.value == "random":
                min.set_visibility(True)
                max.set_visibility(True)
            else:
                min.set_visibility(False)
                max.set_visibility(False)
            if status.value == "double" or status.value == "clear" or status.value == "random":
                number.disable()
            else:
                number.enable()
            if status.value == "delete":
                number.disable()

        def run():
            global refresh_capture_gift
            with open("data/gifts_count.json", "r+", encoding="utf-8") as f:
                gifts = json.load(f)
            with open("data/special_count.json", "r", encoding="utf-8") as f:
                special = json.load(f)
            if status.value == "add":
                gifts[gift_name.value] = int(number.value)
                if gift_name.value in special:
                    special.pop(gift_name.value)
                result = f'添加成功，{gift_name.value} | +{number.value}'
            elif status.value == "sub":
                gifts[gift_name.value] = float(f"-{number.value}")
                if gift_name.value in special:
                    special.pop(gift_name.value)
                result = f'添加成功，{gift_name.value} | -{number.value}'
            elif status.value == "double":
                special[gift_name.value] = "double"
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                result = f'添加成功，{gift_name.value} | 双倍'
            elif status.value == "clear":
                special[gift_name.value] = "clear"
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                result = f'添加成功，{gift_name.value} | 清空'
            elif status.value == "random":
                try:
                    if min.value <= max.value:
                        special[gift_name.value] = [int(min.value), int(max.value)]
                    else:
                        ui.notify("盲盒的值必须最小数<=最大数", type="negative")
                        return
                except TypeError:
                    ui.notify("盲盒的值为空", type="negative")
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                result = f'添加成功，{gift_name.value} | {min.value} ~ {max.value}随机'
            elif status.value == "delete":
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                if gift_name.value in special:
                    special.pop(gift_name.value)
                result = f'删除成功 → {gift_name.value}'

            with open("data/gifts_count.json", "w+", encoding="utf-8") as f:
                json.dump(gifts, f, ensure_ascii=False, indent=4)
            with open("data/special_count.json", "w+", encoding="utf-8") as f:
                json.dump(special, f, ensure_ascii=False, indent=4)
            ui.notify(result, type="positive")
            refresh_capture_gift = True
            gift_count_dialog.close()

        def reset():
            global refresh_capture
            with open("data/gifts_count.json", "r+", encoding="utf-8") as f:
                gifts = json.load(f)
            with open("data/special_count.json", "r+", encoding="utf-8") as f:
                special = json.load(f)
            for k in gifts.keys():
                gifts[k] = 0
            special = {}
            with open("data/gifts_count.json", "w+", encoding="utf-8") as f:
                json.dump(gifts, f, ensure_ascii=False, indent=4)
            with open("data/special_count.json", "w+", encoding="utf-8") as f:
                json.dump(special, f, ensure_ascii=False, indent=4)
            refresh_capture = True
            gift_count_dialog.close()

        def gift_list_fun():
            with open("data/gifts_count.json", "r", encoding="utf-8") as f:
                gifts = json.load(f)
            with open("data/special_count.json", "r", encoding="utf-8") as f:
                special = json.load(f)
            ui.label("设置预览").classes("text-2xl text-blue").style("font-size: 20px")
            # ui.separator()
            for k,v in gifts.items():
                if config["show_zero"]:
                    with ui.row().classes('w-full'):
                        ui.label(k)
                        ui.space()
                        ui.label(f"{v}")
                else:
                    if v != 0:
                        with ui.row().classes('w-full'):
                            ui.label(k)
                            ui.space()
                            ui.label(f"{v}")
            if special != {}:
                for k,v in special.items():
                    if type(v) == list:
                        with ui.row().classes('w-full'):
                            ui.label(k)
                            ui.space()
                            ui.label(f"{v[0]} ~ {v[1]}")
                    else:
                        with ui.row().classes('w-full'):
                            ui.label(k)
                            ui.space()
                            if v == "clear":
                                v = "清空"
                            if v == "double":
                                v = "加倍"
                            ui.label(v)
            ui.separator()

        with ui.dialog() as gift_count_dialog, ui.card(align_items="center"):
            if not os.path.exists("data/gifts_count.json"):
                with open("data/gifts.json", "r", encoding="utf-8") as f:
                    gifts = json.load(f)
                with open("data/gifts_count.json", "w+", encoding="utf-8") as f:
                    json.dump(gifts, f, ensure_ascii=False, indent=4)
            if not os.path.exists("data/special_count.json"):
                with open("data/special_count.json", "w+", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)

            with open("data/gifts_count.json", "r", encoding="utf-8") as f:
                gifts = json.load(f)

            gift_list_fun()
            with ui.row(align_items="center"):
                gifts_name = []
                for k,v in gifts.items():
                    gifts_name.append(k)
                gift_name = ui.select(label="礼物选择", options=gifts_name).style("width: 200px")

            status = ui.toggle(options={"add": "加", "sub": "减", "double": "加倍", "clear": "清空", "random": "盲盒", "delete": "删除"}, on_change=lambda: show()).classes('items-center')
            with ui.row():
                min = ui.number("盲盒最小数", value=0)
                max = ui.number("盲盒最大数", value=0)
                number = ui.number(label="数量", value=0).style("width: 150px")

                if gift_play_unit_main != "":
                    gift_play_unit = ui.input("单位", value=gift_play_unit_main.text, on_change=lambda e: gift_play_unit_main.set_text(e.value))
                else:
                    gift_play_unit = ui.input("单位", on_change=lambda e: gift_play_unit_main.set_text(e.value))
                if gift_play_text_main != "":
                    gift_play_text = ui.input("项目", value=gift_play_text_main.text, on_change=lambda e: gift_play_text_main.set_text(e.value))
                else:
                    gift_play_text = ui.input("项目", on_change=lambda e: gift_play_text_main.set_text(e.value))

                number.set_visibility(False)
                min.set_visibility(False)
                max.set_visibility(False)

            with ui.row():
                ui.button('提交', on_click=lambda: run())
                ui.button("重置", on_click=lambda: reset())
                ui.button('关闭', on_click=lambda: gift_count_dialog.close())

        gift_count_dialog.open()

    def refresh_gift():
        ROOM_ID = room_id.value
        if ROOM_ID == "":
            ui.notify("请先填入房间号！", type="negative")
        else:
            try:
                int(ROOM_ID)
                get_gift.get_gift(ROOM_ID, json_path="data/gifts_img.json", h5_path=f"data/{room_id}.html", write=False, write_time=True)
            except:
                ui.notify("房间号似乎有误？", type="negative")

    with ui.dialog() as dialog, ui.card(align_items="center"):
        with ui.row():
            ui.button("加班设置", on_click=lambda: cd_setting_dialog())
            ui.button("礼物统计", on_click=lambda: gift_count_setting_dialog())
            ui.button("刷新礼物", on_click=lambda: refresh_gift())
        ui.button("关闭", on_click=lambda: dialog.close())

    dialog.open()

def start_task():
    global countdown_timer
    countdown_timer = CountdownTimer((input_hour.value * 3600) + (input_minute.value * 60) + input_second.value)
    countdown_timer.start(time_badge)


def add_time():
    try:
        tmp_time = countdown_timer.get_tmp_time()
        changed_time = tmp_time + ((input_hour.value * 3600) + (input_minute.value * 60) + input_second.value)
        countdown_timer.set_time(changed_time)
    except NameError:
        ui.notify("请先开始计时", type="negative")


def sub_time():
    try:
        tmp_time = countdown_timer.get_tmp_time()
        changed_time = tmp_time - ((input_hour.value * 3600) + (input_minute.value * 60) + input_second.value)
        countdown_timer.set_time(changed_time)
    except NameError:
        ui.notify("请先开始计时", type="negative")

def save_config():
    with open("config.json", "w+", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def change_count_status():
    save_config()
    if count_status_switch.value:
        count_status_capture_label.set_visibility(True)
    else:
        count_status_capture_label.set_visibility(False)

async def check_b_connect_status():
    global b_connect_status
    if b_connect_switch.value:
        if room_id.value == "":
            ui.notify("请输入房间号", type="negative")
            b_connect_switch.set_value(False)
        else:
            start_button.enable()
            count_status_switch.enable()
            b_connect_status = True
            asyncio.create_task(start_handler())
            ui.notify("已连接", type="positive")
            print(f"[INFO] 已成功连接至{room_id.value}")
    elif not b_connect_switch.value and room_id.value != "":
        start_button.disable()
        count_status_switch.disable()
        b_connect_status = False
        await client.stop_and_close()
        ui.notify("已断开连接", type="positive")

def open_capture():
    with ui.dialog() as dialog, ui.card(align_items="center"):
        ui.label("使用OBS捕捉浏览器源时请关闭预览窗口")
        ui.label("如OBS未刷新，请点击：浏览器源 → 刷新当前页面缓存")
        with ui.row():
            ui.button("加班预览", on_click=lambda: ui.navigate.to("/capture_cd", new_tab=True)).on(type="click", handler=lambda: dialog.close())
            ui.button("统计预览", on_click=lambda: ui.navigate.to("/capture_gift", new_tab=True)).on(type="click", handler=lambda: dialog.close())
            ui.button("关闭", on_click=lambda: dialog.close())

    dialog.open()

@ui.page("/capture_cd", title="capture | bili_travail")
def capture():
    def check_cd_refresh():
        global refresh_capture_cd
        if refresh_capture_cd:
            refresh_capture_cd = False
            # ui.run_javascript(f'window.location.href += "?{refresh_time}";')
            ui.navigate.to("/capture_cd")

    # Gifts List
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    if os.path.exists("data/gifts.json"):
        with open("data/gifts.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)
    else:
        gifts = {}
    if os.path.exists("data/gift_img.json"):
        with open("data/gift_img.json", "r", encoding="utf-8") as f:
            gift_img = json.load(f)
    else:
        gift_img = get_gift.get_gift("data/gift_img.json", return_dict=True)
    if os.path.exists("data/special.json"):
        with open("data/special.json", "r", encoding="utf-8") as f:
            special = json.load(f)
    else:
        special = {}
    # ui.query('body').style(f'background: url("{random.choice(config["background_image"])}") 0px 0px/cover')
    with ui.card(align_items="center").classes("bg-transparent").style("box-shadow: None; left: 50%; transform: translate(-50%, 0%);"):
        ui.badge(outline=True, color="", text_color=config["color"]).bind_text_from(time_badge).classes("text-8xl")
        ui.separator()
        for k,v in gifts.items():
            if config["show_zero"]:
                with ui.row().classes('w-full'):
                    with ui.avatar(color=None):
                        ui.image().bind_source_from(gift_img, k)
                    ui.label(k).classes("text-2xl").style(f"color: {config['text_color']}")
                    ui.space()
                    ui.label(f"{v}秒").classes("text-2xl").style(f"color: {config['text_color']}")
            else:
                if v != 0:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-2xl").style(f"color: {config['text_color']}")
                        ui.space()
                        ui.label(f"{v}秒").classes("text-2xl").style(f"color: {config['text_color']}")
        if special != {}:
            for k,v in special.items():
                if type(v) == list:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-2xl").style(f"color: {config['text_color']}")
                        ui.space()
                        ui.label(f"{v[0]} ~ {v[1]}秒").classes("text-2xl").style(f"color: {config['text_color']}")
                else:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-2xl").style(f"color: {config['text_color']}")
                        ui.space()
                        if v == "clear":
                            v = "清空"
                        if v == "double":
                            v = "加倍"
                        ui.label(v).classes("text-2xl").style(f"color: {config['text_color']}")
    ui.timer(5, callback=lambda: check_cd_refresh())

@ui.page("/capture_gift", title="capture | bili_travail")
def capture():
    def check_gift_refresh():
        global refresh_capture_gift
        if refresh_capture_gift:
            refresh_capture_gift = False
            # ui.run_javascript(f'window.location.href += "?{refresh_time}";')
            ui.navigate.to("/capture_gift")

    # Gifts List
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    if os.path.exists("data/gifts_count.json"):
        with open("data/gifts_count.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)
    else:
        gifts = {}
    if os.path.exists("data/gift_img.json"):
        with open("data/gift_img.json", "r", encoding="utf-8") as f:
            gift_img = json.load(f)
    else:
        gift_img = get_gift.get_gift("data/gift_img.json", return_dict=True)
    if os.path.exists("data/special_count.json"):
        with open("data/special_count.json", "r", encoding="utf-8") as f:
            special = json.load(f)
    else:
        special = {}
    # ui.query('body').style(f'background: url("{random.choice(config["background_image"])}") 0px 0px/cover')
    with ui.card(align_items="center").classes("bg-transparent").style("box-shadow: None; left: 50%; transform: translate(-50%, 0%);"):
        with ui.row():
            ui.label("总计").classes("text-4xl").style(f"color: {config['color']}").classes("text-5xl")
            ui.label().bind_text_from(gift_count).style(f"color: {config['color']}").classes("text-5xl")
            ui.label().bind_text_from(gift_play_unit_main).style(f"color: {config['color']}").classes("text-5xl")
            ui.label().bind_text_from(gift_play_text_main).style(f"color: {config['color']}").classes("text-5xl")
        ui.separator()
        for k,v in gifts.items():
            if config["show_zero"]:
                with ui.row().classes('w-full'):
                    with ui.avatar(color=None):
                        ui.image().bind_source_from(gift_img, k)
                    ui.label(k).classes("text-2xl").style(f"color: {config['text_color']}")
                    ui.space()
                    ui.label(f"{v}{gift_play_unit_main.text}").classes("text-2xl").style(f"color: {config['text_color']}")
            else:
                if v != 0:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-2xl").style(f"color: {config['text_color']}")
                        ui.space()
                        ui.label(f"{v}{gift_play_unit_main.text}").classes("text-2xl").style(f"color: {config['text_color']}")
        if special != {}:
            for k,v in special.items():
                if type(v) == list:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-2xl").style(f"color: {config['text_color']}")
                        ui.space()
                        ui.label(f"{v[0]} ~ {v[1]}{gift_play_unit_main.text}").classes("text-2xl").style(f"color: {config['text_color']}")
                else:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-2xl").style(f"color: {config['text_color']}")
                        ui.space()
                        if v == "clear":
                            v = "清空"
                        if v == "double":
                            v = "加倍"
                        ui.label(v).classes("text-2xl").style(f"color: {config['text_color']}")
    ui.timer(5, callback=lambda: check_gift_refresh())

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
with ui.card(align_items="center").classes("absolute-center"):
    # Countdown Control Panel
    time_badge = ui.badge("00:00:00", outline=True).classes("text-9xl")
    gift_count = ui.badge("0")
    gift_play_unit_main = ui.label()
    gift_play_text_main = ui.label()
    gift_count.set_visibility(False)
    gift_play_unit_main.set_visibility(False)
    gift_play_text_main.set_visibility(False)

    with ui.row():
        input_hour = ui.number("时", value=0, min=0).style("width: 100px")
        input_minute = ui.number("分", value=0, min=0).style("width: 100px")
        input_second = ui.number("秒", value=0, min=0).style("width: 100px")

    with ui.row():
        room_id = ui.input("房间号", on_change=lambda: save_config()).style("width: 120px").bind_value(config, "room_id")
        ui.color_input(label="倒计时颜色", value="#5a85ad", on_change=lambda: save_config(), preview=config["color"]).style(f"width: 120px").bind_value(config, "color")
        ui.color_input(label="文字颜色", value="#000000", on_change=lambda: save_config(), preview=config["text_color"]).style(f"width: 120px").bind_value(config, "text_color")

    with ui.row():
        # Start button
        start_button = ui.button('开始加班', on_click=lambda: start_task())
        start_button.disable()

        # Pause button
        pause_button = ui.button('暂停加班', on_click=lambda: countdown_timer.pause())
        pause_button.disable()

        # Resume button
        resume_button = ui.button('继续加班', on_click=lambda: countdown_timer.resume())
        resume_button.disable()

        # Stop button
        cancel_button = ui.button('停止加班', on_click=lambda: countdown_timer.stop(time_badge))
        cancel_button.disable()

    with ui.row():
        # Add time Button
        ui.button("增加时长", on_click=lambda: add_time())

        # Sub Time Button
        ui.button("减少时长", on_click=lambda: sub_time())

        # Gift Setting button
        ui.button("礼物设置", on_click=lambda: gift())
        
        # Show gift list button
        ui.button("界面预览", on_click=lambda: open_capture())

    with ui.row():
        b_connect_switch = ui.switch("连接弹幕服务器", value=False, on_change=lambda: check_b_connect_status())
        count_status_switch = ui.switch("启用礼物统计", value=False, on_change=lambda: change_count_status())
        count_status_switch.disable()

    ui.label(f"OBS倒计时浏览器源URL：http://127.0.0.1:{port}/capture_cd")
    count_status_capture_label = ui.label(f"OBS礼物统计浏览器源URL：http://127.0.0.1:{port}/capture_gift")
    count_status_capture_label.set_visibility(False)

with ui.page_sticky(position='bottom-right', x_offset=10, y_offset=10):
    ui.button(on_click=lambda: ui.navigate.to("/about"), icon='contact_support').props('fab')

@ui.page('/about')
def _():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    ui.query('body').style(f'background: url("{random.choice(config["background_image"])}") 0px 0px/cover')
    with ui.card(align_items="center").classes("absolute-center"):
        ui.label(f"B站加班姬").classes("text-3xl").style(f"color: {config['text_color']}")
        ui.badge(f"v{version}", outline=True)

        text = requests.get("https://nya-wsl.com/bili_travail/chat_msg.json")
        text.encoding = "utf-8"
        if text.status_code == 200 or not config["local_text"]:
            if random.random() < 0.3:
                msg_index = []
                for k in text.json().keys():
                    msg_index.append(k)
                msg_index.remove("group_a")
                msg = text.json()[random.choice(msg_index)]
                ui.chat_message(msg["text_a"], avatar="https://q1.qlogo.cn/g?b=qq&s=100&nk=1357515696", name="高橋はるき", text_html=True, sent=True)
                ui.chat_message(msg["text_b"], avatar="https://q1.qlogo.cn/g?b=qq&s=100&nk=1095530930", name="狐日泽", text_html=True)
            else:
                ui.chat_message(text.json()["group_a"]["text_a"], avatar="https://q1.qlogo.cn/g?b=qq&s=100&nk=1357515696", name="高橋はるき", text_html=True, sent=True)
                ui.chat_message(text.json()["group_a"]["text_b"], avatar="https://q1.qlogo.cn/g?b=qq&s=100&nk=1095530930", name="狐日泽", text_html=True)
        else:
            if os.path.exists("data/text_a.txt"):
                with open("data/text_a.txt", "r", encoding="utf-8") as f:
                    text_a = f.read()
            else:
                text_a = "代码没写完，哪有脸睡觉"
                with open("data/text_a.txt", "w", encoding="utf-8") as f:
                    f.write(text_a)

            if os.path.exists("data/text_b.txt"):
                with open("data/text_b.txt", "r", encoding="utf-8") as f:
                    text_b = f.read()
            else:
                text_a = 'alias cd="sudo rm -rf"'
                with open("data/text_b.txt", "w", encoding="utf-8") as f:
                    f.write(text_b)

            ui.chat_message(text_a, avatar="https://q1.qlogo.cn/g?b=qq&s=100&nk=1357515696", name="高橋はるき", text_html=True, sent=True)
            ui.chat_message(text_b, avatar="https://q1.qlogo.cn/g?b=qq&s=100&nk=1095530930", name="狐日泽", text_html=True)

        ui.html('A Project of <u><a href="https://nya-wsl.com" target="_blank">Nya-WSL</a></u>.')
        ui.html('Powered by <u><a href="https://nicegui.io" target="_blank">NiceGUI</a></u> - <u><a href="https://github.com/xfgryujk/blivedm" target="_blank">blivedm</a></u>.')
        ui.label("Copyright © 2025. All rights reserved. ")
        ui.separator()
        with ui.row():
            with ui.column(align_items="center"):
                with ui.link(target="https://space.bilibili.com/16748991", new_tab=True):
                    with ui.avatar():
                        ui.image("https://q1.qlogo.cn/g?b=qq&s=100&nk=1357515696")
                ui.badge("高橋はるき", outline=True)
            with ui.column(align_items="center"):
                with ui.link(target="https://space.bilibili.com/8907402", new_tab=True):
                    with ui.avatar():
                        ui.image("https://q1.qlogo.cn/g?b=qq&s=100&nk=1095530930")
                ui.badge("狐日泽", outline=True)
        ui.separator()
        ui.label(f"联系我们").classes("text-2xl").style(f"color: {config['text_color']}")
        ui.link("GitHub Issues", "https://github.com/Nya-WSL/bili_travail/issues", True)
        ui.link("support@nya-wsl.com", "mailto:support@nya-wsl.com", True)
        ui.link("Nya-WSL服务与反馈群", "https://jq.qq.com/?_wv=1027&k=tSeB0sdy", True)
        ui.separator()
        # ui.html('关注<u><a href="https://space.bilibili.com/3546729020394298" target="_blank">千蚀vita</a></u>谢谢喵').classes("text-2xl text-white")
        ui.button("返回", on_click=lambda: ui.navigate.to("/"))

ui.run(port=port, title=f"bili_travail | {version}", favicon="static/logo.ico", reload=False, show=True)