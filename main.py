# Local Packages
from blivedm import blivedm
import blivedm.blivedm.models.web as web_models

# Third Party Packages
import os
import json
import shutil
import random
import asyncio
import aiohttp
import datetime
import http.cookies
from typing import *
from nicegui import ui, app, native

version = "0.10.1-beta"

app.storage.general.indent = True
app.add_static_files('/static', 'static')
port = native.find_open_port(65000, 65525)

if not os.path.exists("config.json"):
    if not os.path.exists("config.example.json"):
        with open("config.json", "w+", encoding="utf-8") as f:
            config = {
    "room_id": "",
    "show_zero": False,
    "SESSDATA": "",
    "background_image": [
        "https://nya-wsl.com/images/image01.jpg",
        "static/sample.png",
        "static/sample2.png"
    ]
}
            json.dump(config, f, indent=4, ensure_ascii=False)
    else:
        shutil.copy("config.example.json", "config.json")

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
        print(f'[{client.room_id}] [{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]: 心跳')

    # def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
    #     print(f'[{client.room_id}] {message.uname}：{message.msg}')

    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        # print(f'[{client.room_id}] {message.uname} 赠送{message.gift_name}x{message.num}'
        #       f' （{message.coin_type}瓜子x{message.total_coin}）')
        with open("gifts.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)
        with open("special.json", "r", encoding="utf-8") as f:
            special = json.load(f)

        tmp_time = countdown_timer.get_tmp_time()
        gift = message.gift_name
        num = message.num
        result = ""

        if gift not in gifts:
            if gift not in special:
                gifts[gift] = 0
                with open("gifts.json", "w+", encoding="utf-8") as f:
                    json.dump(gifts, f, indent=4, ensure_ascii=False)
        if gift in special:
            if special[gift] == "double":
                changed_time = tmp_time * int(num + 1)
                result = f"礼物：{gift}\n数量：{num}\n加时：{changed_time}秒\nurl:{message.gift_img}\n总时长："
            if special[gift] == "clear":
                changed_time = 3
                result = f"礼物：{gift}\n数量：{num}\n加时：{changed_time - tmp_time}秒\nurl:{message.gift_img}\n总时长："
            if type(special[gift]) == list:
                changed_time = random.randint(special[gift][0], special[gift][1])
                result = f"礼物：{gift}\n数量：{num}\n加时：{changed_time}秒\nurl:{message.gift_img}\n总时长："
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
        with open("gifts.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)
        with open("special.json", "r", encoding="utf-8") as f:
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

        if gift not in gifts:
            if gift not in special:
                gifts[gift] = 0
                with open("gifts.json", "w+", encoding="utf-8") as f:
                    json.dump(gifts, f, indent=4, ensure_ascii=False)
        if gift in special:
            if special[gift] == "double":
                changed_time = tmp_time * int(num)
                result = f"礼物：{gift}\n数量：{num}\n加时：{changed_time}秒\nurl:{message.gift_img}\n总时长："
            if special[gift] == "clear":
                changed_time = 3
                result = f"礼物：{gift}\n数量：{num}\n加时：{changed_time - tmp_time}秒\nurl:{message.gift_img}\n总时长："
            if type(special[gift]) == list:
                changed_time = random.randint(special[gift][0], special[gift][1])
                result = f"礼物：{gift}\n数量：{num}\n加时：{changed_time}秒\nurl:{message.gift_img}\n总时长："
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
            await asyncio.sleep(1)

        if self._remaining_time <= 0:
            label.set_text("00:00:00")
            start_button.enable()
            cancel_button.disable()

    def start(self, label):
        if not self._running:
            self._running = True
            self._remaining_time = self._start_time  # Reset to initial time
            if self._remaining_time != 0:
                self._task = asyncio.create_task(self._run(label))
                input_hour.set_value(0)
                input_minute.set_value(0)
                input_second.set_value(0)
                asyncio.create_task(start_handler())
            else:
                ui.notify("请输入时间", type="negative")

    async def pause(self):
        if self._running and not self._paused:
            self._paused = True
            self._paused_event.clear()  # Pause the timer
            resume_button.enable()
            pause_button.disable()
            await client.stop_and_close()

    def resume(self):
        if self._running and self._paused:
            self._paused = False
            self._paused_event.set()  # Resume the timer
            pause_button.enable()
            resume_button.disable()
            asyncio.create_task(start_handler())

    async def stop(self, label):
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
            await client.stop_and_close()

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
    def show():
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

    def run():
        with open("gifts.json", "r+", encoding="utf-8") as f:
            gifts = json.load(f)
        with open("special.json", "r", encoding="utf-8") as f:
            special = json.load(f)
        if status.value == "add":
            gifts[gift_name.value] = int(time.value)
        elif status.value == "sub":
            gifts[gift_name.value] = float(f"-{time.value}")
        elif status.value == "double":
            special[gift_name.value] = "double"
        elif status.value == "clear":
            special[gift_name.value] = "clear"
        elif status.value == "random":
            if min.value != 0 and max.value != 0:
                special[gift_name.value] = [min.value, max.value]
        with open("gifts.json", "w+", encoding="utf-8") as f:
            json.dump(gifts, f, ensure_ascii=False, indent=4)
        with open("special.json", "w+", encoding="utf-8") as f:
            json.dump(special, f, ensure_ascii=False, indent=4)
        ui.notify(f'添加成功，{gift_name.value} | {time.value}秒', type="positive")


    with ui.dialog() as dialog, ui.card(align_items="center"):
        if os.path.exists("gifts.json"):
            with open("gifts.json", "r", encoding="utf-8") as f:
                gifts = json.load(f)
        else:
            gifts = {
                    "牛哇牛哇": 0
                    }
            with open("gifts.json", "w+", encoding="utf-8") as f:
                json.dump(gifts, f, ensure_ascii=False, indent=4)
        if os.path.exists("special.json"):
            with open("special.json", "r", encoding="utf-8") as f:
                special = json.load(f)
        else:
            special = {
                    "舰长": "clear",
                    "我星永恒": "double",
                    "情书": [-60, 60]
                    }
            with open("special.json", "w+", encoding="utf-8") as f:
                json.dump(special, f, ensure_ascii=False, indent=4)
        with ui.row(align_items="center"):
            gifts_name = []
            for k,v in gifts.items():
                gifts_name.append(k)
            gift_name = ui.select(label="礼物", options=gifts_name, value=gifts_name[0])
            time = ui.number(label="时长(秒)", value=0)
        status = ui.toggle(options={"add": "加时", "sub": "减时", "double": "加倍", "clear": "清空", "random": "盲盒"}, value="add", on_change=lambda: show()).classes('items-center')
        with ui.row():
            min = ui.number("盲盒最小数(秒)", value=0)
            max = ui.number("盲盒最大数(秒)", value=0)
            min.set_visibility(False)
            max.set_visibility(False)
        with ui.row():
            ui.button('添加', on_click=lambda: run())
            ui.button('关闭', on_click=lambda: dialog.close())

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

def save_room_id():
    with open("config.json", "w+", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

@ui.refreshable
@ui.page("/capture", title="capture | bili_travail")
# obs: 宽度最高325px
def capture():
    # Gifts List
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    with open("gifts.json", "r", encoding="utf-8") as f:
        gifts = json.load(f)
    if os.path.exists("special.json"):
        with open("special.json", "r", encoding="utf-8") as f:
            special = json.load(f)
    else:
        special = {}
    # ui.query('body').style(f'background: url("{random.choice(config["background_image"])}") 0px 0px/cover')
    # with ui.card(align_items="center").classes("absolute-center bg-transparent"):
    ui.badge(outline=True).bind_text_from(time_badge).classes("text-7xl w-full items-center")
    for k,v in gifts.items():
        if config["show_zero"]:
            with ui.row().classes('w-full'):
                ui.label(k).classes("text-2xl")
                ui.space()
                ui.label(f"{v}秒").classes("text-2xl")
        else:
            if v != 0:
                with ui.row().classes('w-full'):
                    ui.label(k).classes("text-2xl")
                    ui.space()
                    ui.label(f"{v}秒").classes("text-2xl")
    if special != {}:
        for k,v in special.items():
            if type(v) == list:
                with ui.row().classes('w-full'):
                    ui.label(k).classes("text-2xl")
                    ui.space()
                    ui.label(f"{v[0]}秒 - {v[1]}秒").classes("text-2xl")
            else:
                with ui.row().classes('w-full'):
                    ui.label(k).classes("text-2xl")
                    ui.space()
                    if v == "clear":
                        v = "清空"
                    if v == "double":
                        v = "加倍"
                    ui.label(v).classes("text-2xl")
        # i = iter(gift_list_rows[0].items())
        # while True:
        #     d = dict(itertools.islice(i, 3))
        #     if d == {}:
        #         break
        #     rows_list = []
        #     rows_list.append(d)
        #     ui.table(rows=rows_list).classes("bg-transparent")


with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
with ui.card(align_items="center").classes("absolute-center"):
    # Countdown Control Panel
    time_badge = ui.badge("00:00:00", outline=True).classes("text-9xl")
    with ui.row():
        room_id = ui.input("房间号", on_change=lambda: save_room_id()).bind_value(config, "room_id")
        input_hour = ui.number("时", value=0, min=0)
        input_minute = ui.number("分", value=0, min=0)
        input_second = ui.number("秒", value=0, min=0)

    with ui.row():
        # Start button
        start_button = ui.button('开始加班', on_click=lambda: start_task())

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
        ui.button("礼物列表", on_click=lambda: ui.navigate.to("capture", new_tab=True))
    ui.label(f"obs浏览器源：http://127.0.0.1:{port}/capture")

with ui.page_sticky(position='bottom-right', x_offset=10, y_offset=10):
    ui.button(on_click=lambda: ui.navigate.to("/about"), icon='contact_support').props('fab')

@ui.page('/about')
def _():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    ui.query('body').style(f'background: url("{random.choice(config["background_image"])}") 0px 0px/cover')
    with ui.card(align_items="center").classes("absolute-center"):
        ui.label(f"B站加班姬").classes("text-3xl text-blue")
        ui.badge(f"v{version}", outline=True)
        ui.chat_message('代码没写完，哪有脸睡觉', avatar="https://q1.qlogo.cn/g?b=qq&s=100&nk=1357515696", name="高橋はるき", text_html=True, sent=True)
        ui.chat_message('alias cd="sudo rm -rf"', avatar="https://q1.qlogo.cn/g?b=qq&s=100&nk=1095530930", name="狐日泽", text_html=True)
        ui.html('A Project of <u><a href="https://nya-wsl.com">Nya-WSL</a></u>.')
        ui.html('Powered by <u><a href="https://nicegui.io">NiceGUI</a></u> - <u><a href="https://github.com/xfgryujk/blivedm">blivedm</a></u>.')
        ui.label("Copyright © 2025. All rights reserved. ")
        ui.separator()
        with ui.row():
            with ui.column(align_items="center"):
                with ui.link(target="https://space.bilibili.com/16748991"):
                    with ui.avatar():
                        ui.image("https://q1.qlogo.cn/g?b=qq&s=100&nk=1357515696")
                ui.badge("高橋はるき", outline=True)
            with ui.column(align_items="center"):
                with ui.link(target="https://space.bilibili.com/8907402"):
                    with ui.avatar():
                        ui.image("https://q1.qlogo.cn/g?b=qq&s=100&nk=1095530930")
                ui.badge("狐日泽", outline=True)
        ui.separator()
        ui.button("返回", on_click=lambda: ui.navigate.to("/"))

ui.run(port=port, title=f"bili_travail | {version}", favicon="static/logo.ico", reload=False, show=True)