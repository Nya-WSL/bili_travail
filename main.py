# Local Packages
import ping
import bili_api

import gift as get_gift
import update as travail_update
import gift_mapping as gift_map
import bili_auth_web as bili_auth
import blivedm.blivedm.models.web as web_models

from log import logger
from blivedm import blivedm
from changelog import changelog

# Third Party Packages
import os
import re
import json
import shutil
import random
import psutil
import cpuinfo
import asyncio
import aiohttp
import requests
import datetime
import traceback
import http.cookies
from typing import *
from nicegui import ui, app

version = "0.31.6-alpha"
logger.debug("version: {}", version)

if os.path.exists("lines.txt"):
    with open("lines.txt", "r", encoding="utf-8") as f:
        app.storage.general["lines"] = f.read()

if app.storage.general.get("lines", 0) == 0:
    app.storage.general["lines"] = 0

# ================================
# 检查环境状态
# ================================

# 初始化NiceGUI
# asyncio.run(app.storage.general.initialize())
app.storage.general.indent = True  # 格式化storage
app.add_static_files('/static', 'static')   # 创建虚拟路径

refresh_capture_cd = False  # 初始化倒计时刷新状态
refresh_capture_gift = False  # 初始化投喂挑战刷新状态
b_connect_status = False # 初始化弹幕服务器连接状态
cd_status = False  # 初始化倒计时状态
reset_inherit_status = False # 初始化重置继承倒计时状态
capture_cd_is_created = False # 初始化倒计时页面状态
capture_gift_is_created = False # 初始化投喂挑战页面状态

# 检查data文件夹状态
if not os.path.exists("data"):
    os.mkdir("data")

# 移除残留的更新包
if os.path.exists("update.bat"):
    os.remove("update.bat")
if os.path.exists("cache"):
    shutil.rmtree("cache")

