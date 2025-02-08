# Local Packages
import blive_crower
import gift as get_gift
from blivedm import blivedm
import blivedm.blivedm.models.web as web_models

# Third Party Packages
import os
import json
import shutil
import random
import hashlib
import asyncio
import aiohttp
import requests
import datetime
import platform
import http.cookies
from typing import *
from nicegui import ui, app
from datetime import timedelta

version = "0.19.0-web_dev"

# ================================
# 检查环境状态
# ================================

# 初始化NiceGUI
app.storage.general.indent = True  # 格式化storage
app.add_static_files('/static', 'static')   # 创建虚拟路径
refresh_capture_cd = False  # 初始倒计时化刷新状态
refresh_capture_gift = False  # 初始化投喂挑战刷新状态
b_connect_status = False # 初始化弹幕服务器连接状态
cd_status = False  # 初始化倒计时状态
inherit_status = False # 初始化重置继承倒计时状态

def format_seconds(seconds):
    """
    格式化时间
    :param seconds: 秒数
    """
    # 处理符号：正数加 `+`，负数加 `-`，0 不加符号
    if seconds > 0:
        sign = "+"
    elif seconds < 0:
        sign = "-"
    else:
        sign = ""
    # 取绝对值计算
    seconds = abs(seconds)
    # 转换为小时、分钟和秒，转化为整数型格式
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    # 格式化输出
    parts = []
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:  # 只有分钟 > 0 时才显示 "分"
        parts.append(f"{minutes}分")
    if seconds > 0 or (hours == 0 and minutes == 0):  # 有秒或时分均为 0 时，才显示秒
        parts.append(f"{seconds}秒")
    return sign + "".join(parts)  # 返回结果，注意是字符串形式

# 检查配置文件状态
# 如配置文件不存在，则注入示例文件/使用内置预设
if not os.path.exists("config.json"):
    if not os.path.exists("config.example.json"):
        with open("config.json", "w+", encoding="utf-8") as f:
            config = {
    "room_id": "",
    "port": 65000,
    "clean_cache": False,
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
    "local_text": False,
    "domain": ""
}
            json.dump(config, f, indent=4, ensure_ascii=False)
    else:
        shutil.copy("config.example.json", "config.json")

if not os.path.exists(".nicegui/storage-general.json"):
    app.storage.general["gift_challenge_count"] = 0
    app.storage.general["gift_challenge_unit"] = ""
    app.storage.general["gift_challenge_text"] = ""
    app.storage.general["countdown_time"] = 0

# 检查data文件夹状态
if not os.path.exists("data"):
    os.mkdir("data")

# ================================
# 初始化配置文件
# ================================

# 加载配置文件
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

port = config["port"]

GiftManager = get_gift.BiliGiftManager()

async def init_config():
    # 初始化gifts.json数据
    # 确保礼物数据文件存在，如果不存在，则先进行初始化礼物数据
    if not os.path.exists("data/gifts.json"):
        # 如果配置文件中包含房间号，则传入；否则会触发 init_gift
        room_id = config.get("room_id", "")

        # 如果配置文件中有room_id，则使用该房间号
        if room_id:
            html_content = await GiftManager.get_live_h5(room_id, h5_path=f"data/{room_id}.html", init=True)
            if not html_content:  # 若获取B站礼物数据失败，则从Nya-WSL服务器或本地注入方式写入
                GiftManager.init_gift("data/gift_img.json", "data/gifts.json", time=0)
            else:  # 格式化B站礼物数据为json
                await GiftManager.convert_h5_to_json(h5_path=f"data/{room_id}.html")
        else:
            # 如果没有room_id，则从Nya-WSL服务器或本地注入方式写入
            GiftManager.init_gift("data/gift_img.json", "data/gifts.json", time=0)

    # 初始化数据
    if not os.path.exists("data/special.json"):
        with open("data/special.json", "w+", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

    if not os.path.exists("data/gifts_count.json"):
        shutil.copy("data/gifts.json", "data/gifts_count.json")

    if not os.path.exists("data/special_count.json"):
        with open("data/special_count.json", "w+", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

asyncio.run(init_config())

# ================================
# 程序运行
# ================================

# 弹幕数据连接
async def start_handler():
    global client

    # 读入配置文件
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # 直播间ID的取值看直播间URL
    ROOM_ID = config["room_id"]

    # 这里填一个已登录账号的cookie的SESSDATA字段的值。不填也可以连接，但是收到弹幕的用户名会打码，UID会变成0
    SESSDATA = config["SESSDATA"]

    session: Optional[aiohttp.ClientSession] = None

    # 创建ws
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
        b_connect_switch.set_value(False)


# 获取礼物信息
class BiliHandler(blivedm.BaseHandler):
    heart_count = 0
    # 心跳数据
    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        self.heart_count += 1
        # print(f'[INFO] [{client.room_id}]-[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]: 触发心跳')
        if self.heart_count < 2:
            b_connect_switch.set_value(True)
            b_connect_switch.set_text("已连接弹幕服务器")
            # print(f"[INFO] 已成功连接至 {room_id.value}")
        print(f'[INFO] [{client.room_id}]-[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]: 触发心跳')


    # 礼物数据
    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        gift = message.gift_name
        num = message.num
        uname = message.uname
        result = ""
        if len(uname.split()) > 8:
            uname = gift.split()[0-5] + "..."

        self._on_gift_play(gift, num, uname)


    # 舰队数据
    def _on_user_toast_v2(self, client: blivedm.BLiveClient, message: web_models.UserToastV2Message):
        gift = message.guard_level
        num = message.num
        uname = message.username
        result = ""

        if gift == 1:
            gift = "总督"
        elif gift == 2:
            gift = "提督"
        elif gift == 3:
            gift = "舰长"
        else:
            gift = "神秘物种"

        if len(uname.split()) > 8:
            uname = gift.split()[0-5] + "..."

        self._on_gift_play(gift, num, uname)

    # ================================
    # 醒目留言
    # 待开发
    # ================================
    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
    #     print(f'[{client.room_id}] 醒目留言 ¥{message.price} {message.uname}：{message.message}')
        return {"price": message.price}

    # def _on_interact_word(self, client: blivedm.BLiveClient, message: web_models.InteractWordMessage):
    #     if message.msg_type == 1:
    #         print(f'[{client.room_id}] {message.username} 进入房间')


    # 收到礼物后执行函数
    def _on_gift_play(self, gift, num, uname):
        if b_connect_status:  # True则已连接至弹幕服务器
            if gift_challenge_switch.value:  # True则为投喂挑战开关为开状态
                # 检查投喂挑战数据文件是否存在
                if os.path.exists("data/gifts_count.json"):
                    with open("data/gifts_count.json", "r", encoding="utf-8") as f:
                        gifts = json.load(f)
                    with open("data/special_count.json", "r", encoding="utf-8") as f:
                        special = json.load(f)

                    # 如果礼物数据没有该礼物则写入
                    if gift not in gifts:
                        if gift not in special:
                            gifts[gift] = 0
                            with open("data/gifts_count.json", "w+", encoding="utf-8") as f:
                                json.dump(gifts, f, indent=4, ensure_ascii=False)

                    # 如果收到的礼物在special.json中
                    if gift in special:
                        if special[gift] == "double": # 加倍挑战
                            changed_num = int(gift_challenge_count.text) * (2 * int(num))
                            result = f"礼物：{gift}\n数量：{num}\n加减：{changed_num}\n总数量："
                            gift_list_show(uname, gift, num, f"{2 * int(num)}倍")
                        if special[gift] == "clear": # 清空挑战
                            changed_num = 0
                            result = f"礼物：{gift}\n数量：{num}\n加减：{changed_num - int(gift_challenge_count.text)}\n总数量："
                            gift_list_show(uname, gift, num, "清空")
                        if type(special[gift]) == list: # 随机挑战，只有随机的类型为list
                                # random_num = random.randint(special[gift][0], special[gift][1]) # 从列表第一位和第二位的范围内随机抽一个int值
                                # changed_num = int(gift_challenge_count.text) + (random_num * num) # 目前总数 + random_num生成的随机数
                            total_changed_num = 0
                            for i in range(num):
                                random_num = random.randint(special[gift][0], special[gift][1] + 1)
                                total_changed_num += random_num
                                i += 1
                            changed_num = int(gift_challenge_count.text) + total_changed_num
                            result = f"礼物：{gift}\n数量：{num}\n加减：{random_num}\n总数量："
                            gift_list_show(uname, gift, num, str(int(gifts[gift] * int(num))) + gift_play_unit_main.text)

                    # 如果收到的礼物不在special.json中
                    else:  
                        changed_num = (gifts[gift] * int(num)) + int(gift_challenge_count.text) # （设定的值 * 礼物数量） + 目前总数
                        result = f"礼物：{gift}\n数量：{num}\n总数量："
                        if gifts[gift] != 0:
                            gift_list_show(uname, gift, num, str(int(gifts[gift] * int(num))) + gift_play_unit_main.text)

                    gift_challenge_count.set_text(changed_num) # 将label的text设定为结果
                    gift_challenge_count.bind_text_to(app.storage.general, "gift_challenge_count") # 将结果写入storage
                    # print(result, changed_num)

            if cd_status:  # True则倒计时为启动状态
                if os.path.exists("data/gifts.json"):
                    with open("data/gifts.json", "r", encoding="utf-8") as f:
                        gifts = json.load(f)
                    with open("data/special.json", "r", encoding="utf-8") as f:
                        special = json.load(f)

                    tmp_time = countdown_timer.get_tmp_time() # 获取当前倒计时

                    if gift not in gifts:
                        if gift not in special:
                            gifts[gift] = 0
                            with open("data/gifts.json", "w+", encoding="utf-8") as f:
                                json.dump(gifts, f, indent=4, ensure_ascii=False)

                    if gift in special:
                        if special[gift] == "double":
                            changed_time = tmp_time * (2 * int(num))
                            result = [{"gift": gift}, {"num": num}, {"time": format_seconds(changed_time)}]
                            gift_list_show(uname, gift, num, f"{2 * int(num)}倍")

                        if special[gift] == "clear":
                            changed_time = 3
                            result = [{"gift": gift}, {"num": num}, {"time": format_seconds(changed_time - tmp_time)}]
                            gift_list_show(uname, gift, num, "清空")

                        if type(special[gift]) == list:
                            total_changed_time = 0
                            for i in range(num):
                                random_time = random.randint(special[gift][0], special[gift][1] + 1)
                                total_changed_time += random_time
                                i += 1
                            changed_time = tmp_time + total_changed_time
                            result = [{"gift": gift}, {"num": num}, {"time": format_seconds(random_time)}]
                            gift_list_show(uname, gift, num, format_seconds(total_changed_time))

                    else:
                        changed_time = (gifts[gift] * int(num)) + tmp_time
                        result = [{"gift": gift}, {"num": num}, {"time": format_seconds(gifts[gift] * int(num))}]
                        if gifts[gift] != 0:
                            gift_list_show(uname, gift, num, format_seconds(gifts[gift] * int(num)))

                    countdown_timer.set_time(changed_time) # 重设倒计时数据

# 倒计时类
class CountdownTimer:
    def __init__(self):
        self._remaining = timedelta(seconds=0)

    def get_tmp_time(self):
        '''
        获取倒计时剩余时间
        '''
        return self._remaining.seconds

    # 运行倒计时
    def start(self, hour, minute, second):
        global cd_status, inherit_status
        if cd_status:
            ui.notify("倒计时已在运行中", type="negative")

        elif inherit_status:
            cd_status = True
            self.timer = app.timer(1, self.update)
            # 设置按钮状态
            start_button.disable()
            cancel_button.enable()
            pause_button.enable()
            add_button.enable()
            sub_button.enable()
            cancel_button.set_text("停止")
            inherit_status = False

        elif hour == 0 and minute == 0 and second == 0:
            ui.notify("请输入时间", type="negative")

        else:
            cd_status = True # 设置倒计时运行状态
            self._remaining = timedelta(hours=hour, minutes=minute, seconds=second)
            self.timer = app.timer(1, self.update)
            # 重置时间输入框
            input_hour.set_value(0)
            input_minute.set_value(0)
            input_second.set_value(0)
            # 设置按钮状态
            start_button.disable()
            cancel_button.enable()
            pause_button.enable()
            add_button.enable()
            sub_button.enable()
            cancel_button.set_text("停止")

    def update(self):
        global cd_status
        if self._remaining > timedelta(seconds=0):
            self._remaining -= timedelta(seconds=1)
            time_badge.set_text(format_timer(self._remaining.seconds))
        else:
            cd_status = False
            self._remaining = timedelta(seconds=0)
            self.timer.cancel()
            time_badge.set_text("00:00:00")
            input_hour.set_value(0)
            input_minute.set_value(0)
            input_second.set_value(0)

        app.storage.general["countdown_time"] = self._remaining.seconds

    # 暂停倒计时
    def pause(self):
        global cd_status
        self.timer.active = False

        # 设置按钮状态
        resume_button.enable()
        pause_button.disable()
        add_button.disable()
        sub_button.disable()

        # 设置倒计时状态
        cd_status = False

    # 继续倒计时
    def resume(self):
        global cd_status
        self.timer.active = True

        # 设置按钮状态
        pause_button.enable()
        resume_button.disable()
        add_button.enable()
        sub_button.enable()

        # 设置倒计时状态
        cd_status = True

    # 停止倒计时
    def stop(self):
        global cd_status

        # 如果重置继承
        if inherit_status:
            app.storage.general["countdown_time"] = 0
            self._remaining = timedelta(seconds=0)
            time_badge.set_text("00:00:00")
            cancel_button.set_text("停止")
            cancel_button.disable()
        else:
            app.storage.general["countdown_time"] = 0
            self._remaining = timedelta(seconds=0)

            # 设置按钮状态
            start_button.enable()
            cancel_button.disable()
            pause_button.disable()
            resume_button.disable()
            add_button.disable()
            sub_button.disable()
            input_hour.set_value(0)
            input_minute.set_value(0)
            input_second.set_value(0)

            # 设置倒计时状态
            cd_status = False

    # 设置倒计时
    def set_time(self, time):
        self._remaining = timedelta(seconds=time)


# ================================
# GUI
# ================================

### 礼物设置

# 倒计时设置弹窗
def cd_setting_dialog():
    # 设置数值输入框是否允许可视/编辑
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

    # 确定按钮
    def run():
        global refresh_capture_cd
        with open("data/gifts.json", "r+", encoding="utf-8") as f:
            gifts = json.load(f)
        with open("data/special.json", "r", encoding="utf-8") as f:
            special = json.load(f)
        if gift_name.value == None or time.value < 0:
            if gift_name.value == None:
                ui.notify("请选择礼物", type="negative")
            if time.value < 0:
                ui.notify("时间不能是负数", type="negative")
        else:
            if status.value == "add":
                gifts[gift_name.value] = int(time.value)
                if gift_name.value in special:
                    special.pop(gift_name.value)
                result = f'添加成功，{gift_name.value} | {format_seconds(time.value)}'
            elif status.value == "sub":
                gifts[gift_name.value] = float(f"-{time.value}")
                if gift_name.value in special:
                    special.pop(gift_name.value)
                result = f'添加成功，{gift_name.value} | {format_seconds(time.value)}'
            elif status.value == "double":
                special[gift_name.value] = "double"
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                result = f'添加成功，{gift_name.value} | 加倍'
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
                        ui.notify("随机的值必须最小数<=最大数", type="negative")
                        return
                except TypeError:
                    ui.notify("随机的值为空", type="negative")
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                result = f'添加成功，{gift_name.value} | {format_seconds(min.value)} ~ {format_seconds(max.value)}随机'

            with open("data/gifts.json", "w+", encoding="utf-8") as f:
                json.dump(gifts, f, ensure_ascii=False, indent=4)
            with open("data/special.json", "w+", encoding="utf-8") as f:
                json.dump(special, f, ensure_ascii=False, indent=4)

            ui.notify(result, type="positive")
            refresh_capture_cd = True # 设置capture刷新状态
            cd_dialog.close() # 关闭弹窗

    # 重置按钮
    def reset():
        def double_check():
            global refresh_capture_cd
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
            refresh_capture_cd = True
            double_check_dialog.close()
            cd_dialog.close()

        with ui.dialog() as double_check_dialog, ui.card(align_items="center"):
            ui.label("是否确认重置所有礼物？")

            with ui.row():
                ui.button("确认重置", on_click=lambda: double_check())
                ui.button("取消重置", on_click=lambda: double_check_dialog.close())

        double_check_dialog.open()

    def delete():
        global refresh_capture_cd
        with open("data/gifts.json", "r+", encoding="utf-8") as f:
            gifts = json.load(f)
        with open("data/special.json", "r+", encoding="utf-8") as f:
            special = json.load(f)
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
        refresh_capture_cd = True # 设置capture刷新状态
        cd_dialog.close() # 关闭弹窗

    # 设置预览
    def gift_list_fun():
        def del_gift(is_special, k):
            global refresh_capture_cd
            with open("data/gifts.json", "r", encoding="utf-8") as f:
                gifts = json.load(f)
            with open("data/special.json", "r", encoding="utf-8") as f:
                special = json.load(f)

            if is_special:
                special.pop(k)
                with open("data/special.json", "w+", encoding="utf-8") as f:
                    json.dump(special, f, ensure_ascii=False, indent=4)
            else:
                gifts[k] = 0
                with open("data/gifts.json", "w+", encoding="utf-8") as f:
                    json.dump(gifts, f, ensure_ascii=False, indent=4)

            refresh_capture_cd = True
            cd_dialog.close()

        with open("data/gifts.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)
        with open("data/special.json", "r", encoding="utf-8") as f:
            special = json.load(f)
        ui.label("设置预览").classes("text-2xl text-blue").style("font-size: 20px")
        # ui.separator()
        for k,v in gifts.items():
            if config["show_zero"]: # 如果配置文件的"show_zero"为True，则显示值为0的礼物
                with ui.row().classes('w-full'):
                    ui.label(k)
                    ui.space()
                    ui.label(format_seconds(v))
            else:
                if v != 0:
                    with ui.row().classes('w-full'):
                        ui.label(k)
                        ui.space()
                        ui.label(format_seconds(v))
                        ui.button("删除", on_click=lambda k = k: del_gift(False, k))

        if special != {}: # 如果特殊礼物的数据不是空的
            for k,v in special.items():
                if type(v) == list:
                    with ui.row().classes('w-full'):
                        ui.label(k)
                        ui.space()
                        ui.label(f"{format_seconds(v[0])} ~ {format_seconds(v[1])}")
                        ui.button("删除", on_click=lambda k = k: del_gift(True, k))
                else:
                    with ui.row().classes('w-full'):
                        ui.label(k)
                        ui.space()

                        # 格式化输出
                        if v == "clear":
                            v = "清空"
                        if v == "double":
                            v = "加倍"
                        ui.label(v)
                        ui.button("删除", on_click=lambda k = k: del_gift(True, k))
        ui.separator() # 分割线

    # 弹窗
    with ui.dialog() as cd_dialog, ui.card(align_items="center"):
        with open("data/gifts.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)
        gift_list_fun()
        with ui.row(align_items="center"):
            gifts_name = []
            for k,v in gifts.items():
                gifts_name.append(k)
            gift_name = ui.select(label="礼物选择", options=gifts_name, with_input=True, clearable=True).style("width: 200px")

        status = ui.toggle(options={"add": "加时", "sub": "减时", "double": "加倍", "clear": "清空", "random": "随机"}, on_change=lambda: show()).classes('items-center')

        # 数值输入框
        with ui.row():
            min = ui.number("随机最小数(秒)", value=0)
            max = ui.number("随机最大数(秒)", value=0)
            time = ui.number(label="时长(秒)", value=0, min=0)
            time.set_visibility(False)
            min.set_visibility(False)
            max.set_visibility(False)

        # 按钮
        with ui.row():
            ui.button('提交', on_click=lambda: run())
            ui.button("删除", on_click=lambda: delete())
            ui.button("重置全部", on_click=lambda: reset())
            ui.button('关闭', on_click=lambda: cd_dialog.close())

    cd_dialog.open() # 打开弹窗

# 投喂挑战弹窗
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
        if gift_name.value == None or number.value < 0:
            if gift_name.value == None:
                ui.notify("请选择礼物", type="negative")
            if number.value < 0:
                ui.notify("数量不能是负数", type="negative")
        else:
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
                result = f'添加成功，{gift_name.value} | 加倍'
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
                        ui.notify("随机的值必须最小数<=最大数", type="negative")
                        return
                except TypeError:
                    ui.notify("随机的值为空", type="negative")
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
                result = f'添加成功，{gift_name.value} | {min.value} ~ {max.value}随机'

            with open("data/gifts_count.json", "w+", encoding="utf-8") as f:
                json.dump(gifts, f, ensure_ascii=False, indent=4)
            with open("data/special_count.json", "w+", encoding="utf-8") as f:
                json.dump(special, f, ensure_ascii=False, indent=4)
            ui.notify(result, type="positive")
            refresh_capture_gift = True
            gift_count_dialog.close()

    def reset():
        def double_check():
            global refresh_capture_gift
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
            refresh_capture_gift = True
            gift_count_dialog.close()

        with ui.dialog() as double_check_dialog, ui.card(align_items="center"):
            ui.label("是否确认重置所有礼物？")

            with ui.row():
                ui.button("确认重置", on_click=lambda: double_check())
                ui.button("取消重置", on_click=lambda: double_check_dialog.close())

        double_check_dialog.open()

    def delete():
        global refresh_capture_gift
        with open("data/gifts_count.json", "r+", encoding="utf-8") as f:
            gifts = json.load(f)
        with open("data/special_count.json", "r+", encoding="utf-8") as f:
            special = json.load(f)
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
        refresh_capture_gift = True # 设置capture刷新状态
        gift_count_dialog.close() # 关闭弹窗

    def gift_list_fun():
        def del_gift(is_special, k):
            global refresh_capture_gift
            with open("data/gifts_count.json", "r", encoding="utf-8") as f:
                gifts = json.load(f)
            with open("data/special_count.json", "r", encoding="utf-8") as f:
                special = json.load(f)

            if is_special:
                special.pop(k)
                with open("data/special_count.json", "w+", encoding="utf-8") as f:
                    json.dump(special, f, ensure_ascii=False, indent=4)
            else:
                gifts[k] = 0
                with open("data/gifts_count.json", "w+", encoding="utf-8") as f:
                    json.dump(gifts, f, ensure_ascii=False, indent=4)

            refresh_capture_gift = True
            gift_count_dialog.close()

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
                        if v <= 0:
                            ui.label(f"{int(v)}{gift_play_unit_main.text}")
                        elif v > 0:
                            ui.label(f"+{int(v)}{gift_play_unit_main.text}")
                        ui.button("删除", on_click=lambda k = k: del_gift(False, k))

        if special != {}:
            for k,v in special.items():
                if type(v) == list:
                    with ui.row().classes('w-full'):
                        ui.label(k)
                        ui.space()
                        if v[1] < 0:
                            ui.label(f"{int(v[0])} ~ {int(v[1])}{gift_play_unit_main.text}")
                        elif v[0] < 0 and v[1] != 0:
                            ui.label(f"{int(v[0])} ~ +{v[1]}{gift_play_unit_main.text}")
                        elif v[0] < 0 and v[1] == 0:
                            ui.label(f"{int(v[0])} ~ {v[1]}{gift_play_unit_main.text}")
                        elif v[0] == 0 and v[1] == 0:
                            ui.label(f"{v[0]} ~ {v[1]}{gift_play_unit_main.text}")
                        elif v[0] == 0 and v[1] != 0:
                            ui.label(f"{v[0]} ~ +{v[1]}{gift_play_unit_main.text}")
                        else:
                            ui.label(f"+{v[0]} ~ +{v[1]}{gift_play_unit_main.text}")
                        ui.button("删除", on_click=lambda k = k: del_gift(True, k))
                else:
                    with ui.row().classes('w-full'):
                        ui.label(k)
                        ui.space()
                        if v == "clear":
                            v = "清空"
                        if v == "double":
                            v = "加倍"
                        ui.label(v)
                        ui.button("删除", on_click=lambda k = k: del_gift(True, k))
        ui.separator()

    with ui.dialog() as gift_count_dialog, ui.card(align_items="center"):
        with open("data/gifts_count.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)

        gift_list_fun()
        with ui.row(align_items="center"):
            gifts_name = []
            for k,v in gifts.items():
                gifts_name.append(k)
            gift_name = ui.select(label="礼物选择", options=gifts_name, with_input=True, clearable=True).style("width: 200px")

        status = ui.toggle(options={"add": "加", "sub": "减", "double": "加倍", "clear": "清空", "random": "随机"}, on_change=lambda: show()).classes('items-center')
        with ui.row():
            min = ui.number("随机最小数", value=0)
            max = ui.number("随机最大数", value=0)
            number = ui.number(label="数量", value=0, min=0).style("width: 150px")

            # 自定义单位、项目输入框
            if gift_play_unit_main != "":
                gift_play_unit = ui.input("单位", value=gift_play_unit_main.text, on_change=lambda e: gift_play_unit_main.set_text(e.value)).bind_value_to(app.storage.general, "gift_challenge_unit")
            else:
                gift_play_unit = ui.input("单位", on_change=lambda e: gift_play_unit_main.set_text(e.value)).bind_value_to(app.storage.general, "gift_challenge_unit")
            if gift_play_text_main != "":
                gift_play_text = ui.input("项目", value=gift_play_text_main.text, on_change=lambda e: gift_play_text_main.set_text(e.value)).bind_value_to(app.storage.general, "gift_challenge_text")
            else:
                gift_play_text = ui.input("项目", on_change=lambda e: gift_play_text_main.set_text(e.value)).bind_value_to(app.storage.general, "gift_challenge_text")

            number.set_visibility(False)
            min.set_visibility(False)
            max.set_visibility(False)

        def change_challenge_count(status):
            def double_check():
                if status == "add":
                    app.storage.general["gift_challenge_count"] += 1
                elif status == "sub":
                    if app.storage.general["gift_challenge_count"] > 0:
                        app.storage.general["gift_challenge_count"] -= 1
                elif status == "reset":
                    app.storage.general["gift_challenge_count"] = 0

                double_check_dialog.close()

            with ui.dialog() as double_check_dialog, ui.card(align_items="center"):
                ui.label("是否确认重置计数？")

                with ui.row():
                    ui.button("确认重置", on_click=lambda: double_check())
                    ui.button("取消重置", on_click=lambda: double_check_dialog.close())

            double_check_dialog.open()

        with ui.row():
            ui.button('提交', on_click=lambda: run())
            ui.button("删除", on_click=lambda: delete())
            ui.button("重置全部", on_click=lambda: reset())
            ui.button("重置计数", on_click=lambda: change_challenge_count("reset"))
            # ui.button("加1", on_click=lambda: change_challenge_count("add"))
            # ui.button("减1", on_click=lambda: change_challenge_count("sub"))
            ui.button('关闭', on_click=lambda: gift_count_dialog.close())

    gift_count_dialog.open()

# 礼物设置弹窗
# with ui.dialog() as dialog, ui.card(align_items="center"):
#     with ui.row():
#         ui.button("加班设置", on_click=lambda: cd_setting_dialog())
#         ui.button("投喂挑战", on_click=lambda: gift_count_setting_dialog())
#     ui.button("关闭", on_click=lambda: dialog.close())

# dialog.open()

countdown_timer = CountdownTimer()


# 手动加时
def add_time():
    if cd_status:
        if input_hour.value != 0 or input_minute.value != 0 or input_second.value != 0:
            tmp_time = countdown_timer.get_tmp_time()
            changed_time = tmp_time + ((input_hour.value * 3600) + (input_minute.value * 60) + input_second.value) + 1 # 在视觉效果上倒计时被正确反馈，实际上多加了1s
            countdown_timer.set_time(changed_time)
    else:
        ui.notify("请先开始计时", type="negative")


# 手动减时
def sub_time():
    if cd_status:
        if input_hour.value != 0 or input_minute.value != 0 or input_second.value != 0:
            tmp_time = countdown_timer.get_tmp_time()
            changed_time = tmp_time - ((input_hour.value * 3600) + (input_minute.value * 60) + input_second.value) + 1  # 在视觉效果上倒计时被正确反馈，实际上少减了1s
            countdown_timer.set_time(changed_time)
    else:
        ui.notify("请先开始计时", type="negative")


# 保存配置
def save_config():
    with open("config.json", "w+", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# 获取当前设备ip
def get_public_ip():
    try:
        response = requests.get("https://api64.ipify.org?format=text", timeout=5)
        return response.text
    except requests.RequestException as e:
        return f"Error: {e}"

# 检查弹幕服务器连接状态
async def check_b_connect_status():
    global b_connect_status

    # 如果连接弹幕服务器开关为关且房间号不为空
    if b_connect_switch.value == False:
        if room_id.value == "":
            if not b_connect_status:
                b_connect_switch.set_value(False)
                return
            else:
                start_button.disable()
                gift_challenge_switch.disable()
                b_connect_status = False
                await client.stop_and_close() # 断开弹幕服务器ws连接并关闭blivedm客户端
                ui.notify("已断开连接，这通常是因为手动关闭了连接或房间号不正确")
                b_connect_switch.set_value(False)
                b_connect_switch.set_text("连接至弹幕服务器")
        else:
            start_button.disable()
            gift_challenge_switch.disable()
            b_connect_status = False
            await client.stop_and_close() # 断开弹幕服务器ws连接并关闭blivedm客户端
            ui.notify("已断开连接，这通常是因为手动关闭了连接或房间号不正确")
            b_connect_switch.set_value(False)
            b_connect_switch.set_text("连接至弹幕服务器")

    # 如果正在连接弹幕服务器
    if b_connect_switch.value == "null":
        if room_id.value == "":
            b_connect_switch.set_value(False)
            return

        if not b_connect_status:
            if config["SESSDATA"] == "":
                ui.notify("SESSDATA为空，历史礼物功能可能无法显示用户名", type="warning")
            asyncio.create_task(start_handler()) # 创建连接弹幕服务器协程
            b_connect_switch.set_value("null")
            b_connect_switch.set_text("尝试连接弹幕服务器")
            b_connect_status = True # 设置弹幕服务器连接状态
        else:
            b_connect_switch.set_value(True)

    # 如果连接弹幕服务器开关为开
    if b_connect_switch.value == True:
        if room_id.value == "": # 如果房间号为空
            ui.notify("请输入房间号", type="negative")
            b_connect_switch.set_value(False) # 重置开关为关
            return

        if b_connect_status:
            start_button.enable()
            gift_challenge_switch.enable()
        else:
            b_connect_switch.set_value("null")

# 打开界面预览弹窗
def open_capture():
    with ui.dialog() as dialog, ui.card(align_items="center"):
        ui.label("使用OBS捕捉浏览器源时请关闭预览窗口")
        ui.label("如OBS未刷新，请点击：浏览器源 → 刷新当前页面缓存")
        with ui.row():
            ui.button("加班预览", on_click=lambda: ui.navigate.to("/capture_cd", new_tab=True)).on(type="click", handler=lambda: dialog.close())
            ui.button("挑战预览", on_click=lambda: ui.navigate.to("/capture_gift", new_tab=True)).on(type="click", handler=lambda: dialog.close())
            ui.button("关闭", on_click=lambda: dialog.close())

    dialog.open()

# 更新礼物数据
async def refresh_gift():
    ROOM_ID = room_id.value
    if ROOM_ID == "":
        ui.notify("请先填入房间号！", type="negative")
    else:
        async def check_refresh():
            check_dialog.close()
            ui.notify("正在更新礼物数据，请稍后...", type="info")
            await asyncio.sleep(1)
            int(ROOM_ID) # 判断ROOM_ID是否是数字
            GiftManager.remove_h5_file(f"data/{ROOM_ID}.html") # 删除旧的h5文件
            html_content = await GiftManager.get_live_h5(ROOM_ID, f"data/{ROOM_ID}.html") # 爬取B站直播间数据
            # 如果成功爬取到数据则格式化礼物数据，否则让用户选择是否使用预设数据重置
            if html_content:
                # print("[INFO] 正在格式化数据...")
                await GiftManager.convert_h5_to_json(f"data/{ROOM_ID}.html")
                # print("[INFO] 礼物数据更新完成!")
                ui.notify("礼物数据更新完成", type="positive")
            else:
                # 重置本地数据
                def reset_gift_data():
                    try:
                        GiftManager.init_gift("data/gift_img.json", "data/gifts.json", time=0)
                        ui.notify("重置成功", type="negative")
                        reset_dialog.close()
                    except:
                        ui.notify("重置失败", type="positive")

                with ui.dialog() as reset_dialog, ui.card(align_items="center"):
                    with ui.row():
                        ui.label("更新礼物数据失败。是否重置本地数据？")
                    ui.button("确定", on_click=lambda: reset_gift_data())
                    ui.button("取消", on_click=lambda: reset_dialog.close())

                reset_dialog.open()

        with ui.dialog() as check_dialog, ui.card(align_items="center"):
            ui.label("请不要在倒计时和投喂挑战功能运行时更新。")
            ui.label("更新礼物数据前，请先暂停倒计时与投喂挑战。")
            ui.label("是否进行更新？")
            with ui.row():
                ui.button("确定", on_click=lambda: check_refresh())
                ui.button("取消", on_click=lambda: check_dialog.close())

        check_dialog.open()

# 倒计时预览
@ui.page("/capture_cd", title="倒计时 | bili_travail")
async def capture():
    # 检查是否需要刷新页面
    def check_cd_refresh():
        global refresh_capture_cd
        if refresh_capture_cd:
            refresh_capture_cd = False
            # ui.run_javascript(f'window.location.href += "?{refresh_time}";')
            ui.navigate.reload()

    # 初始化礼物列表
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)


    if not os.path.exists("data/gifts.json"):
        await init_config()
        await GiftManager.convert_h5_to_json(f"data/{config['room_id']}.html", write_img=False)

    with open("data/gifts.json", "r", encoding="utf-8") as f:
        gifts = json.load(f)


    if not os.path.exists("data/gift_img.json"):
        await init_config()
        await GiftManager.convert_h5_to_json(f"data/{config['room_id']}.html", write_time=False)

    with open("data/gift_img.json", "r", encoding="utf-8") as f:
        gift_img = json.load(f)


    if os.path.exists("data/special.json"):
        with open("data/special.json", "r", encoding="utf-8") as f:
            special = json.load(f)
    else:
        special = {}
    # ui.query('body').style(f'background: url("{random.choice(config["background_image"])}") 0px 0px/cover')

    # 创建预览界面
    with ui.card(align_items="center").classes("bg-transparent").style("box-shadow: None; left: 50%; transform: translate(-50%, 0%);"): # 居中、背景透明、取消卡片阴影、置顶居中
        ui.badge(outline=True, color="", text_color=config["color"]).bind_text_from(time_badge).classes("text-8xl") # 创建时钟
        ui.separator() # 分割线

        # 创建礼物列表
        for k,v in gifts.items():
            if config["show_zero"]:
                with ui.row().classes('w-full'):
                    with ui.avatar(color=None):
                        ui.image().bind_source_from(gift_img, k)
                    ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                    ui.space()
                    if v < 0:
                        ui.label(format_seconds(v)).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                    else:
                        ui.label(format_seconds(v)).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
            else:
                if v != 0:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        ui.space()
                        if v < 0:
                            ui.label(format_seconds(v)).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        else:
                            ui.label(format_seconds(v)).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
        if special != {}:
            for k,v in special.items():
                if type(v) == list:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        ui.space()
                        ui.label(f"{format_seconds(v[0])} ~ {format_seconds(v[1])}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                else:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        ui.space()
                        if v == "clear":
                            v = "清空"
                        if v == "double":
                            v = "加倍"
                        ui.label(v).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
    ui.timer(5, callback=lambda: check_cd_refresh())

# 投喂挑战预览
@ui.page("/capture_gift", title="投喂挑战 | bili_travail")
async def capture():
    def check_gift_refresh():
        global refresh_capture_gift
        if refresh_capture_gift:
            refresh_capture_gift = False
            # ui.run_javascript(f'window.location.href += "?{refresh_time}";')
            ui.navigate.reload()

    # 礼物列表
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)


    if not os.path.exists("data/gifts_count.json"):
        await init_config()
        await GiftManager.convert_h5_to_json(f"data/{config['room_id']}.html", write_img=False, time_path="data/gifts_count.json")

    with open("data/gifts_count.json", "r", encoding="utf-8") as f:
        gifts = json.load(f)


    if not os.path.exists("data/gift_img.json"):
        await init_config()
        await GiftManager.convert_h5_to_json(f"data/{config['room_id']}.html", write_time=False)

    with open("data/gift_img.json", "r", encoding="utf-8") as f:
        gift_img = json.load(f)


    if os.path.exists("data/special_count.json"):
        with open("data/special_count.json", "r", encoding="utf-8") as f:
            special = json.load(f)
    else:
        special = {}
    # ui.query('body').style(f'background: url("{random.choice(config["background_image"])}") 0px 0px/cover')
    with ui.card(align_items="center").classes("bg-transparent").style("box-shadow: None; left: 50%; transform: translate(-50%, 0%);"):
        with ui.row():
            ui.label("总计").classes("text-4xl").style(f"color: {config['color']}").classes("text-5xl")
            ui.label().bind_text_from(gift_challenge_count).style(f"color: {config['color']}").classes("text-5xl")
            ui.label().bind_text_from(gift_play_unit_main).style(f"color: {config['color']}").classes("text-5xl")
            ui.label().bind_text_from(gift_play_text_main).style(f"color: {config['color']}").classes("text-5xl")
        ui.separator()
        for k,v in gifts.items():
            if config["show_zero"]:
                with ui.row().classes('w-full'):
                    with ui.avatar(color=None):
                        ui.image().bind_source_from(gift_img, k)
                    ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                    ui.space()
                    ui.label(f"{v}{gift_play_unit_main.text}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
            else:
                if v != 0:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        ui.space()
                        if v < 0:
                            ui.label(f"{int(v)}{gift_play_unit_main.text}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        elif v > 0:
                            ui.label(f"+{int(v)}{gift_play_unit_main.text}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        else:
                            ui.label(f"{int(v)}{gift_play_unit_main.text}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
        if special != {}:
            for k,v in special.items():
                if type(v) == list:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        ui.space()
                        if v[1] < 0:
                            ui.label(f"{int(v[0])} ~ {int(v[1])}{gift_play_unit_main.text}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        elif v[0] < 0 and v[1] != 0:
                            ui.label(f"{int(v[0])} ~ +{v[1]}{gift_play_unit_main.text}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        elif v[0] < 0 and v[1] == 0:
                            ui.label(f"{int(v[0])} ~ {v[1]}{gift_play_unit_main.text}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        elif v[0] == 0 and v[1] == 0:
                            ui.label(f"{v[0]} ~ {v[1]}{gift_play_unit_main.text}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        elif v[0] == 0 and v[1] != 0:
                            ui.label(f"{v[0]} ~ +{v[1]}{gift_play_unit_main.text}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        else:
                            ui.label(f"+{v[0]} ~ +{v[1]}{gift_play_unit_main.text}").classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                else:
                    with ui.row().classes('w-full'):
                        with ui.avatar(color=None):
                            ui.image().bind_source_from(gift_img, k)
                        ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
                        ui.space()
                        if v == "clear":
                            v = "清空"
                        if v == "double":
                            v = "加倍"
                        ui.label(v).classes("text-3xl font-extrabold").style(f"color: {config['text_color']}")
    ui.timer(5, callback=lambda: check_gift_refresh())

# ================================
# GUI
# ================================

def format_timer(remaining_time):
    minute, second = divmod(remaining_time, 60)
    hour, minute = divmod(minute, 60)
    return "%02d:%02d:%02d" % (hour, minute, second)


@ui.page('/')
def page():
    if not app.storage.user.get('authenticated'):
        ui.navigate.to('/login')
    else:
        ui.navigate.to('/admin')


@ui.page('/login', title="登录 | bili_travail")
def page():
    def try_login() -> None:
        if not os.path.exists('users.json'):
            with open('users.json', 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
        with open('users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        try:
            if users[username.value] == hashlib.sha256(str(password.value).encode('utf-8')).hexdigest():
                app.storage.user.indent = True
                app.storage.user.update({'user': username.value, 'authenticated': True})
                ui.navigate.to(app.storage.user.get('referrer_path', '/admin'))
            else:
                ui.notify('密码错误', color='negative')
        except KeyError:
            ui.notify('账号错误或不存在', color='negative')

    ui.query('body').style('background: url("static/bg.jpg") 0px 0px/cover')
    with ui.card(align_items="center").classes('absolute-center'):
        ui.badge('B站加班姬', outline=True).classes('text-3xl')
        username = ui.input('账号').style("width: 150px")
        password = ui.input('密码', password=True, password_toggle_button=True).on('keydown.enter', try_login).style("width: 150px")
        ui.button('登录', on_click=try_login)

    with ui.page_sticky(position='bottom-left', x_offset=10, y_offset=10):
        ui.button(on_click=lambda: ui.navigate.to("/about"), icon='contact_support').props('fab')

# 创建管理面板
@ui.page('/admin', title="管理面板 | bili_travail")
def page():
    global time_badge, time_badge_inherit, gift_challenge_count, gift_play_unit_main, gift_play_text_main, input_hour, input_minute, input_second, gift_challenge_switch, start_button, pause_button, resume_button, cancel_button, add_button, sub_button, room_id, b_connect_switch, inherit_status, gift_list_show

    # def check_cd_status():
        

    ui.query('body').style(f'background: url("static/bg_server.png") 0px 0px/cover')

    if not app.storage.user.get('authenticated'):
        ui.navigate.to('/login')

    with ui.card(align_items="center").classes("absolute-center"):
        # time_badge = ui.badge(outline=True).bind_text_from(countdown_timer, 'remaining', lambda remaining: f'{format_timer(remaining.seconds)}').classes("text-9xl") # 创建时钟
        time_badge = ui.badge(text=format_timer(app.storage.general["countdown_time"]), outline=True).classes("text-9xl") # 创建时钟
        time_badge_inherit = ui.badge(0).bind_text_from(app.storage.general, "countdown_time") # 倒计时数据继承
        time_badge_inherit.set_visibility(False)
        gift_challenge_count = ui.badge(0).bind_text_from(app.storage.general, "gift_challenge_count") # 将结果写入storage) # 投喂挑战总数
        gift_play_unit_main = ui.label().bind_text_from(app.storage.general, "gift_challenge_unit") # 投喂挑战单位
        gift_play_text_main = ui.label().bind_text_from(app.storage.general, "gift_challenge_text") # 投喂挑战项目
        gift_challenge_count.set_visibility(False)
        gift_play_unit_main.set_visibility(False)
        gift_play_text_main.set_visibility(False)

        # 时间输入框
        with ui.row():
            input_hour = ui.number("时", value=0, min=0).style("width: 100px")
            input_minute = ui.number("分", value=0, min=0).style("width: 100px")
            input_second = ui.number("秒", value=0, min=0).style("width: 100px")
            gift_challenge_switch = ui.switch("启用投喂挑战", value=False, on_change=lambda: save_config())
            gift_challenge_switch.disable()

        # 倒计时按钮
        with ui.row():
            # Start button
            start_button = ui.button('开始', on_click=lambda: countdown_timer.start(input_hour.value, input_minute.value, input_second.value))
            start_button.disable()

            # Pause button
            pause_button = ui.button('暂停', on_click=lambda: countdown_timer.pause())
            pause_button.disable()

            # Resume button
            resume_button = ui.button('继续', on_click=lambda: countdown_timer.resume())
            resume_button.disable()

            # Stop button
            cancel_button = ui.button('停止', on_click=lambda: countdown_timer.stop())
            cancel_button.disable()

            # Add time Button
            add_button = ui.button("手动增加", on_click=lambda: add_time())
            add_button.disable()

            # Sub Time Button
            sub_button = ui.button("手动减少", on_click=lambda: sub_time())
            sub_button.disable()

        ui.separator()

        # 房间号和颜色输入框，颜色只在about和capture页面生效
        with ui.row():
            room_id = ui.input("房间号", on_change=lambda: save_config()).style("width: 120px").bind_value(config, "room_id") # 实时写入房间号到配置文件
            b_connect_switch = ui.switch("连接至弹幕服务器", on_change=lambda: check_b_connect_status()).props('checked-icon="check" color="green" unchecked-icon="clear"')

        ui.separator()

        with ui.row():
            ui.color_input(label="强调色", value="#5a85ad", on_change=lambda: save_config(), preview=config["color"]).style(f"width: 120px").bind_value(config, "color")
            ui.color_input(label="文字颜色", value="#000000", on_change=lambda: save_config(), preview=config["text_color"]).style(f"width: 120px").bind_value(config, "text_color")
            # Show gift list button
            ui.button("界面预览", on_click=lambda: open_capture())

        # 按钮组
        with ui.row():
            # Gift Setting button
            # ui.button("礼物设置", on_click=lambda: gift())
            ui.button("加班礼物设置", on_click=lambda: cd_setting_dialog())
            ui.button("投喂挑战设置", on_click=lambda: gift_count_setting_dialog())

        def gift_list_show(name, gift, num, time):
            with open("data/gift_img.json", "r", encoding="utf-8") as f:
                gifts = json.load(f)

            with gift_scroll:
                with ui.row().classes("w-full"):
                    ui.label(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {name} 赠送").classes("text-l")
                    with ui.avatar(color="").classes("w-6 h-6"):
                        ui.image(gifts[gift])
                    ui.label(f"{gift}x{num}").classes("text-l")
                    ui.label(time).classes("text-l")
            gift_scroll.scroll_to(percent=1, duration=0.5)

        with ui.card(align_items="stretch").classes("w-full"):
            with ui.scroll_area().classes('h-32') as gift_scroll:
                tmp_label = ui.label()
                tmp_label.set_visibility(False)

        with ui.row():
            # Update gift data button
            ui.button("更新礼物数据", on_click=lambda: refresh_gift())

        # obs源
        if config["domain"] == "":
            if platform.system() == "Windows" or platform.system() == "Darwin": # 如果是Windows或MacOS
                server = "127.0.0.1"
            else:
                server = get_public_ip()
        else:
            server = config["domain"]

        ui.label(f"OBS倒计时浏览器源URL：http://{server}:{port}/capture_cd")
        ui.label(f"OBS投喂挑战浏览器源URL：http://{server}:{port}/capture_gift")

    if app.storage.general["countdown_time"] != 0: # 如果存在可继承的倒计时
        countdown_timer.set_time(float(app.storage.general["countdown_time"]))
        inherit_status = True # 设置重置继承倒计时状态为True
        cancel_button.set_text("重置")
        cancel_button.enable()

    # about按钮
    with ui.page_sticky(position='bottom-left', x_offset=10, y_offset=10):
        ui.button(on_click=lambda: ui.navigate.to("/about"), icon='contact_support').props('fab')


# about页面
@ui.page('/about')
def _():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    ui.query('body').style(f'background: url("{random.choice(config["background_image"])}") 0px 0px/cover') # 设置背景图片

    # Card框
    with ui.card(align_items="center").classes("absolute-center"):
        ui.label(f"B站加班姬").classes("text-3xl").style(f"color: {config['text_color']}")
        ui.badge(f"v{version}", outline=True)

        # 私货
        def read_or_create_file(file_path, default_content):
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                with open(file_path, "w+", encoding="utf-8") as f:
                    f.write(default_content)
                return default_content

        text = requests.get("https://nya-wsl.com/bili_travail/chat_msg.json")
        text.encoding = "utf-8"
        if text.status_code == 200 or not config["local_text"]: # 如果请求状态为200且配置文件未启用本地文本
            if random.random() < 0.3:
                msg_index = []
                for k in text.json().keys():
                    msg_index.append(k)
                msg_index.remove("group_a")
                msg = text.json()[random.choice(msg_index)]
                ui.chat_message(msg["text_a"], avatar=blive_crower.get_bili_img("https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"), name="高橋はるき", text_html=True, sent=True)
                ui.chat_message(msg["text_b"], avatar=blive_crower.get_bili_img("https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"), name="狐日泽", text_html=True)
            else:
                ui.chat_message(text.json()["group_a"]["text_a"], avatar=blive_crower.get_bili_img("https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"), name="高橋はるき", text_html=True, sent=True)
                ui.chat_message(text.json()["group_a"]["text_b"], avatar=blive_crower.get_bili_img("https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"), name="狐日泽", text_html=True)
        else:
            text_a = read_or_create_file("data/text_a.txt", "代码没写完，哪有脸睡觉")
            text_b = read_or_create_file("data/text_b.txt", 'alias cd="sudo rm -rf"')

            ui.chat_message(text_a, avatar=blive_crower.get_bili_img("https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"), name="高橋はるき", text_html=True, sent=True)
            ui.chat_message(text_b, avatar=blive_crower.get_bili_img("https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"), name="狐日泽", text_html=True)

        # 项目介绍
        ui.html('A Project of <u><a href="https://nya-wsl.com" target="_blank">Nya-WSL</a></u>.')
        ui.html('Powered by <u><a href="https://nicegui.io" target="_blank">NiceGUI</a></u> - <u><a href="https://github.com/xfgryujk/blivedm" target="_blank">blivedm</a></u>.')
        ui.label("Copyright © 2025. All rights reserved. ")
        ui.separator()

        # 开发组成员显示
        with ui.row(align_items="center"):
            with ui.column(align_items="center"):
                ui.label("代码架构").classes("text-blue")
                with ui.link(target="https://space.bilibili.com/16748991", new_tab=True):
                    with ui.avatar():
                        ui.image(blive_crower.get_bili_img("https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"))
                ui.badge("高橋はるき", outline=True)
            with ui.column(align_items="center"):
                ui.label("代码开发").classes("text-blue")
                with ui.link(target="https://space.bilibili.com/8907402", new_tab=True):
                    with ui.avatar():
                        ui.image(blive_crower.get_bili_img("https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"))
                ui.badge("狐日泽", outline=True)
            with ui.column(align_items="center"):
                ui.label("特别感谢").classes("text-blue")
                with ui.link(target="https://space.bilibili.com/3546729020394298/", new_tab=True):
                    with ui.avatar():
                        ui.image(blive_crower.get_bili_img("https://i1.hdslb.com/bfs/face/1c90e9c3a52b13b898f4025a5282a394b09eeda0.jpg"))
                ui.badge("千蚀vita", outline=True)
        ui.separator()

        # 联系我们
        ui.label(f"联系我们").classes("text-2xl").style(f"color: {config['text_color']}")
        ui.link("GitHub Issues", "https://github.com/Nya-WSL/bili_travail/issues", True)
        ui.link("support@nya-wsl.com", "mailto:support@nya-wsl.com", True)
        ui.link("Nya-WSL服务与反馈群", "https://jq.qq.com/?_wv=1027&k=tSeB0sdy", True)
        ui.separator()
        # ui.html('关注<u><a href="https://space.bilibili.com/3546729020394298" target="_blank">千蚀vita</a></u>谢谢喵').classes("text-2xl text-white")
        ui.button("返回", on_click=lambda: ui.navigate.to("/"))

# 运行NiceGUI
ui.run(host="0.0.0.0", port=port, title="bili_travail", favicon="static/logo.ico", show=False, reconnect_timeout=15, storage_secret="vita")