if os.path.exists("data/gift_history.json"):
    if not os.path.exists("data/history"):
        os.mkdir("data/history")
    shutil.move("data/gift_history.json", f"data/history/{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
if os.path.exists("data/gift_statistics.json"):
    if not os.path.exists("data/statistics"):
        os.mkdir("data/statistics")
    shutil.move("data/gift_statistics.json", f"data/statistics/{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
if os.path.exists("data/blind_box_value.json"):
    if not os.path.exists("data/blind_box"):
        os.mkdir("data/blind_box")
    shutil.move("data/blind_box_value.json", f"data/blind_box/{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json")

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

example_config = {
    "room_id": "",
    "host": "127.0.0.1",
    "port": 65000,
    "SESSDATA": "",
    "background_image": [
        "https://nya-wsl.com/images/image001.png",
        "https://nya-wsl.com/images/image002.png",
        "https://nya-wsl.com/images/image003.png",
        "static/sample1.png",
        "static/sample2.png"
    ],
    "color": "#fcefe8",
    "btn_color": "#fcefe8",
    "text_color": "#000000",
    "local_text": False,
    "show_capture_gift_list": False,
    "capture_gift_list_number": 3
}

# 检查配置文件状态
# 如配置文件不存在，则注入内置预设
if not os.path.exists("config.json"):
    with open("config.json", "w+", encoding="utf-8") as f:
        json.dump(example_config, f, indent=4, ensure_ascii=False)

# 检查storage状态
app.storage.general["gift_challenge_count"] = app.storage.general.get("gift_challenge_count", 0)
app.storage.general["gift_challenge_unit"] = app.storage.general.get("gift_challenge_unit", "")
app.storage.general["gift_challenge_text"] = app.storage.general.get("gift_challenge_text", "")
app.storage.general["countdown_time"] = app.storage.general.get("countdown_time", 0)
app.storage.general["version"] = app.storage.general.get("version", version)
app.storage.general["startup_check_bili_auth"] = app.storage.general.get("startup_check_bili_auth", False)

# ================================
# 初始化配置文件
# ================================

# 加载配置文件
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# 检查配置文件缺失项
diff = example_config.keys() - config.keys()

for key in diff:
    config[key] = example_config[key]

# 检查配置文件多余项
diff = config.keys() - example_config.keys()

for key in diff:
    config.pop(key, None)

config["cwd"] = os.getcwd() # 保存工作目录用于debug

with open("config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=4)

host = config["host"]
port = config["port"]
btn_color = config["btn_color"]

ui.add_css(
    f"""
.text-btn {{
color: {btn_color};
}}

.bg-btn {{
background: {btn_color};
}}
""",
    shared=True,
)

ui.button.__init__.__kwdefaults__['color'] = btn_color # 设置所有按钮颜色为配置文件中的btn_color

GiftManager = get_gift.BiliGiftManager()

def create_blind_box():
    box_id = []
    blind_box = {}
    gifts = GiftManager.get_room_gift("android")
    for gift in gifts:
        if re.search("盲盒", gift["name"]):
            box_id.append(gift["id"])

    if box_id == []:
        logger.error("未获取到盲盒数据")
        return

    for id in box_id:
        gifts = []
        box_gifts = GiftManager.get_blind_box(id)

        if box_gifts != {}:
            try:
                box_gifts_list = box_gifts["gifts"]
            except Exception as e:
                if config.get("SESSDATA", "") == "":
                    logger.error(f"获取盲盒数据失败：{e}，未登录账号")
                else:
                    logger.error(f"获取盲盒数据失败：{e}")
                return blind_box

            for gift in box_gifts_list:
                gifts.append(gift["gift_name"])
            blind_box[box_gifts["blind_gift_name"]] = gifts
        else:
            logger.error("盲盒数据为空")

    with open("data/blinx_box_data.json", "w+", encoding="utf-8") as f:
        json.dump(blind_box, f, ensure_ascii=False, indent=4)

    return blind_box

def init_config():
    """
    初始化礼物数据
    """

    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    # 初始化gifts.json数据
    # 确保礼物数据文件存在，如果不存在，则先初始化礼物数据
    if not os.path.exists("data/gifts.json") or not os.path.exists("data/gift_img.json"):
        # 如果配置文件中包含房间号，则传入；否则会触发 init_gift
        room_id = config.get("room_id", "")

        # 如果配置文件中有room_id，则使用该房间号
        if room_id:
            gift_config = GiftManager.get_config(img_path="data/gift_img.json", time_path="data/gifts.json") # 使用B站api
            # 如获取B站礼物数据失败，则从Nya-WSL服务器或本地注入方式写入
            if not gift_config:
                GiftManager.init_gift("data/gift_img.json", "data/gifts.json")
        else:
            # 如果没有room_id，则创建空文件
            with open("data/gifts.json", "w+", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            with open("data/gift_img.json", "w+", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=4)

    # 初始化数据
    if not os.path.exists("data/special.json"):
        with open("data/special.json", "w+", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

    if not os.path.exists("data/gifts_count.json"):
        shutil.copy("data/gifts.json", "data/gifts_count.json")

    if not os.path.exists("data/special_count.json"):
        with open("data/special_count.json", "w+", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

init_config()

def get_pid_info(pid):
    p = psutil.Process(pid)
    p_cpu_percent = p.cpu_percent(interval=None)
    p_memory_info = p.memory_info()

    return p_cpu_percent, p_memory_info

def check_sys():
    # CPU信息
    cpu_model = cpuinfo.get_cpu_info().get('brand_raw', '未知')
    cpu_usage = psutil.cpu_percent(interval=None)
    cpu_freq = psutil.cpu_freq()

    # 内存信息
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    p_cpu_percent, p_memory_info = get_pid_info(os.getpid())

    sys_info = {
                "CPU型号": cpu_model,
                "CPU总使用率": cpu_usage,
                "CPU频率": f"{cpu_freq.current / 1000} GHz" if cpu_freq else 0,
                "内存大小": mem.total / (1024**3),
                "已使用内存": mem.used / (1024**3),
                "剩余内存": mem.free / (1024**3),
                "内存使用率": mem.percent,
                "swap分区大小": swap.total / (1024**3),
                "已使用swap分区": swap.used / (1024**3),
                "剩余swap分区": swap.free / (1024**3),
                "swap分区使用率": swap.percent,
                "加班姬CPU使用率": p_cpu_percent,
                "加班姬内存占用": f"{p_memory_info.rss / (1024 * 1024):.2f} MB"
            }

    if not os.path.exists("data/sys_info"):
        os.mkdir("data/sys_info")

    with open(f"data/sys_info/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w+", encoding="utf-8") as f:
        json.dump(sys_info, f, ensure_ascii=False, indent=4)

    return sys_info

@ui.page("/debug")
async def index():
    ui.label(f"统计时间: {datetime.datetime.now().strftime('%Y.%m.%d %H:%M:%S')}")
    for k, v in check_sys().items():
        if isinstance(v, list):
            ui.label(f"{k}: {', '.join(map(str, v))}")
        elif isinstance(v, (int, float)):
            if "使用率" in k:
                ui.label(f"{k}: {v:.2f}%")
            else:
                ui.label(f"{k}: {v:.2f}GB")
        else:
            ui.label(f"{k}: {v}")

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

        client = blivedm.BLiveClient(ROOM_ID, session=session)
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
        logger.info("触发心跳")
        if self.heart_count < 2:
            b_connect_switch.set_value(True)
            b_connect_switch.set_text("已连接弹幕服务器")
            logger.info(f"已连接至{room_id.value}")

            uid = client.uid
            if uid != 0:
                login_status.set_text("已登录")
                login_status.classes("text-green")
            else:
                login_status.set_text("未登录")

    # 礼物数据
    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        gift = message.gift_name
        num = message.num
        uname = message.uname
        price = message.price / 100
        result = ""
        if len(uname.split("")) > 8:
            uname = uname.split("")[0-5] + "..."

        self._on_gift_play(gift, num, uname, message, price)
        self._on_gift_statistics(gift, num, uname, price)
        logger.info(message)


    # 舰队数据
    def _on_user_toast_v2(self, client: blivedm.BLiveClient, message: web_models.UserToastV2Message):
        gift = message.guard_level
        num = message.num
        uname = message.username
        price = message.price / 100
        result = ""

        if gift == 1:
            gift = "总督"
        elif gift == 2:
            gift = "提督"
        elif gift == 3:
            gift = "舰长"
        else:
            gift = "神秘物种"

        if len(uname.split("")) > 8:
            uname = uname.split("")[0-5] + "..."

        self._on_gift_play(gift, num, uname, False)
        self._on_gift_statistics(gift, num, uname, price)
        logger.info(message)

    # ================================
    # 醒目留言
    # 待开发
    # ================================
    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        logger.info(f'[{client.room_id}] 醒目留言 ¥{message.price} {message.uname}：{message.message}')

    def _on_interact_word(self, client: blivedm.BLiveClient, message: web_models.InteractWordMessage):
        if message.msg_type == 1:
            logger.info(f'{message.username} 进入房间')

    def _on_gift_statistics(self, gift, num, uname, price = 0):
        if not os.path.exists("data/gift_statistics.json"):
            with open("data/gift_statistics.json", "w+", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=4)

        with open("data/gift_statistics.json", "r", encoding="utf-8") as f:
            count = json.load(f)

        count.setdefault(gift, {"num": 0, "price": 0, "user": []})
        users = count[gift]["user"]

        if uname not in users:
            users.append(uname)

        num += count[gift]["num"]

        if gift == "辣条":
            price = 0

        count[gift] = {"num": num, "price": price, "user": users}

        with open("data/gift_statistics.json", "w+", encoding="utf-8") as f:
            json.dump(count, f, ensure_ascii=False, indent=4)

    # 收到礼物后执行函数
    def _on_gift_play(self, gift, num, uname, message, price = 0):
        is_blind_box = False

        def blind_box_value(gift, num : int, price : int, box_name):
            if not os.path.exists("data/blind_box_value.json"):
                with open("data/blind_box_value.json", "w+", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)

            with open("data/blind_box_value.json", "r", encoding="utf-8") as f:
                box_value = json.load(f)

            if box_value.get(box_name, None) == None:
                box_value[box_name] = {}

            if box_value[box_name].get(gift, None) == None:
                box_value[box_name][gift] = {"num": 0, "price": 0}

            box_value[box_name][gift] = {"num": box_value[box_name][gift]["num"] + num, "price": price}

            with open("data/blind_box_value.json", "w+", encoding="utf-8") as f:
                json.dump(box_value, f, ensure_ascii=False, indent=4)

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

                    # 初始化盲盒数据
                    blind_box = create_blind_box()
                    blind_box_gifts = []

                    if blind_box == {}:
                        logger.error("初始化盲盒失败，将使用默认数据")
                        blind_box = gift_map.blind_box

                    for v in blind_box.values():
                        for blind_gift in v:
                            blind_box_gifts.append(blind_gift)

                    # 如果礼物在盲盒中，将礼物设定为盲盒id
                    origin_gift = None
                    if gift in blind_box_gifts:
                        for box_name, gifts_name in blind_box.items():
                            if gift in gifts_name:
                                if gifts[box_name] != 0 or special.get(box_name, None) != None:
                                    origin_gift = gift
                                    if gift not in special and gifts[gift] == 0:
                                        is_blind_box = True
                                        gift = box_name

                                    blind_box_value(origin_gift, num, price, box_name) # 盲盒价值

                    # 如果收到的礼物在special.json中
                    if gift in special:
                        if special[gift] == "double": # 加倍挑战
                            changed_num = int(gift_challenge_count.text) * (2 * int(num))

                            if is_blind_box:
                                gift = origin_gift

                            # gift_list_show(uname, gift, num, f"{2 * int(num)}倍")
                            if show_capture_gift_list_switch.value and capture_gift_is_created:
                                capture_challenge_gift_list_show(uname, gift, num, f"{2 * int(num)}倍", message)

                        if special[gift] == "clear": # 清空挑战
                            changed_num = 0

                            if is_blind_box:
                                gift = origin_gift

                            # gift_list_show(uname, gift, num, "清空")
                            if show_capture_gift_list_switch.value and capture_gift_is_created:
                                capture_challenge_gift_list_show(uname, gift, num, "清空", message)

                        if type(special[gift]) == list: # 随机挑战，只有随机的类型为list
                            total_changed_num = 0

                            for i in range(num):
                                random_num = random.randint(special[gift][0], special[gift][1] + 1)
                                total_changed_num += random_num

                            changed_num = int(gift_challenge_count.text) + total_changed_num
                            gift_list_show_num = str(int(gifts[gift] * int(num)))

                            if is_blind_box:
                                gift = origin_gift

                            # gift_list_show(uname, gift, num, gift_list_show_num + gift_play_unit_main.text, message)
                            if show_capture_gift_list_switch.value and capture_gift_is_created:
                                capture_challenge_gift_list_show(uname, gift, num, gift_list_show_num + gift_play_unit_main.text, message)

                    # 如果收到的礼物不在special.json中
                    else:
                        changed_num = (gifts[gift] * int(num)) + int(gift_challenge_count.text) # （设定的值 * 礼物数量） + 目前总数
                        gift_list_show_num = str(int(gifts[gift] * int(num)))

                        if is_blind_box:
                            gift = origin_gift

                        if gifts[gift] != 0 or is_blind_box:
                            # gift_list_show(uname, gift, num, gift_list_show_num + gift_play_unit_main.text, message)
                            if show_capture_gift_list_switch.value and capture_gift_is_created:
                                capture_challenge_gift_list_show(uname, gift, num, gift_list_show_num + gift_play_unit_main.text, message)

                    gift_challenge_count.set_text(changed_num) # 将label的text设定为结果
                    gift_challenge_count.bind_text_to(app.storage.general, "gift_challenge_count") # 将结果写入storage

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

                    # 初始化盲盒数据
                    blind_box = create_blind_box()
                    blind_box_gifts = []

                    if blind_box == {}:
                        logger.error("初始化盲盒失败，将使用默认数据")
                        blind_box = gift_map.blind_box

                    for v in blind_box.values():
                        for blind_gift in v:
                            blind_box_gifts.append(blind_gift)

                    # 如果礼物在盲盒中，将礼物设定为盲盒id
                    origin_gift = None
                    if gift in blind_box_gifts:
                        for box_name, gifts_name in blind_box.items():
                            if gift in gifts_name:
                                if gifts[box_name] != 0 or special.get(box_name, None) != None:
                                    origin_gift = gift
                                    if gift not in special and gifts[gift] == 0:
                                        is_blind_box = True
                                        gift = box_name

                                    blind_box_value(origin_gift, num, price, box_name) # 盲盒价值

                    if gift in special:
                        if special[gift] == "double":
                            changed_time = tmp_time * (2 * int(num))

                            if is_blind_box:
                                gift = origin_gift

                            # gift_list_show(uname, gift, num, f"{2 * int(num)}倍")
                            if show_capture_gift_list_switch.value and capture_cd_is_created:
                                capture_cd_gift_list_show(uname, gift, num, f"{2 * int(num)}倍", message)

                        if special[gift] == "clear":
                            changed_time = 3

                            if is_blind_box:
                                gift = origin_gift

                            # gift_list_show(uname, gift, num, "清空")
                            if show_capture_gift_list_switch.value and capture_cd_is_created:
                                capture_cd_gift_list_show(uname, gift, num, "清空", message)

                        if type(special[gift]) == list:
                            total_changed_time = 0
                            for i in range(num):
                                random_time = random.randint(special[gift][0], special[gift][1] + 1)
                                total_changed_time += random_time

                            changed_time = tmp_time + total_changed_time

                            if is_blind_box:
                                gift = origin_gift

                            # gift_list_show(uname, gift, num, format_seconds(total_changed_time), message)
                            if show_capture_gift_list_switch.value and capture_cd_is_created:
                                capture_cd_gift_list_show(uname, gift, num, format_seconds(total_changed_time), message)

                    else:
                        changed_time = (gifts[gift] * int(num)) + tmp_time
                        gift_list_show_time = gifts[gift] * int(num)

                        if is_blind_box:
                            gift = origin_gift

                        if gifts[gift] != 0 or is_blind_box:
                            # gift_list_show(uname, gift, num, format_seconds(gift_list_show_time), message)
                            if show_capture_gift_list_switch.value and capture_cd_is_created:
                                capture_cd_gift_list_show(uname, gift, num, format_seconds(gift_list_show_time), message)

                    countdown_timer.set_time(changed_time) # 重设倒计时数据

# 倒计时类
class CountdownTimer:
    def __init__(self, start_time):
        self._start_time = start_time # 初始化开始时间
        self._remaining_time = start_time # 初始化剩余时间
        self._paused = False # 初始化暂停状态
        self._running = False # 初始化运行状态
        self._paused_event = asyncio.Event() # 初始化event
        self._paused_event.set()  # 最开始没有暂停
        self._task = None # 初始化task

    # 获取当前倒计时
    def get_tmp_time(self):
        return float(self._remaining_time)

    # 倒计时运行函数
    async def _run(self, label):
        while self._running and self._remaining_time > 0:
            if self._paused:
                await self._paused_event.wait()  # Wait until unpaused
            # 设置按钮状态
            start_button.disable()
            cancel_button.enable()
            pause_button.enable()

            self._remaining_time -= 1 # 倒计时减1s
            app.storage.general["countdown_time"] = self._remaining_time

            # 格式化时间数据
            minute, second = divmod(self._remaining_time, 60)
            hour, minute = divmod(minute, 60)
            label.set_text("%02d:%02d:%02d" % (hour, minute, second))
            await asyncio.sleep(1) # 异步阻塞1s

        # 判断倒计时状态
        if self._remaining_time <= 0:
            await self.stop(time_badge)

            # 倒计时结束后重置时间输入框
            input_hour.set_value(0)
            input_minute.set_value(0)
            input_second.set_value(0)

    # 运行倒计时
    def start(self, label):
        global cd_status
        # 如果倒计时未在运行
        if not self._running:
            self._running = True # 修改运行状态
            self._remaining_time = self._start_time  # 设置开始时间
            if self._remaining_time != 0: # 防止写入0时开始倒计时
                self._task = asyncio.create_task(self._run(label)) # 创建倒计时协程
                # 重置时间输入框
                input_hour.set_value(0)
                input_minute.set_value(0)
                input_second.set_value(0)
                # 设置按钮状态
                add_button.enable()
                sub_button.enable()
                cancel_button.set_text("停止")
                cd_status = True # 设置倒计时运行状态
            else:
                ui.notify("请输入时间", type="negative")
                self._running = False

    # 暂停倒计时
    async def pause(self):
        global cd_status
        if self._running and not self._paused: # 如果倒计时在运行且没有暂停
            self._paused = True
            self._paused_event.clear()  # Pause the timer
            resume_button.enable()
            pause_button.disable()
            add_button.disable()
            sub_button.disable()
            cd_status = False

    # 继续倒计时
    def resume(self):
        global cd_status
        if self._running and self._paused:
            self._paused = False
            self._paused_event.set()  # Resume the timer
            pause_button.enable()
            resume_button.disable()
            add_button.enable()
            sub_button.enable()
            cd_status = True

    # 停止倒计时
    async def stop(self, label):
        global cd_status
        if self._running:
            self._running = False
            self._paused = False
            if self._task:
                self._task.cancel() # 结束协程
            label.set_text("00:00:00")
            app.storage.general["countdown_time"] = 0
            self._start_time = int(app.storage.general["countdown_time"])
            self._remaining_time = self._start_time  # Reset the timer
            start_button.enable()
            cancel_button.disable()
            pause_button.disable()
            resume_button.disable()
            add_button.disable()
            sub_button.disable()
            input_hour.set_value(0)
            input_minute.set_value(0)
            input_second.set_value(0)
            cd_status = False
        else:
            if reset_inherit_status:
                label.set_text("00:00:00")
                app.storage.general["countdown_time"] = 0
                self._start_time = int(app.storage.general["countdown_time"])
                self._remaining_time = self._start_time  # Reset the timer
                cancel_button.set_text("停止")
                cancel_button.disable()

    # 设置倒计时
    def set_time(self, time):
        # 如果计时器正在运行，首先停止它
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()

        # 更新起始时间和剩余时间
        self._start_time = time
        self._remaining_time = time

        # 更新 UI 上的显示
        hour, minute = divmod(self._remaining_time, 3600)
        minute, second = divmod(minute, 60)
        time_badge.set_text("%02d:%02d:%02d" % (hour, minute, second))

        # 如果计时器没有运行，则重新启动计时器
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run(time_badge))

    # 继承倒计时
    def inherit_time(self, time):
        # 如果计时器正在运行，首先停止它
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()

        # 更新起始时间和剩余时间
        self._start_time = time
        self._remaining_time = time

        # 更新 UI 上的显示
        hour, minute = divmod(self._remaining_time, 3600)
        minute, second = divmod(minute, 60)
        time_badge.set_text("%02d:%02d:%02d" % (hour, minute, second))


def sort_dict(d):
    # 分离正数（包括零）和负数
    positive = {k: v for k, v in d.items() if v >= 0}
    negative = {k: v for k, v in d.items() if v < 0}

    # 正数按值降序排序，负数按值升序排序
    sorted_positive = sorted(positive.items(), key=lambda x: x[1], reverse=True)
    sorted_negative = sorted(negative.items(), key=lambda x: x[1])

    # 合并结果并创建有序字典
    sorted_items = sorted_positive + sorted_negative
    return OrderedDict(sorted_items)
    # 或者直接返回字典（Python 3.7+）
    # return dict(sorted_items)

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
            elif status.value == "sub":
                gifts[gift_name.value] = float(f"-{time.value}")
                if gift_name.value in special:
                    special.pop(gift_name.value)
            elif status.value == "double":
                special[gift_name.value] = "double"
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
            elif status.value == "clear":
                special[gift_name.value] = "clear"
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
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

            gifts = sort_dict(gifts)  # 对礼物数据进行排序

            with open("data/gifts.json", "w+", encoding="utf-8") as f:
                json.dump(gifts, f, ensure_ascii=False, indent=4)
            with open("data/special.json", "w+", encoding="utf-8") as f:
                json.dump(special, f, ensure_ascii=False, indent=4)

            refresh_capture_cd = True # 设置capture刷新状态
            refresh_card()

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
            refresh_card()

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

        gifts = sort_dict(gifts)  # 对礼物数据进行排序

        with open("data/gifts.json", "w+", encoding="utf-8") as f:
            json.dump(gifts, f, ensure_ascii=False, indent=4)
        with open("data/special.json", "w+", encoding="utf-8") as f:
            json.dump(special, f, ensure_ascii=False, indent=4)

        refresh_capture_cd = True # 设置capture刷新状态
        refresh_card()

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
            gifts = sort_dict(gifts)  # 对礼物数据进行排序
            with open("data/gifts.json", "w+", encoding="utf-8") as f:
                json.dump(gifts, f, ensure_ascii=False, indent=4)

        refresh_capture_cd = True
        refresh_card()

    def create_card():
        with open("data/gifts.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)
        with open("data/special.json", "r", encoding="utf-8") as f:
            special = json.load(f)

        for k,v in gifts.items():
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

    def refresh_card():
        gift_card.clear()  # 清空卡片内容
        with gift_card:
            create_card()

    # 弹窗
    with ui.dialog() as cd_dialog, ui.card(align_items="center"):
        with open("data/gifts.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)

        ui.label("设置预览").classes("text-2xl text-blue").style("font-size: 20px")

        with ui.card().classes("w-full") as gift_card:
            create_card()

        ui.separator() # 分割线

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

# 盲盒价值弹窗
def blind_box_value_dialog():
    def get_box_value():
        if not os.path.exists("data/blind_box_value.json"):
            with open("data/blind_box_value.json", "w+", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
        with open("data/blind_box_value.json", "r", encoding="utf-8") as f:
            box_value = json.load(f)
        box_price_list = {"星月盲盒": 50, "心动盲盒": 150, "奇遇盲盒": 330, "闪耀盲盒": 500, "至尊盲盒": 1000, "百花盲盒": 250} # 盲盒基础价值
        value_list = {}
        price_list = {}
        for k,v in box_value.items():
            if not k in box_price_list:
                box_price_list[k] = 0

            for gift, value in v.items():
                gift_name = gift
                num = int(value["num"])
                price = int(value["price"])
                if value_list.get(k, None) == None:
                    value_list[k] = []
                value_list[k].append(f"礼物：{gift_name} | 数量：{num} | 总价格：{num * price}电池")

            blind_all_price = 0
            for gift_name, gift_value in v.items():
                blind_all_price += (gift_value["num"] * gift_value["price"]) - (box_price_list[k] * gift_value["num"])
            price_list[k] = blind_all_price

        with value_card:
            for box_name in box_value.keys():
                ui.label(f"{box_name} | 价格：{box_price_list[box_name]}电池")
                for k,v in value_list.items():
                    if k == box_name:
                        for i in v:
                            ui.label(i)
                        ui.label(f"盈亏：{price_list[k]}电池")
                ui.separator() # 分割线

            all_price = 0
            for i in price_list.values():
                all_price += i
            ui.label(f"总盈亏：{all_price}电池")

    def clear_box_value():
        os.remove("data/blind_box_value.json")
        value_card.clear()
        get_box_value()
        ui.button("关闭", on_click=lambda: value_dialog.close())

    if not os.path.exists("data/blind_box_value.json"):
        with open("data/blind_box_value.json", "w+", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

    with ui.dialog() as value_dialog, ui.card(align_items="center") as value_card:
        ui.label().set_visibility(False)
        get_box_value()
        ui.button("清零", on_click=lambda: clear_box_value())

    value_dialog.open()

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
            elif status.value == "sub":
                gifts[gift_name.value] = float(f"-{number.value}")
                if gift_name.value in special:
                    special.pop(gift_name.value)
            elif status.value == "double":
                special[gift_name.value] = "double"
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
            elif status.value == "clear":
                special[gift_name.value] = "clear"
                if gift_name.value in gifts:
                    gifts[gift_name.value] = 0
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

            with open("data/gifts_count.json", "w+", encoding="utf-8") as f:
                json.dump(gifts, f, ensure_ascii=False, indent=4)
            with open("data/special_count.json", "w+", encoding="utf-8") as f:
                json.dump(special, f, ensure_ascii=False, indent=4)

            refresh_capture_gift = True
            refresh_card()

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
            double_check_dialog.close()
            refresh_card()

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

        with open("data/gifts_count.json", "w+", encoding="utf-8") as f:
            json.dump(gifts, f, ensure_ascii=False, indent=4)
        with open("data/special_count.json", "w+", encoding="utf-8") as f:
            json.dump(special, f, ensure_ascii=False, indent=4)

        refresh_capture_gift = True # 设置capture刷新状态
        refresh_card()

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
        refresh_card()

    def create_card():
        with open("data/gifts_count.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)
        with open("data/special_count.json", "r", encoding="utf-8") as f:
            special = json.load(f)
        for k,v in gifts.items():
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

    def refresh_card():
        gift_card.clear()  # 清空卡片内容
        with gift_card:
            create_card()

    with ui.dialog() as gift_count_dialog, ui.card(align_items="center"):
        with open("data/gifts_count.json", "r", encoding="utf-8") as f:
            gifts = json.load(f)

        ui.label("设置预览").classes("text-2xl text-blue").style("font-size: 20px")

        with ui.card().classes("w-full") as gift_card:
            create_card()

        ui.separator()

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

def init_task():
    global countdown_timer
    global reset_inherit_status
    countdown_timer = CountdownTimer(int(time_badge_inherit.text))
    if app.storage.general.get("countdown_time", 0) != 0: # 如果存在可继承的倒计时
        cancel_button.set_text("重置")
        cancel_button.enable()
        reset_inherit_status = True # 设置重置继承倒计时状态为True

# 运行倒计时
def start_task():
    if countdown_timer._start_time == 0:
        countdown_timer._start_time = (input_hour.value * 3600) + (input_minute.value * 60) + input_second.value
        countdown_timer._remaining_time = countdown_timer._start_time
    countdown_timer.start(time_badge)


# 手动加时
def add_time():
    try:
        if input_hour.value != 0 or input_minute.value != 0 or input_second.value != 0:
            tmp_time = countdown_timer.get_tmp_time()
            changed_time = tmp_time + ((input_hour.value * 3600) + (input_minute.value * 60) + input_second.value) + 1 # 在视觉效果上倒计时被正确反馈，实际上多加了1s
            countdown_timer.set_time(changed_time)
    except NameError:
        ui.notify("请先开始计时", type="negative")


# 手动减时
def sub_time():
    try:
        if input_hour.value != 0 or input_minute.value != 0 or input_second.value != 0:
            tmp_time = countdown_timer.get_tmp_time()
            changed_time = tmp_time - ((input_hour.value * 3600) + (input_minute.value * 60) + input_second.value) + 1  # 在视觉效果上倒计时被正确反馈，实际上少减了1s
            countdown_timer.set_time(changed_time)
    except NameError:
        ui.notify("请先开始计时", type="negative")


# 保存配置
def save_config():
    with open("config.json", "w+", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


def check_auth(loginInfo):
    status = bili_auth.login(loginInfo[0])

    if status == True:
        ui.notify("登录成功", type="positive")
        try:
            os.remove(loginInfo[1])
        except:
            logger.warning(f"删除{loginInfo[1]}失败")

    else:
        ui.notify(status, type="negative")


def bili_login(init = False):
    global qrcode_ui
    if config["room_id"] == "":
        ui.notify("请先填入房间号", type="negative")
        return

    loginInfo = bili_auth.get_qrcode("bili_qrcode")

    with ui.dialog() as auth_dialog, ui.card(align_items="center"):
        qrcode_ui = ui.image(loginInfo[1])
        ui.label("请使用B站APP扫描二维码登录")
        qr_button = ui.button("已扫码", on_click=lambda: check_auth(loginInfo))
        qr_button.on_click(lambda: auth_dialog.close()).on_click(lambda: os.remove(loginInfo[1])) # 因为太长了所以换一行写
        if init:
            qr_button.on_click(lambda: init_login_dialog.close())

    auth_dialog.open()
    auth_dialog.on("hide", lambda: os.remove(loginInfo[1]))


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

    # 尝试连接弹幕服务器
    if b_connect_switch.value == "null":
        if room_id.value == "":
            b_connect_switch.set_value(False)
            return

        if not b_connect_status:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            if config["SESSDATA"] == "":
                ui.notify("未登录B站账号，历史礼物功能可能无法显示用户名且无法获取最新的盲盒数据", type="warning")
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
    async def check_refresh():
        if room_id.value == "":
            ui.notify("请输入房间号", type="negative")
            return

        check_dialog.close()

        ui.notify("正在更新礼物数据，请稍后...", type="info")

        await asyncio.sleep(1)

        gift_config = GiftManager.get_config(img_path="data/gift_img.json", time_path="data/gifts.json", init=False)

        if gift_config == True:
            ui.notify("礼物数据更新完成", type="positive")
        # 如果本地礼物配置数据不存在，则直接初始化
        elif gift_config == None:
            ui.notify("未检测到本地礼物数据，将初始化礼物数据...", type="info")
            init_config()
            ui.notify("礼物数据初始化完成", type="positive")
        # 如果更新盲盒礼物出错
        elif gift_config == "blind_box_none":
            ui.notify("未登录账号，无法更新盲盒礼物，将使用默认数据...", type="negative")
            await asyncio.sleep(2)
            ui.notify("礼物数据更新完成", type="positive")
        # 如果礼物数据更新失败，则使用本地数据重置
        else:
            ui.notify("礼物数据更新失败，请检查日志或稍后重试，或者使用本地数据重置", type="negative")

    def reset_local_gift():
        # 重置本地数据
        try:
            GiftManager.init_gift("data/gift_img.json", "data/gifts.json")
            ui.notify("重置成功", type="positive")
        except Exception as e:
            logger.exception(f"使用本地数据重置失败：{e}")
            ui.notify("重置失败", type="negative")

    with ui.dialog() as check_dialog, ui.card(align_items="center"):
        ui.label("请不要在倒计时和投喂挑战功能运行时更新。")
        ui.label("更新礼物数据前，请先暂停倒计时与投喂挑战。")
        ui.label("是否进行更新？")

        with ui.row():
            ui.button("确定", on_click=lambda: check_refresh())
            ui.button("取消", on_click=lambda: check_dialog.close())
            ui.button("使用本地数据重置", on_click=lambda: reset_local_gift())

    check_dialog.open()

# 倒计时预览
@ui.page("/capture_cd", title="倒计时 | bili_travail")
async def capture():
    global capture_cd_gift_list_show, capture_cd_is_created

    # 检查是否需要刷新页面
    def check_cd_refresh():
        global refresh_capture_cd
        if not show_capture_gift_list_switch.value:
            if scroll_card.visible:
                scroll_card.set_visibility(False)
        else:
            scroll_card.set_visibility(True)

        if refresh_capture_cd:
            refresh_capture_cd = False
            # ui.run_javascript(f'window.location.href += "?{refresh_time}";')
            ui.navigate.reload()

    capture_cd_is_created = True

    if not os.path.exists("data/gifts.json") or not os.path.exists("data/gift_img.json"):
        init_config()


    # 初始化礼物列表
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    with open("data/gifts.json", "r", encoding="utf-8") as f:
        gifts = json.load(f)

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

        def capture_cd_gift_list_show(name, gift, num, time, message):
            if not show_capture_gift_list_switch.value:
                scroll_card.set_visibility(False)
            else:
                scroll_card.set_visibility(True)
                capture_gift_scroll.clear()

                if not os.path.exists("data/gift_history.json"):
                    gift_history = {
                        "cd": [],
                        "challenge": []
                    }
                    with open("data/gift_history.json", "w+", encoding="utf-8") as f:
                        json.dump(gift_history, f, ensure_ascii=False, indent=4)

                with open("data/gift_history.json", "r", encoding="utf-8") as f:
                    gift_history = json.load(f)
                with open("data/gift_img.json", "r", encoding="utf-8") as f:
                    gifts = json.load(f)
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)

                gift_history["cd"].append({
                    "name": name,
                    "gift": gift,
                    "num": num,
                    "rule": time,
                    "url": message.gift_img_basic if message else gifts.get(data["gift"], ""),
                    "time": datetime.datetime.now().strftime('%H:%M:%S')
                })

                with open("data/gift_history.json", "w+", encoding="utf-8") as f:
                    json.dump(gift_history, f, ensure_ascii=False, indent=4)

                with capture_gift_scroll:
                    for data in gift_history["cd"][-int(config["capture_gift_list_number"]):]:
                        with ui.row().classes("w-full"):
                            gift_user = data["name"]
                            gift_num = data["num"]
                            gift_rule = data["rule"]
                            gift_name = data["gift"]
                            gift_img = data["url"]

                            ui.label(f"{gift_user}").classes("text-xl font-extrabold").style(f"color: {config['text_color']}")
                            with ui.avatar(color="").classes("w-6 h-6"):
                                if gift_name not in ["舰长", "提督", "总督"]:
                                    if message:
                                        ui.image(bili_api.get_bili_img(gift_img))
                                    else:
                                        ui.image(bili_api.get_bili_img(gifts.get(gift_name, "")))
                                else:
                                    ui.image(gifts.get(gift_name, ""))
                            ui.label(f"x{gift_num}").classes("text-xl font-extrabold").style(f"color: {config['text_color']}")
                            ui.label(gift_rule).classes("text-xl font-extrabold").style(f"color: {config['text_color']}")

                capture_gift_scroll.scroll_to(percent=1, duration=0.5)

        with ui.card(align_items="stretch").classes("bg-transparent w-full").style("box-shadow: None;") as scroll_card:
            with ui.scroll_area().classes('h-32 w-full') as capture_gift_scroll:
                ui.label().set_visibility(False)

    ui.timer(5, callback=lambda: check_cd_refresh())

# 投喂挑战预览
@ui.page("/capture_gift", title="投喂挑战 | bili_travail")
async def capture():
    global capture_challenge_gift_list_show, capture_gift_is_created
    def check_gift_refresh():
        global refresh_capture_gift
        if not show_capture_gift_list_switch.value:
            if scroll_card.visible:
                scroll_card.set_visibility(False)
        else:
            scroll_card.set_visibility(True)

        if refresh_capture_gift:
            refresh_capture_gift = False
            # ui.run_javascript(f'window.location.href += "?{refresh_time}";')
            ui.navigate.reload()

    capture_gift_is_created = True

    if not os.path.exists("data/gifts_count.json") or not os.path.exists("data/gift_img.json"):
        init_config()

    # 礼物列表
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    with open("data/gifts_count.json", "r", encoding="utf-8") as f:
        gifts = json.load(f)

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

        def capture_challenge_gift_list_show(name, gift, num, time, message):
            if not show_capture_gift_list_switch.value:
                scroll_card.set_visibility(False)
            else:
                scroll_card.set_visibility(True)
                capture_gift_scroll.clear()

                if not os.path.exists("data/gift_history.json"):
                    gift_history = {
                        "cd": [],
                        "challenge": []
                    }
                    with open("data/gift_history.json", "w+", encoding="utf-8") as f:
                        json.dump(gift_history, f, ensure_ascii=False, indent=4)

                with open("data/gift_history.json", "r", encoding="utf-8") as f:
                    gift_history = json.load(f)
                with open("data/gift_img.json", "r", encoding="utf-8") as f:
                    gifts = json.load(f)
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)

                gift_history["challenge"].append({
                    "name": name,
                    "gift": gift,
                    "num": num,
                    "rule": time,
                    "url": message.gift_img_basic if message else gifts.get(data["gift"], ""),
                    "time": datetime.datetime.now().strftime('%H:%M:%S')
                })

                with open("data/gift_history.json", "w+", encoding="utf-8") as f:
                    json.dump(gift_history, f, ensure_ascii=False, indent=4)

                with capture_gift_scroll:
                    for data in gift_history["challenge"][-int(config["capture_gift_list_number"]):]:
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
                                        ui.image(bili_api.get_bili_img(gift_img))
                                    else:
                                        ui.image(bili_api.get_bili_img(gifts.get(gift_name, "")))
                                else:
                                    ui.image(gifts.get(gift_name, ""))
                            ui.label(f"x{gift_num}").classes("text-xl font-extrabold")
                            ui.label(gift_rule).classes("text-xl font-extrabold")

                capture_gift_scroll.scroll_to(percent=1, duration=0.5)

        with ui.card(align_items="stretch").classes("bg-transparent w-full").style("box-shadow: None;") as scroll_card:
            with ui.scroll_area().classes('h-32 w-full') as capture_gift_scroll:
                ui.label().set_visibility(False)

    ui.timer(5, callback=lambda: check_gift_refresh())


# ================================
# 主界面GUI
# ================================

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

async def ping_server():
    servers = {
        "GitHub": "github.com",
        "CN-HK": "travail.nya-wsl.com",
        "CN-QN": "qn.nya-wsl.cn"
    }
    server = await ping.ping(servers.values())
    if server != False:
        for k, v in servers.items():
            if v == server:
                return k
    else:
        return False

# 检查版本更新按钮
async def check_update(init = False):

    async def update(server, status):
        if server == "auto":
            ui.notify(f"测速中，请稍候...", progress=True, timeout=3000, type="ongoing", color="blue-100")
            server = await ping_server()
            if server == False:
                ui.notify("无法连接更新服务器", type="negative")
                return

        await travail_update.update(server, status) # 调用更新函数

    def version_dialog():
        with ui.dialog() as dialog, ui.card(align_items="center"):
            ui.label(f"当前版本：{version} | 最新版本：{status}")
            server_select = ui.select(options={"CN-HK": "国内源", "CN-QN": "国内备用源", "GitHub": "GitHub", "auto": "自动检测"}, label="选择更新源", value="auto").classes("w-1/2")
            ui.button("更新", on_click=lambda: update(server_select.value, status))

        dialog.open()

    def version_check():
        url = ["http://version.nya-wsl.cn/bili_travail/version.json", "https://nya-wsl.com/bili_travail/version.json"]
        try:
            response = requests.get(url[0]) # 优先从Nya-WSL中国服务器获取版本信息
            if response.status_code == 200:
                data = response.json()
                latest_version = data["version"]
            else:
                raise ValueError("From Nya-WSL CN to get version info was error") # 抛出错误
        except Exception as e:
            logger.error(e)
            try:
                response = requests.get(url[1]) # 从Nya-WSL海外服务器获取版本信息
                if response.status_code == 200: # 服务器请求返回值
                    data = response.json()
                    latest_version = data["version"]
                else:
                    latest_version = "Error"
            except Exception as e:
                logger.error(e)
                latest_version = "Error" # 如果请求均失败版本信息设为"Error"

        return latest_version

    status = version_check()

    if status != version:
        if status != "Error":
            if init:
                with main_card:
                    ui.notify(f"检查到可用更新：v{status}", progress=True, timeout=10000, color="orange-10")
            else:
                version_dialog()
        else:
            with main_card:
                ui.notify("检查更新失败", type="negative")
    else:
        with main_card:
            ui.notify("已是最新版本", type="positive")

# 礼物设置弹窗
with ui.dialog() as gift_setting_dialog, ui.card(align_items="center"):
    with ui.row():
        ui.button("加班设置", on_click=lambda: cd_setting_dialog())
        ui.button("挑战设置", on_click=lambda: gift_count_setting_dialog())
        ui.button("更新礼物", on_click=lambda: refresh_gift())
    ui.button("关闭", on_click=lambda: gift_setting_dialog.close())

# 统计相关弹窗
with ui.dialog() as gift_count_dialog, ui.card(align_items="center"):
    with ui.row():
        ui.button("盲盒盈亏", on_click=lambda: blind_box_value_dialog())
        ui.button("礼物统计", on_click=lambda: ui.navigate.to("/count", True))
    ui.button("关闭", on_click=lambda: gift_count_dialog.close())

with ui.dialog() as color_dialog, ui.card(align_items="center"):
    # 颜色输入框，颜色只在about和capture页面生效
    with ui.row():
        ui.color_input(label="预览颜色", value="#5a85ad", on_change=lambda: save_config(), preview=config["color"]).style(f"width: 120px").bind_value(config, "color")
        ui.color_input(label="按钮颜色", value="#eddad2", on_change=lambda: save_config(), preview=config["btn_color"]).style(f"width: 120px").bind_value(config, "btn_color")
        ui.color_input(label="文字颜色", value="#000000", on_change=lambda: save_config(), preview=config["text_color"]).style(f"width: 120px").bind_value(config, "text_color")
    ui.button("关闭", on_click=lambda: color_dialog.close())


# 创建主界面
with ui.card(align_items="center").classes("absolute-center") as main_card:
    asyncio.run(check_update(True))
    time_badge = ui.badge("00:00:00", outline=True, color="").classes("text-9xl").style(f"color: {btn_color}") # 创建时钟
    time_badge_inherit = ui.badge(0).bind_text_from(app.storage.general, "countdown_time") # 倒计时数据继承
    gift_challenge_count = ui.badge(0).bind_text_from(app.storage.general, "gift_challenge_count") # 投喂挑战总数
    gift_play_unit_main = ui.label().bind_text_from(app.storage.general, "gift_challenge_unit") # 投喂挑战单位
    gift_play_text_main = ui.label().bind_text_from(app.storage.general, "gift_challenge_text") # 投喂挑战项目
    time_badge_inherit.set_visibility(False) # 隐藏继承数据徽章
    gift_challenge_count.set_visibility(False) # 隐藏投喂挑战总数徽章
    gift_play_unit_main.set_visibility(False) # 隐藏投喂挑战单位标签
    gift_play_text_main.set_visibility(False) # 隐藏投喂挑战项目标签

    # 时间输入框
    with ui.row():
        input_hour = ui.number("时", value=0, min=0).style("width: 100px")
        input_minute = ui.number("分", value=0, min=0).style("width: 100px")
        input_second = ui.number("秒", value=0, min=0).style("width: 100px")

    # 倒计时按钮
    with ui.row():
        # Start button
        start_button = ui.button('开始', on_click=lambda: start_task())
        start_button.disable()

        # Pause button
        pause_button = ui.button('暂停', on_click=lambda: countdown_timer.pause())
        pause_button.disable()

        # Resume button
        resume_button = ui.button('继续', on_click=lambda: countdown_timer.resume())
        resume_button.disable()

        # Stop button
        cancel_button = ui.button('停止', on_click=lambda: countdown_timer.stop(time_badge))
        cancel_button.disable()

        # Add time Button
        add_button = ui.button("增加", on_click=lambda: add_time())
        add_button.disable()

        # Sub Time Button
        sub_button = ui.button("减少", on_click=lambda: sub_time())
        sub_button.disable()

    ui.separator()

    # 房间号
    with ui.row(align_items="center"):
        room_id = ui.input("房间号", on_change=lambda: save_config()).style("width: 120px").bind_value(config, "room_id").on_value_change(lambda e: GiftManager.set_room_id(e.value)) # 实时写入房间号到配置文件

        with ui.column().classes("gap-0"):
            b_connect_switch = ui.switch("连接至弹幕服务器", on_change=lambda: check_b_connect_status()).props('checked-icon="check" color="green" unchecked-icon="clear"')
            show_capture_gift_list_switch = ui.switch("OBS显示投喂记录", value=False, on_change=lambda: save_config()).bind_value(config, "show_capture_gift_list").props('color="btn"')

        with ui.column().classes("gap-0"):
            gift_challenge_switch = ui.switch("启用投喂挑战", value=False, on_change=lambda: save_config()).props('color="btn"')
            gift_challenge_switch.disable()

            with ui.row().classes("gap-0"):
                ui.label("登录状态：")
                login_status = ui.label("未连接").classes("text-red")

            with ui.row().classes("gap-0"):
                ui.label("当前行数：")
                ui.label().bind_text_from(app.storage.general, "lines")

    ui.separator()

    # 按钮组
    with ui.row():
        ui.button("礼物设置", on_click=lambda: gift_setting_dialog.open())
        ui.button("颜色设置", on_click=lambda: color_dialog.open())
        ui.button("统计相关", on_click=lambda: gift_count_dialog.open())

    with ui.row():
        # Login bilibili button
        ui.button("登录账号", on_click=lambda: bili_login())
        # Update version button
        ui.button("检查更新", on_click=lambda: check_update())
        # Changelog button
        ui.button("更新日志", on_click=lambda: ui.navigate.to("/changelog"))
        # Preview page button
        ui.button("界面预览", on_click=lambda: open_capture())

    # obs源
    with ui.label(f"http://{host}:{port}/capture_cd").on("click", js_handler=f'() => navigator.clipboard.writeText("http://{host}:{port}/capture_cd")').on("click", lambda: ui.notify("已复制至剪贴板", type="info")):
        ui.tooltip("OBS倒计时浏览器源URL，单击可复制至剪贴板")
    with ui.label(f"http://{host}:{port}/capture_gift").on("click", js_handler=f'() => navigator.clipboard.writeText("http://{host}:{port}/capture_gift")').on("click", lambda: ui.notify("已复制至剪贴板", type="info")):
        ui.tooltip("OBS投喂挑战浏览器源URL，单击可复制至剪贴板")

    init_task()
    countdown_timer.inherit_time(int(time_badge_inherit.text))

    if not app.storage.general["startup_check_bili_auth"]:
        with ui.dialog() as init_login_dialog, ui.card(align_items="center"):
            ui.label("您似乎未登录B站账号，是否需要登录？")
            ui.label("未登录历史礼物功能可能无法显示用户名且无法获取最新的盲盒数据")
            ui.label("建议使用小号登录，以免账号被风控")
            with ui.row():
                ui.button("扫码登录", on_click=lambda: bili_login(True))
                ui.button("取消", on_click=lambda: init_login_dialog.close())

        if config["room_id"] != "":
            app.storage.general["startup_check_bili_auth"] = True
            init_login_dialog.open()

# about按钮
with ui.page_sticky(position='bottom-right', x_offset=10, y_offset=10):
    ui.button(on_click=lambda: ui.navigate.to("/about", new_tab=True), icon='contact_support').props('fab')

@ui.page('/changelog')
def _():
    changelog()

if app.storage.general["version"] != version: # 如果版本号不一致
    app.storage.general["version"] = version # 更新版本号
    ui.navigate.to("/changelog") # 跳转到更新日志页面

@ui.page('/count')
def _():
    ui.query('body').style(f'background: url("static/bg_vita.png") fixed')
    try:
        with open("data/gift_statistics.json", "r", encoding="utf-8") as f:
            count = json.load(f)
        if count == {}:
            raise Exception("No data")
    except:
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

        try:
            text = requests.get("https://nya-wsl.com/bili_travail/chat_msg.json")
        except Exception as e:
            logger.exception(f"获取文本失败：{e}")
            try:
                text = requests.get("http://version.nya-wsl.cn/bili_travail/chat_msg.json")
            except Exception as e:
                logger.exception(f"获取文本失败：{e}")

        text.encoding = "utf-8"
        if text.status_code == 200 or not config["local_text"]: # 如果请求状态为200且配置文件未启用本地文本
            if random.random() < 0.3:
                msg_index = []
                for k in text.json().keys():
                    msg_index.append(k)
                msg_index.remove("group_a")
                msg = text.json()[random.choice(msg_index)]
                ui.chat_message(msg["text_a"], avatar=bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"), name="高橋はるき", text_html=True, sent=True)
                ui.chat_message(msg["text_b"], avatar=bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"), name="狐日泽", text_html=True)
            else:
                ui.chat_message(text.json()["group_a"]["text_a"], avatar=bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"), name="高橋はるき", text_html=True, sent=True)
                ui.chat_message(text.json()["group_a"]["text_b"], avatar=bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"), name="狐日泽", text_html=True)
        else:
            text_a = read_or_create_file("data/text_a.txt", "代码没写完，哪有脸睡觉")
            text_b = read_or_create_file("data/text_b.txt", 'alias cd="sudo rm -rf"')

            ui.chat_message(text_a, avatar=bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"), name="高橋はるき", text_html=True, sent=True)
            ui.chat_message(text_b, avatar=bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"), name="狐日泽", text_html=True)

        # 项目介绍
        ui.html('A Project of <u><a href="https://nya-wsl.com" target="_blank">Nya-WSL</a></u>.')
        ui.html('Powered by <u><a href="https://nicegui.io" target="_blank">NiceGUI</a></u> - <u><a href="https://github.com/xfgryujk/blivedm" target="_blank">blivedm</a></u>.')
        ui.label("Copyright © 2025. All rights reserved. ")
        ui.separator()

        # 开发组成员显示
        with ui.row(align_items="center"):
            with ui.column(align_items="center"):
                ui.label("程序架构").classes("text-blue")
                with ui.link(target="https://space.bilibili.com/16748991", new_tab=True):
                    with ui.avatar():
                        ui.image(bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"))
                ui.badge("高橋はるき", outline=True)
            with ui.column(align_items="center"):
                ui.label("程序开发").classes("text-blue")
                with ui.link(target="https://space.bilibili.com/8907402", new_tab=True):
                    with ui.avatar():
                        ui.image(bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"))
                ui.badge("狐日泽", outline=True)
            with ui.column(align_items="center"):
                ui.label("特别感谢").classes("text-blue")
                with ui.link(target="https://space.bilibili.com/3546729020394298/", new_tab=True):
                    with ui.avatar():
                        ui.image(bili_api.get_bili_img("https://i1.hdslb.com/bfs/face/1c90e9c3a52b13b898f4025a5282a394b09eeda0.jpg"))
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
try:
    ui.run(host=host, port=port, title=f"bili_travail | {version}", favicon="static/logo.ico", reload=False, show=False, native=True, window_size=[560, 650])
except:
    logger.error(f"run error: {traceback.format_exc()}")