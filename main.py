# Local Packages
from libs import log

try:
    # 该模块在打包时填入密钥后自动生成
    import env # type: ignore
except:
    with open("env.py", "w+", encoding="utf-8") as f:
        f.write(f"""
def get_key():
    return {{
        "ACCESS_KEY_ID": "",
        "ACCESS_KEY_SECRET": "",
        "APP_ID": 0
    }}
""")
    import env # type: ignore

import version as base_ver
import libs.config as travail_config

import blivedm.blivedm.models.web as web_models
import blivedm.blivedm.models.open_live as open_models

from libs import ping
from libs import styles
from libs import bili_api
from libs import travail_stat
from libs import dns_resolver
from libs import check_runtime
from libs import gift as get_gift
from libs import update as travail_update
from libs import gift_mapping as gift_map
from libs.changelog import changelog, get_log

from blivedm import blivedm

# Third Party Packages
import os
import re
import orjson
import shutil
import random
import psutil
import cpuinfo
import asyncio
import aiohttp
import requests
import datetime
import traceback
import itertools

from icecream import ic
from copy import deepcopy
from nicegui import ui, app
from itertools import islice
from multiprocessing import freeze_support
from packaging import version as pack_version
from nicegui import __version__ as gui_version
from apscheduler.schedulers.asyncio import AsyncIOScheduler

ver_strftime = env.get_key().get("version", datetime.datetime.now().strftime("%y%m%d%H%M"))
version = f"{base_ver.base_version}.{ver_strftime}"

logger = log.logger
logger.debug("version: {}", version)

scheduler = AsyncIOScheduler() # 创建调度器

# ================================
# 检查环境状态
# ================================

# 初始化NiceGUI
# asyncio.run(app.storage.general.initialize())
app.storage.general.indent = True  # 格式化storage # type: ignore
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

if not os.path.exists("data/blind_box_data.json"):
    with open("data/blind_box_data.json", "wb+") as f:
        f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

if not os.path.exists("data/time.json"):
    with open("data/time.json", "wb+") as f:
        f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

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

def format_seconds(seconds) -> str:
    """
    格式化时间

    :param seconds: 秒数
    """

    # 如果输入不是数字，直接返回
    if not isinstance(seconds, (int, float)):
        logger.warning(f"{seconds} 不是int或float，跳过格式化")
        return str(seconds)

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

def format_cd(seconds):
    minute, second = divmod(seconds, 60)
    hour, minute = divmod(minute, 60)
    return ("%02d:%02d:%02d" % (hour, minute, second))

# 检查storage状态
def init_storage():
    app.storage.general["gift_challenge_count"] = app.storage.general.get("gift_challenge_count", 0)
    app.storage.general["gift_challenge_unit"] = app.storage.general.get("gift_challenge_unit", "")
    app.storage.general["gift_challenge_text"] = app.storage.general.get("gift_challenge_text", "")
    app.storage.general["countdown_time"] = app.storage.general.get("countdown_time", 0)
    app.storage.general["version"] = app.storage.general.get("version", version)
    app.storage.general["startup_check_bili_auth"] = app.storage.general.get("startup_check_bili_auth", False)
    app.storage.general["ignore_cd"] = app.storage.general.get("ignore_cd", False)
    app.storage.general["custom_gift_rate"] = app.storage.general.get("custom_gift_rate", {})
    app.storage.general["gift_cd_rate"] = app.storage.general.get("gift_cd_rate", {"nega": 0, "zero": 0, "posi": 0})

# ================================
# 初始化配置文件
# ================================

init_storage()

base_config = travail_config.Config()
base_config.sync_config(base_config.load(), base_config.default_data)
config = base_config.load()

host = config["general"]["host"]  # type: ignore[index]
port = config["general"]["port"]  # type: ignore[index]
btn_color = config["color"]["btn_color"]  # type: ignore[index]

# 需申请哔哩哔哩直播开放平台开发者账号并将id、key和app_id填入config.json中，如需开箱即用请在 https://github.com/Nya-WSL/bili_travail/releases 下载
bili_keys = env.get_key()

if base_config.get("open_live", "ACCESS_KEY_ID", "") != "":
    ACCESS_KEY_ID= base_config.get("open_live", "ACCESS_KEY_ID", "")
else:
    ACCESS_KEY_ID= bili_keys.get("ACCESS_KEY_ID", "")

if base_config.get("open_live", "ACCESS_KEY_SECRET", "") != "":
    ACCESS_KEY_SECRET = base_config.get("open_live", "ACCESS_KEY_SECRET", "")
else:
    ACCESS_KEY_SECRET = bili_keys.get("ACCESS_KEY_SECRET", "")

if base_config.get("open_live", "APP_ID", 0) != 0:
    APP_ID = base_config.get("open_live", "APP_ID", 0)
else:
    APP_ID = bili_keys.get("APP_ID", 0)

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

# 设置所有按钮颜色为配置文件中的btn_color
# 如果nicegui版本低于v3.5.0
# 使用__init__.__kwdefaults__设置默认属性（字体颜色默认黑色）
# 否则使用default_props设置默认属性（字体颜色默认白色）
if pack_version.parse(gui_version) < pack_version.parse("3.5.0"):
    ui.button.__init__.__kwdefaults__['color'] = btn_color  # pyright: ignore[reportOptionalSubscript]
else:
    ui.button.default_props(f'color={btn_color} text-color="black"')

GiftManager = get_gift.BiliGiftManager()

async def create_blind_box():
    box_id = []
    blind_box = {}
    box_price = {}
    gifts = await GiftManager.get_room_gift("android")

    if gifts is None:
        logger.error("未获取到礼物数据")
        return

    for gift in gifts:
        if re.search("盒", gift["name"]):
            box_id.append(gift["id"])

    if box_id == []:
        logger.error("未获取到盲盒数据")
        return

    blind_boxes = await GiftManager.get_blind_box(box_id)

    # 忽略盲盒礼物图标，图标在gift.get_config()中已经处理了
    for box, box_gifts in blind_boxes.items():
        box_price.setdefault(box, 0)
        box_price[box] = int(box_gifts['price'] / 100) # API的单位是金瓜子，这里换算为电池
        if not box in blind_box:
            blind_box[box] = []
        for gift in box_gifts["gifts"]:
            blind_box[box].append(gift['gift'])

    with open("data/blind_box_data.json", "wb+") as f:
        f.write(orjson.dumps(blind_box, option=orjson.OPT_INDENT_2))

    with open("data/blind_box_price.json", "wb+") as f:
        f.write(orjson.dumps(box_price, option=orjson.OPT_INDENT_2))

async def init_config():
    """
    初始化礼物数据
    """
    # # 确保礼物数据文件存在，如果不存在，则先初始化礼物数据
    # if not os.path.exists("data/gifts.json") or not os.path.exists("data/gift_img.json"):
    #     # 如果配置文件中包含房间号，则传入；否则会直接初始化空数据
    #     room_id = base_config.get("general", "room_id", "")

    #     # 如果配置文件中有room_id，则使用该房间号
    #     if room_id:
    #         GiftManager.set_room_id(room_id)
    #         gift_config = await GiftManager.get_config("data/gift_img.json") # 使用B站api
    #         # 如获取B站礼物数据失败，则从Nya-WSL服务器或本地注入方式写入
    #         if not gift_config:
    #             await GiftManager.init_gift("data/gift_img.json")

    # 初始化数据
    if not os.path.exists("data/gift_img.json"):
        with open("data/gift_img.json", "wb+") as f:
            f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

    if not os.path.exists("data/gifts.json"):
        with open("data/gifts.json", "wb+") as f:
            f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

    if not os.path.exists("data/gifts_count.json"):
        with open("data/gifts_count.json", "wb+") as f:
            f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

    if not os.path.exists("data/special.json"):
        with open("data/special.json", "wb+") as f:
            f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

    if not os.path.exists("data/special_count.json"):
        with open("data/special_count.json", "wb+") as f:
            f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

asyncio.run(init_config())

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

    with open(f"data/sys_info/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "wb+") as f:
        f.write(orjson.dumps(sys_info, option=orjson.OPT_INDENT_2))

    return sys_info

@ui.page("/debug")
async def debug():
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

async def start_handler():
    await run_client()

async def run_client():
    global client

    client = blivedm.OpenLiveClient(
        access_key_id=ACCESS_KEY_ID,  # pyright: ignore[reportArgumentType]
        access_key_secret=ACCESS_KEY_SECRET,  # pyright: ignore[reportArgumentType]
        app_id=int(APP_ID),  # pyright: ignore[reportArgumentType]
        room_owner_auth_code=base_config.get("general", "auth_code", None),  # pyright: ignore[reportArgumentType]
    )
    handler = BiliHandler()
    client.set_handler(handler)
    client.start()

    try:
        await client.join()
    finally:
        await client.stop_and_close()

# 获取礼物信息
class BiliHandler(blivedm.BaseHandler):
    heart_count = 0
    # 心跳数据
    async def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage): # type: ignore[override]
        global b_connect_status

        self.heart_count += 1
        logger.info("触发心跳")
        if self.heart_count == 1:
            room_id = client.room_id
            if room_id != None:
                room_id = room_id
            else:
                room_id = 3

            config = base_config.load()
            config["general"]["room_id"] = room_id  # pyright: ignore[reportIndexIssue]
            base_config.save(config)
            GiftManager.set_room_id(room_id)

            with main_card:
                ui.notify("正在等待B站下发自定义礼物数据，请稍候...", type="info")
                await asyncio.sleep(5) # 等待5秒B站发送自定义礼物数据

                try:
                    await refresh_gift(True) # 刷新礼物数据
                except: # type: ignore
                    ui.notify("获取礼物数据失败，可能导致部分功能异常", type="warning")

            logger.info(f"已连接至{room_id}")

            uid = client.room_owner_uid
            if uid != None:
                now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                await travail_stat.stat(room_id, uid, version, now_time)
                login_status.set_text(room_id)  # pyright: ignore[reportArgumentType]
                login_status.classes("text-green")
                b_connect_status = True # 在第一次心跳时设置状态为已连接至弹幕服务器
                b_connect_switch.set_value(True)
                b_connect_switch.set_text("已连接弹幕服务器")
            else:
                login_status.set_text("未连接")
                login_status.classes(replace="text-red")

    # 礼物数据
    async def _on_open_live_gift(self, client: blivedm.OpenLiveClient, message: open_models.GiftMessage):  # pyright: ignore[reportIncompatibleMethodOverride]
        logger.debug("收到礼物")
        gift = message.gift_name
        num = message.gift_num
        uname = message.uname
        price = message.price / 100
        is_paid = message.paid
        if len(uname) > 8:
            uname = uname[:5] + "..."

        await self._on_gift_play(gift, num, uname, message, int(price))  # type: ignore[arg-type]
        self._on_gift_statistics(gift, num, uname, int(price))  # type: ignore[arg-type]
        logger.debug(message)


    # 舰队数据
    async def _on_open_live_buy_guard(self, client: blivedm.OpenLiveClient, message: open_models.GuardBuyMessage):  # pyright: ignore[reportIncompatibleMethodOverride]
        gift = message.guard_level
        num = message.guard_num
        uname = message.user_info.uname
        price = message.price / 100

        if gift == 1:
            gift = "总督"
        elif gift == 2:
            gift = "提督"
        elif gift == 3:
            gift = "舰长"
        else:
            gift = "神秘物种"

        if len(uname) > 8:
            uname = uname[:5] + "..."

        await self._on_gift_play(gift, num, uname, False)
        self._on_gift_statistics(gift, num, uname, price)
        logger.debug(message)

    # ================================
    # 醒目留言
    # 待开发
    # ================================
    def _on_open_live_super_chat(self, client: blivedm.OpenLiveClient, message: open_models.SuperChatMessage):
        logger.info(f'[{message.room_id}] 醒目留言 ¥{message.rmb} {message.uname}：{message.message}')

    def _on_open_live_enter_room(self, client: blivedm.OpenLiveClient, message: open_models.RoomEnterMessage):
        logger.info(f'{message.uname} 进入 {message.room_id}')

    def _on_gift_statistics(self, gift, num, uname, price: int | float = 0):
        if not os.path.exists("data/gift_statistics.json"):
            with open("data/gift_statistics.json", "wb+") as f:
                f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

        with open("data/gift_statistics.json", "rb") as f:
            count = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        count.setdefault(gift, {"num": 0, "price": 0, "user": []})
        users = count[gift]["user"]

        if uname not in users:
            users.append(uname)

        num += count[gift]["num"]

        if gift == "辣条":
            price = 0

        count[gift] = {"num": num, "price": price, "user": users}

        with open("data/gift_statistics.json", "wb+") as f:
            f.write(orjson.dumps(count, option=orjson.OPT_INDENT_2))

    # 收到礼物后执行函数
    async def _on_gift_play(self, gift, num, uname, message, price: int | float = 0):
        is_blind_box = False

        def blind_box_value(gift, num : int, price : int | float, box_name):
            if not os.path.exists("data/blind_box_value.json"):
                with open("data/blind_box_value.json", "wb+") as f:
                    f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

            with open("data/blind_box_value.json", "rb") as f:
                box_value = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

            if box_value.get(box_name, None) is None:
                box_value[box_name] = {}

            if box_value[box_name].get(gift, None) is None:
                box_value[box_name][gift] = {"num": 0, "price": 0}

            box_value[box_name][gift] = {"num": box_value[box_name][gift]["num"] + num, "price": price}

            with open("data/blind_box_value.json", "wb+") as f:
                f.write(orjson.dumps(box_value, option=orjson.OPT_INDENT_2))

        if b_connect_status:  # True则已连接至弹幕服务器
            if gift_challenge_switch.value:  # True则为投喂挑战开关为开状态
                # 检查投喂挑战数据文件是否存在
                if os.path.exists("data/gifts_count.json"):
                    with open("data/gifts_count.json", "rb") as f:
                        gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
                    with open("data/special_count.json", "rb") as f:
                        special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

                    # 如果礼物数据没有该礼物则写入
                    if gift not in gifts and gift not in special:
                        with open("data/gift_img.json", "rb") as f:
                            gift_img = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
                        gift_img[gift] = "https://s1.hdslb.com/bfs/live/d57afb7c5596359970eb430655c6aef501a268ab.png"
                        with open("data/gift_img.json", "wb+") as f:
                            f.write(orjson.dumps(gift_img, option=orjson.OPT_INDENT_2))

                    # 初始化盲盒数据
                    with open("data/blind_box_data.json", "rb") as f:
                        blind_box = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

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
                                if gifts.get(box_name, None) != None or special.get(box_name, None) != None:
                                    origin_gift = gift
                                    if gift not in special and gifts.get(gift, None) is None:
                                        is_blind_box = True
                                        gift = box_name

                                    blind_box_value(origin_gift, num, price, box_name) # 盲盒价值

                    # 如果收到的礼物在special.json中
                    if gift in special:
                        changed_num = int(app.storage.general["gift_challenge_count"])  # 初始化为当前计数

                        if special[gift] == "double": # 加倍挑战
                            changed_num = int(app.storage.general["gift_challenge_count"]) << int(num)

                            if is_blind_box:
                                gift = origin_gift

                            if show_capture_gift_list_switch.value and capture_gift_is_created:
                                capture_challenge_gift_list_show(uname, gift, num, f"2^{int(num)}倍", message)

                        if special[gift] == "half": # 减半挑战
                            changed_num = int(app.storage.general["gift_challenge_count"]) >> int(num)

                            if is_blind_box:
                                gift = origin_gift

                            if show_capture_gift_list_switch.value and capture_gift_is_created:
                                capture_challenge_gift_list_show(uname, gift, num, f"2^(-{int(num)})倍", message)

                        if special[gift] == "clear": # 清空挑战
                            changed_num = 0

                            if is_blind_box:
                                gift = origin_gift

                            if show_capture_gift_list_switch.value and capture_gift_is_created:
                                capture_challenge_gift_list_show(uname, gift, num, "清空", message)

                        if type(special[gift]) == list: # 随机挑战，只有随机的类型为list
                            total_changed_num = 0

                            for _ in range(num):
                                random_num = random.randint(special[gift][0], special[gift][1])
                                total_changed_num += random_num

                            changed_num = int(app.storage.general["gift_challenge_count"]) + total_changed_num
                            gift_list_show_num = str(total_changed_num)

                            if is_blind_box:
                                gift = origin_gift

                            if show_capture_gift_list_switch.value and capture_gift_is_created:
                                capture_challenge_gift_list_show(uname, gift, num, gift_list_show_num + app.storage.general["gift_challenge_unit"], message)

                        app.storage.general["gift_challenge_count"] = changed_num  # 重设投喂挑战数据

                    # 如果收到的礼物不在special.json中
                    elif gift in gifts:
                        changed_num = (gifts[gift] * int(num)) + int(app.storage.general["gift_challenge_count"]) # （设定的值 * 礼物数量） + 目前总数
                        gift_list_show_num = str(int(gifts[gift] * int(num)))

                        if is_blind_box:
                            gift = origin_gift

                        if gifts.get(gift, None) != None or is_blind_box:
                            if show_capture_gift_list_switch.value and capture_gift_is_created:
                                capture_challenge_gift_list_show(uname, gift, num, gift_list_show_num + app.storage.general["gift_challenge_unit"], message)

                        app.storage.general["gift_challenge_count"] = changed_num
                else:
                    logger.error("投喂挑战失败，未找到礼物数据文件")

            if cd_status or app.storage.general.get("ignore_cd", False):  # True则倒计时为启动状态
                if os.path.exists("data/gifts.json"):
                    with open("data/gifts.json", "rb") as f:
                        gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
                    with open("data/special.json", "rb") as f:
                        special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

                    custom_gifts = GiftManager.custom_gifts
                    current_seconds = countdown_timer.remaining_seconds

                    if gift not in gifts and gift not in special:
                        with open("data/gift_img.json", "rb") as f:
                            gift_img = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
                        gift_img[gift] = "https://s1.hdslb.com/bfs/live/d57afb7c5596359970eb430655c6aef501a268ab.png"
                        with open("data/gift_img.json", "wb+") as f:
                            f.write(orjson.dumps(gift_img, option=orjson.OPT_INDENT_2))

                    # 初始化盲盒数据
                    with open("data/blind_box_data.json", "rb") as f:
                        blind_box = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

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
                                if gifts.get(box_name, None) != None or special.get(box_name, None) != None:
                                    origin_gift = gift
                                    if gift not in special and gifts.get(gift, None) is None:
                                        is_blind_box = True
                                        gift = box_name

                                    blind_box_value(origin_gift, num, price, box_name) # 盲盒价值

                    if gift in special:
                        new_seconds = current_seconds  # 初始化为当前剩余秒数

                        if special[gift] == "double":
                            new_seconds = current_seconds * (2 ** num)

                            if is_blind_box:
                                gift = origin_gift

                            if show_capture_gift_list_switch.value and capture_cd_is_created:
                                capture_cd_gift_list_show(uname, gift, num, f"2^{int(num)}倍", message)

                        if special[gift] == "half":
                            new_seconds = current_seconds / (2 ** num)

                            if is_blind_box:
                                gift = origin_gift

                            if show_capture_gift_list_switch.value and capture_cd_is_created:
                                capture_cd_gift_list_show(uname, gift, num, f"-2^{int(num)}倍", message)

                        if special[gift] == "clear":
                            new_seconds = 3

                            if is_blind_box:
                                gift = origin_gift

                            if show_capture_gift_list_switch.value and capture_cd_is_created:
                                capture_cd_gift_list_show(uname, gift, num, "清空", message)

                        if type(special[gift]) == list:
                            total_changed_time = 0
                            rate = app.storage.general["gift_cd_rate"]

                            if gift in custom_gifts:
                                custom_rate = float(app.storage.general["custom_gift_rate"][gift])
                            else:
                                custom_rate = 1

                            for _ in range(num):
                                r = round(random.random(), 2)

                                if r <= rate.get("nega", 0) and rate.get("nega", 0) != 0:
                                    if special[gift][0] >= 0: # 如果下界>=0，为防止抛错将使用默认算法
                                        total_changed_time += random.randint(special[gift][0], special[gift][1]) * custom_rate
                                    else:
                                        total_changed_time += random.randint(special[gift][0], -1) * custom_rate

                                elif r <= rate.get("zero", 0) + rate.get("nega", 0) and rate.get("zero", 0) != 0: # 如果r小于等于减时概率则会先进入减时的if语句，如果r大于减时概率但小于等于两者之和则会进入不变的elif语句
                                    total_changed_time += 0

                                elif r <= rate.get("posi", 0) + rate.get("nega", 0) + rate.get("zero", 0) and rate.get("posi", 0) != 0: # 同上
                                    if special[gift][1] <= 0:# 如果上界<=0，为防止抛错将使用默认算法
                                        total_changed_time += random.randint(special[gift][0], special[gift][1]) * custom_rate
                                    else:
                                        total_changed_time += random.randint(1, special[gift][1]) * custom_rate

                                else:
                                    total_changed_time += random.randint(special[gift][0], special[gift][1]) * custom_rate

                            new_seconds = current_seconds + total_changed_time

                            if is_blind_box:
                                gift = origin_gift

                            if show_capture_gift_list_switch.value and capture_cd_is_created:
                                capture_cd_gift_list_show(uname, gift, num, format_seconds(total_changed_time), message)

                        countdown_timer.set_remaining_seconds(new_seconds) # 重设倒计时数据

                    if gift in gifts:
                        delta_seconds = gifts[gift] * int(num)

                        if gift in custom_gifts:
                            delta_seconds = delta_seconds * float(app.storage.general["custom_gift_rate"][gift])

                        new_seconds = countdown_timer.remaining_seconds + delta_seconds
                        gift_list_show_time = delta_seconds

                        if is_blind_box:
                            gift = origin_gift

                        if gifts.get(gift, None) != None or is_blind_box:
                            if show_capture_gift_list_switch.value and capture_cd_is_created:
                                capture_cd_gift_list_show(uname, gift, num, format_seconds(gift_list_show_time), message)

                        countdown_timer.set_remaining_seconds(new_seconds) # 重设倒计时数据
                else:
                    logger.error("计时失败，未找到礼物数据文件")

def update_btn_state(state: str):
    if state == "start":
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
    elif state == "pause":
        resume_button.enable()
        pause_button.disable()
        add_button.disable()
        sub_button.disable()
    elif state == "resume":
        pause_button.enable()
        resume_button.disable()
        add_button.enable()
        sub_button.enable()
    elif state == "stop":
        start_button.enable()
        cancel_button.disable()
        pause_button.disable()
        resume_button.disable()
        add_button.disable()
        sub_button.disable()
        # 重置时间输入框
        input_hour.set_value(0)
        input_minute.set_value(0)
        input_second.set_value(0)

# 倒计时类
class CountdownTimer:
    def __init__(self):
        self.remaining_time = datetime.timedelta(0) # 初始化剩余时间
        self.target_time: datetime.datetime | None = None # 初始化目标时间
        self._paused = False # 初始化暂停状态
        self._running = False # 初始化运行状态
        self._paused_event = asyncio.Event() # 初始化event
        self._paused_event.set()  # 最开始没有暂停
        self._task = None # 初始化task
        self.exit_timer = None

    def exit_func(self):
        logger.info("计时器结束，退出程序")
        app.shutdown()

    @property
    def remaining_seconds(self) -> float:
        if not self.target_time:
            return 0.0
        return max((self.target_time - datetime.datetime.now()).total_seconds(), 0.0)

    def set_remaining_seconds(self, seconds: float) -> None:
        if seconds < 0:
            seconds = 0
        now = datetime.datetime.now()
        self.target_time = now + datetime.timedelta(seconds=seconds)
        self.remaining_time = datetime.timedelta(seconds=seconds)
        app.storage.general["countdown_time"] = seconds

    # 倒计时运行函数
    async def update(self):
        global cd_status
        while self._running and self.target_time:
            if self._paused:
                await self._paused_event.wait()  # 暂停时等待

            if self.remaining_seconds <= 0:
                self.stop()
                break

            self.remaining_time = datetime.timedelta(seconds=self.remaining_seconds)
            app.storage.general["countdown_time"] = self.remaining_seconds
            cd_status = True
            await asyncio.sleep(1)

    # 运行倒计时
    def start(self):
        global cd_status
        # 如果倒计时未在运行
        if self._running:
            return

        self._running = True # 修改运行状态
        if self.target_time is not None and self.target_time - datetime.datetime.now() != datetime.timedelta(0): # 防止写入0时开始倒计时
            self._task = asyncio.create_task(self.update()) # 创建倒计时协程
            update_btn_state("start") # 更新按钮状态
            cd_status = True # 设置倒计时运行状态
            if self.exit_timer and self.exit_timer.active:
                logger.info("倒计时开始，停止计时器")
                self.exit_timer.cancel(with_current_invocation=True) # 关闭退出计时器
        else:
            ui.notify("请输入时间", type="negative")
            self._running = False

    # 暂停倒计时
    async def pause(self):
        global cd_status
        if self._running and not self._paused: # 如果倒计时在运行且没有暂停
            self._paused = True
            self._paused_event.clear()  # 暂停计时器
            update_btn_state("pause") # 更新按钮状态
            cd_status = False

    # 继续倒计时
    def resume(self):
        global cd_status
        if self._running and self._paused:
            self._paused = False
            self._paused_event.set()  # 恢复计时器
            self.set_remaining_seconds(app.storage.general["countdown_time"])
            update_btn_state("resume") # 更新按钮状态
            cd_status = True

    # 停止倒计时
    def stop(self):
        global cd_status
        if self._running:
            self._running = False
            self._paused = False
            if self._task:
                self._task.cancel() # 结束协程
            app.storage.general["countdown_time"] = 0
            self.remaining_time = datetime.timedelta(0)
            update_btn_state("stop") # 更新按钮状态
            cd_status = False
            if not self.exit_timer and base_config.get("bool", "exit_timer", True):
                logger.info("倒计时停止，启动计时器")
                self.exit_timer = app.timer(base_config.get("num", "exit_time", 1800), lambda: self.exit_func(), once=True) # pyright: ignore[reportArgumentType]
        else:
            if reset_inherit_status:
                app.storage.general["countdown_time"] = 0
                self.remaining_time = datetime.timedelta(0)
                cancel_button.set_text("停止")
                cancel_button.disable()

def sort_dict(dictionary, type_order=None, sort_within_type=False):
    """
    高级排序：先按类型排序，再按值排序

    Args:
        dictionary: 要排序的字典
        type_order: 类型顺序, None: [int, str, list]
        sort_within_type: 是否在同一类型内进行排序
    """
    if type_order is None:
        type_order = [int, str, list]

    type_priority = {t: i for i, t in enumerate(type_order)}

    def sort_key(item):
        key, value = item
        value_type = type(value)
        type_rank = type_priority.get(value_type, len(type_order))

        if sort_within_type:
            # 在同一类型内，按值排序
            if value_type == int or value_type == str:
                return (type_rank, value)
            elif value_type == list:
                return (type_rank, str(value))  # 列表转换为字符串进行比较
            else:
                return (type_rank, str(value))
        else:
            # 只按类型排序
            return type_rank

    sorted_items = sorted(dictionary.items(), key=sort_key)
    return dict(sorted_items)

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
            rate_column.set_visibility(True)
            # rate_nega.set_visibility(True)
            # rate_posi.set_visibility(True)
            # rate_zero.set_visibility(True)
        else:
            min.set_visibility(False)
            max.set_visibility(False)
            rate_column.set_visibility(False)
            # rate_nega.set_visibility(False)
            # rate_posi.set_visibility(False)
            # rate_zero.set_visibility(False)

        if status.value == "double" or status.value == "clear" or status.value == "random" or status.value == "half":
            time.disable()
        else:
            time.enable()

        if status.value == "delete":
            time.disable()

    # 确定按钮
    def run():
        global refresh_capture_cd
        with open("data/gifts.json", "rb+") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/special.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        if gift_name.value is None or time.value < 0:
            if gift_name.value is None:
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
                    gifts.pop(gift_name.value)
            elif status.value == "half":
                special[gift_name.value] = "half"
                if gift_name.value in gifts:
                    gifts.pop(gift_name.value)
            elif status.value == "clear":
                special[gift_name.value] = "clear"
                if gift_name.value in gifts:
                    gifts.pop(gift_name.value)
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
                    gifts.pop(gift_name.value)

            gifts = sort_dict(dictionary=gifts, sort_within_type=True)  # 对礼物数据进行排序

            with open("data/gifts.json", "wb+") as f:
                f.write(orjson.dumps(gifts, option=orjson.OPT_INDENT_2))
            with open("data/special.json", "wb+") as f:
                f.write(orjson.dumps(special, option=orjson.OPT_INDENT_2))

            refresh_capture_cd = True # 设置capture刷新状态
            refresh_card()

    # 重置按钮
    def reset():
        def double_check():
            global refresh_capture_cd
            with open("data/gifts.json", "wb+") as f:
                f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))
            with open("data/special.json", "wb+") as f:
                f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))
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
        with open("data/gifts.json", "rb+") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/special.json", "rb+") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        if gift_name.value in gifts:
            gifts.pop(gift_name.value)
        if gift_name.value in special:
            special.pop(gift_name.value)

        gifts = sort_dict(dictionary=gifts, sort_within_type=True)  # 对礼物数据进行排序

        with open("data/gifts.json", "wb+") as f:
            f.write(orjson.dumps(gifts, option=orjson.OPT_INDENT_2))
        with open("data/special.json", "wb+") as f:
            f.write(orjson.dumps(special, option=orjson.OPT_INDENT_2))

        refresh_capture_cd = True # 设置capture刷新状态
        refresh_card()

    def del_gift(is_special, k):
        global refresh_capture_cd
        with open("data/gifts.json", "rb") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/special.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        if is_special:
            special.pop(k)
            with open("data/special.json", "wb+") as f:
                f.write(orjson.dumps(special, option=orjson.OPT_INDENT_2))
        else:
            gifts.pop(k)
            gifts = sort_dict(dictionary=gifts, sort_within_type=True)  # 对礼物数据进行排序
            with open("data/gifts.json", "wb+") as f:
                f.write(orjson.dumps(gifts, option=orjson.OPT_INDENT_2))

        refresh_capture_cd = True
        refresh_card()

    def create_card():
        with open("data/gifts.json", "rb") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/special.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        if gifts != {}:
            for k,v in gifts.items():
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
                        if v == "half":
                            v = "减半"
                        ui.label(v)
                        ui.button("删除", on_click=lambda k = k: del_gift(True, k))

    def refresh_card():
        gift_card.clear()  # 清空卡片内容
        with gift_card:
            create_card()

    # 弹窗
    with ui.dialog() as cd_dialog, ui.card(align_items="center"):
        with open("data/gift_img.json", "rb") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        ui.label("设置预览").classes("text-2xl text-blue").style("font-size: 20px")

        with ui.card().classes("w-full") as gift_card:
            create_card()

        ui.separator() # 分割线

        with ui.row(align_items="center"):
            gift_name = ui.select(label="礼物选择", options=list(gifts.keys()), with_input=True, clearable=True).style("width: 200px")

        status = ui.toggle(options={"add": "加时", "sub": "减时", "double": "加倍", "half": "减半", "clear": "清空", "random": "随机"}, on_change=lambda: show()).classes('items-center')

        # 数值输入框
        with ui.row():
            min = ui.number("随机最小数(秒)", value=0)
            max = ui.number("随机最大数(秒)", value=0)
            time = ui.number(label="时长(秒)", value=0, min=0)
            time.set_visibility(False)
            min.set_visibility(False)
            max.set_visibility(False)

        with ui.column(align_items="center") as rate_column:
            ui.label("随机玩法权重设置(设置会自动保存)")
            ui.link("使用说明", "https://docs.travail.nya-wsl.com/guides/usage/play/#随机权重", True)

        # rate_column.set_visibility(False)

        def verify_rate():
            if "rate_posi" in globals() or "rate_posi" in locals(): # 防止未创建输入框时调用函数导致报错
                rate_posi_value = round(1 - rate_nega.value - rate_zero.value, 2)
                if rate_posi_value < 0:
                    rate_posi_value = 0
                rate_posi.set_value(rate_posi_value)

        # 概率输入框
        with ui.row():
            rate_nega = ui.number(label="减时概率", value=0, min=0, max=1, step=0.1, on_change=lambda: verify_rate()).bind_value(app.storage.general["gift_cd_rate"], "nega")
            rate_zero = ui.number(label="零的概率", value=0, min=0, max=1, step=0.1, on_change=lambda: verify_rate()).bind_value(app.storage.general["gift_cd_rate"], "zero")
            rate_posi = ui.number(label="加时概率", value=0, min=0, max=1, step=0.1, on_change=lambda: verify_rate()).bind_value(app.storage.general["gift_cd_rate"], "posi")
            # rate_nega.set_visibility(False)
            # rate_zero.set_visibility(False)
            # rate_posi.set_visibility(False)

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
            with open("data/blind_box_value.json", "wb+") as f:
                f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))
        if not os.path.exists("data/blind_box_price.json"):
            with open("data/blind_box_price.json", "wb+") as f:
                f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

        with open("data/blind_box_value.json", "rb") as f:
            box_value = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/blind_box_price.json", "rb") as f:
            box_price_list = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        value_list = {}
        price_list = {}
        for k,v in box_value.items():
            if not k in box_price_list:
                box_price_list[k] = 0

            for gift, value in v.items():
                gift_name = gift
                num = int(value["num"])
                price = int(value["price"])
                if value_list.get(k, None) is None:
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
        with open("data/blind_box_value.json", "wb+") as f:
            f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

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
        if status.value == "double" or status.value == "clear" or status.value == "random" or status.value == "half":
            number.disable()
        else:
            number.enable()
        if status.value == "delete":
            number.disable()

    def run():
        global refresh_capture_gift
        with open("data/gifts_count.json", "rb+") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/special_count.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        if gift_name.value is None or number.value < 0:
            if gift_name.value is None:
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
                    gifts.pop(gift_name.value)
            elif status.value == "half":
                special[gift_name.value] = "half"
                if gift_name.value in gifts:
                    gifts.pop(gift_name.value)
            elif status.value == "clear":
                special[gift_name.value] = "clear"
                if gift_name.value in gifts:
                    gifts.pop(gift_name.value)
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
                    gifts.pop(gift_name.value)

            gifts = sort_dict(dictionary=gifts, sort_within_type=True)  # 对礼物数据进行排序

            with open("data/gifts_count.json", "wb+") as f:
                f.write(orjson.dumps(gifts, option=orjson.OPT_INDENT_2))
            with open("data/special_count.json", "wb+") as f:
                f.write(orjson.dumps(special, option=orjson.OPT_INDENT_2))

            refresh_capture_gift = True
            refresh_card()

    def reset():
        def double_check():
            global refresh_capture_gift
            with open("data/gifts_count.json", "wb+") as f:
                f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))
            with open("data/special_count.json", "wb+") as f:
                f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))
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
        with open("data/gifts_count.json", "rb+") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/special_count.json", "rb+") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        if gift_name.value in gifts:
            gifts.pop(gift_name.value)
        if gift_name.value in special:
            special.pop(gift_name.value)

        gifts = sort_dict(dictionary=gifts, sort_within_type=True)  # 对礼物数据进行排序

        with open("data/gifts_count.json", "wb+") as f:
            f.write(orjson.dumps(gifts, option=orjson.OPT_INDENT_2))
        with open("data/special_count.json", "wb+") as f:
            f.write(orjson.dumps(special, option=orjson.OPT_INDENT_2))

        refresh_capture_gift = True # 设置capture刷新状态
        refresh_card()

    def del_gift(is_special, k):
        global refresh_capture_gift
        with open("data/gifts_count.json", "rb") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/special_count.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        if is_special:
            special.pop(k)
            with open("data/special_count.json", "wb+") as f:
                f.write(orjson.dumps(special, option=orjson.OPT_INDENT_2))
        else:
            gifts.pop(k)
            with open("data/gifts_count.json", "wb+") as f:
                f.write(orjson.dumps(gifts, option=orjson.OPT_INDENT_2))

        refresh_capture_gift = True
        refresh_card()

    def create_card():
        with open("data/gifts_count.json", "rb") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/special_count.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        if gifts != {}:
            for k,v in gifts.items():
                with ui.row().classes('w-full'):
                    ui.label(k)
                    ui.space()
                    if v < 0:
                        ui.label(f"{int(v)}{app.storage.general["gift_challenge_unit"]}")
                    elif v > 0:
                        ui.label(f"+{int(v)}{app.storage.general["gift_challenge_unit"]}")
                    ui.button("删除", on_click=lambda k = k: del_gift(False, k))

        if special != {}:
            for k,v in special.items():
                if type(v) == list:
                    with ui.row().classes('w-full'):
                        ui.label(k)
                        ui.space()
                        if v[1] < 0:
                            ui.label(f"{int(v[0])} ~ {int(v[1])}{app.storage.general["gift_challenge_unit"]}")
                        elif v[0] < 0 and v[1] != 0:
                            ui.label(f"{int(v[0])} ~ +{v[1]}{app.storage.general["gift_challenge_unit"]}")
                        elif v[0] < 0 and v[1] == 0:
                            ui.label(f"{int(v[0])} ~ {v[1]}{app.storage.general["gift_challenge_unit"]}")
                        elif v[0] == 0 and v[1] == 0:
                            ui.label(f"{v[0]} ~ {v[1]}{app.storage.general["gift_challenge_unit"]}")
                        elif v[0] == 0 and v[1] != 0:
                            ui.label(f"{v[0]} ~ +{v[1]}{app.storage.general["gift_challenge_unit"]}")
                        else:
                            ui.label(f"+{v[0]} ~ +{v[1]}{app.storage.general["gift_challenge_unit"]}")
                        ui.button("删除", on_click=lambda k = k: del_gift(True, k))
                else:
                    with ui.row().classes('w-full'):
                        ui.label(k)
                        ui.space()
                        if v == "clear":
                            v = "清空"
                        if v == "double":
                            v = "加倍"
                        if v == "half":
                            v = "减半"
                        ui.label(v)
                        ui.button("删除", on_click=lambda k = k: del_gift(True, k))

    def refresh_card():
        gift_card.clear()  # 清空卡片内容
        with gift_card:
            create_card()

    with ui.dialog() as gift_count_dialog, ui.card(align_items="center"):
        with open("data/gift_img.json", "rb") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        ui.label("设置预览").classes("text-2xl text-blue").style("font-size: 20px")

        with ui.card().classes("w-full") as gift_card:
            create_card()

        ui.separator()

        with ui.row(align_items="center"):
            gift_name = ui.select(label="礼物选择", options=list(gifts.keys()), with_input=True, clearable=True).style("width: 200px")

        status = ui.toggle(options={"add": "加", "sub": "减", "double": "加倍", "half": "减半", "clear": "清空", "random": "随机"}, on_change=lambda: show()).classes('items-center')
        with ui.row():
            min = ui.number("随机最小数", value=0)
            max = ui.number("随机最大数", value=0)
            number = ui.number(label="数量", value=0, min=0).style("width: 150px")

            # 自定义单位、项目输入框
            if app.storage.general["gift_challenge_unit"] != "":
                gift_play_unit = ui.input("单位").bind_value(app.storage.general, "gift_challenge_unit")
            else:
                gift_play_unit = ui.input("单位").bind_value(app.storage.general, "gift_challenge_unit")
            if app.storage.general["gift_challenge_text"] != "":
                gift_play_text = ui.input("项目").bind_value(app.storage.general, "gift_challenge_text")
            else:
                gift_play_text = ui.input("项目").bind_value(app.storage.general, "gift_challenge_text")

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


def init_task():
    global countdown_timer
    global reset_inherit_status
    countdown_timer = CountdownTimer()
    if app.storage.general.get("countdown_time", 0) != 0: # 如果存在可继承的倒计时
        cancel_button.set_text("重置")
        cancel_button.enable()
        reset_inherit_status = True # 设置重置继承倒计时状态为True


# 运行倒计时
def start_task():
    if app.storage.general.get("countdown_time", 0) == 0:
        base_seconds = (input_hour.value * 3600) + (input_minute.value * 60) + input_second.value
    else:
        base_seconds = app.storage.general["countdown_time"]

    countdown_timer.set_remaining_seconds(base_seconds)
    countdown_timer.start()


# 手动加时
def add_time():
    try:
        if input_hour.value or input_minute.value or input_second.value:
            delta = (input_hour.value * 3600) + (input_minute.value * 60) + input_second.value
            new_seconds = countdown_timer.remaining_seconds + delta
            countdown_timer.set_remaining_seconds(new_seconds)
    except NameError:
        ui.notify("请先开始计时", type="negative")


# 手动减时
def sub_time():
    try:
        if input_hour.value or input_minute.value or input_second.value:
            delta = (input_hour.value * 3600) + (input_minute.value * 60) + input_second.value
            new_seconds = countdown_timer.remaining_seconds - delta
            countdown_timer.set_remaining_seconds(new_seconds)
    except NameError:
        ui.notify("请先开始计时", type="negative")


async def upload_log(room_id):
    '''
    发送日志到服务器
    '''

    file_path = log.file_name
    url = base_config.get("api", "server", None)

    if url is None or url == "":
        result = "未配置服务器地址，上传日志失败"
        ui.notify(result, type="negative")
        logger.error(result)
        return

    # 验证文件是否存在
    if not os.path.exists(file_path):
        result = f"文件不存在: {file_path}"
        ui.notify(result, type="negative")
        logger.error(result)
        return

    url = f"{url}/log/{room_id}"

    try:
        data = aiohttp.FormData()

        file_obj = open(file_path, "rb")

        data.add_field(
            name="file", # 参数名必须与FastAPI接口一致
            value=file_obj,
            filename=os.path.basename(file_path),
            content_type="application/octet-stream"
        )

        timeout = aiohttp.ClientTimeout(total=60)  # 60秒超时

        async with aiohttp.ClientSession(timeout=timeout, connector=await dns_resolver.connector()) as session:
            async with session.post(url, data=data) as response:
                if response.status == 201:
                    result = await response.json()
                    ui.notify(f"日志上传成功，状态码：{result.get("status", None)}", type="positive")
                    logger.info(f"日志上传成功：{result}")
                else:
                    error = await response.text()
                    result = f"日志上传失败，状态码: {response.status}"
                    ui.notify(result, type="negative")
                    logger.error(f"{result}")
                    logger.error(f"服务器返回错误: {error}")

    except aiohttp.ClientError as e:
        result = "日志上传失败，发生网络错误: "
        ui.notify(result + str(e), type="negative")
        logger.error(result + traceback.format_exc())

    except Exception as e:
        result = "日志上传失败，发生错误: "
        ui.notify(result + str(e), type="negative")
        logger.error(result + traceback.format_exc())

    finally:
        file_obj = locals().get("file_obj")
        if file_obj is not None and not file_obj.closed:
            file_obj.close()


async def check_b_connect_status():
    global b_connect_status
    switch_value = b_connect_switch.value

    def disconnect_timer():
        if b_connect_switch.value == "null":
            ui.notify("连接超时，请检查日志", type="negative")
            b_connect_switch.set_value(False)

    # 开关关闭状态：断开连接
    if switch_value is False:
        # 无身份码且未连接
        if auth_code.value == "" and not b_connect_status:
            b_connect_switch.set_value(False)
            return

        # 断开连接
        start_button.disable()
        gift_challenge_switch.disable()
        b_connect_status = False

        if "client" in globals() and client is not None:
            client.stop() # 断开弹幕服务器ws连接
            logger.info("弹幕服务器ws连接已断开")
        else:
            logger.warning("弹幕服务器ws连接未建立，跳过断开")

        ui.notify("已断开连接")
        b_connect_switch.set_value(False)
        b_connect_switch.set_text("连接至弹幕服务器")
        login_status.set_text("未连接")
        login_status.classes(replace="text-red")

    # 开关为"null"状态：尝试连接
    if switch_value == "null":
        # 检查身份码
        if not auth_code.value:
            ui.notify("未填入身份码，无法连接弹幕服务器", type="negative")
            b_connect_switch.set_value(False)
            return

        # 启动连接
        if not b_connect_status:
            asyncio.create_task(start_handler())
            ui.timer(60, lambda: disconnect_timer(), once=True) # 如果超时仍未连接强制断开
            b_connect_switch.set_value("null")
            b_connect_switch.set_text("尝试连接弹幕服务器")
            login_status.set_text("未连接")
            login_status.classes(replace="text-red")
        else:
            b_connect_switch.set_value(True)

    # 开关打开状态：已连接
    if switch_value is True:
        if not auth_code.value:
            ui.notify("请输入身份码", type="negative")
            b_connect_switch.set_value(False)
            return

        if b_connect_status:
            start_button.enable()
            gift_challenge_switch.enable()
        else:
            b_connect_switch.set_value("null")


async def get_notes():
    '''
    获取公告信息
    '''
    async def fetch_notes() -> list:
        url = base_config.get("api", "server", None)

        if url is None or url == "":
            result = "未配置服务器地址，获取公告失败"
            logger.error(result)
            return []

        url = f"{url}/notes"

        try:
            timeout = aiohttp.ClientTimeout(total=10)  # 10秒超时

            async with aiohttp.ClientSession(timeout=timeout, connector=await dns_resolver.connector()) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("data", [])
                    else:
                        error = await response.text()
                        result = f"获取公告失败:{error}，状态码: {response.status}"
                        logger.error(result)
                        return []

        except aiohttp.ClientError as e:
            result = f"获取公告失败，发生网络错误: {e}"
            logger.error(result + "\n" + traceback.format_exc())
            return []

        except Exception as e:
            result = f"获取公告失败，发生错误: {e}"
            logger.error(result + "\n" + traceback.format_exc())
            return []

    async def random_notes():
        result = await fetch_notes()
        local_notes = result.copy()
        with open("data/gifts.json", "rb") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        for note in local_notes:
            for i in GiftManager.custom_gifts:
                if i in note:
                    local_notes.pop(local_notes.index(note))
                if i in gifts:
                    local_notes.append(
                        f'赠送{i}可触发{app.storage.general["custom_gift_rate"].get(i, None)}倍暴击！'
                    )

        if local_notes: # 如果公告列表不为空
            # 过滤掉所有空字符串占位符
            local_notes = [n for n in local_notes if n]
            if local_notes:
                note = random.choice(local_notes)
                notes_label.set_text(f"Tips: {note}")

    notes_label = (
        ui.label()
        .classes("text-2xl font-extrabold")
        .style(f"color: {config['color']['text_color']}")  # pyright: ignore[reportIndexIssue]
    )
    app.timer(5, random_notes)  # 每5秒随机切换公告内容


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


async def refresh_gift_loop():
    if auth_code.value == "" or b_connect_status is False:
        logger.warning("身份码为空或未连接弹幕服务器，跳过礼物更新")
        return

    gift_config = await GiftManager.get_config("data/gift_img.json")
    await create_blind_box()

    if gift_config:
        result = "礼物数据定时更新完成"
        with main_card:
            ui.notify(result, type="positive")
        logger.info(result)
    elif gift_config == "blind_box_none":
        logger.warning("未登录账号，无法定时更新盲盒礼物，将使用默认数据...")
    else:
        result = f"定时更新礼物数据失败: gift_config return {gift_config}"
        with main_card:
            ui.notify(result, type="negative")
        logger.error(result)


# 更新礼物数据
async def refresh_gift(heartbeat=False):
    async def check_refresh():
        if auth_code.value == "":
            ui.notify("请输入身份码", type="negative")
            return

        if not heartbeat:
            check_dialog.close()

        ui.notify("正在更新礼物数据，请稍后...", type="info")

        await asyncio.sleep(1)

        try:
            gift_config = await GiftManager.get_config("data/gift_img.json")
            await create_blind_box()
        except Exception as e:
            logger.error(f"更新礼物数据时发生错误: {e}")
            raise

        if gift_config is True:
            ui.notify("礼物数据更新完成", type="positive")
        # 如果本地礼物配置数据不存在，则直接初始化
        elif gift_config is None:
            ui.notify("未检测到本地礼物数据，将初始化礼物数据...", type="info")
            await init_config()
            ui.notify("礼物数据初始化完成", type="positive")
        # 如果更新盲盒礼物出错
        elif gift_config == "blind_box_none":
            ui.notify("未登录账号，无法更新盲盒礼物，将使用默认数据...", type="negative")
            await asyncio.sleep(2)
            ui.notify("礼物数据更新完成", type="positive")
        # 如果礼物数据更新失败，则使用本地数据重置
        else:
            ui.notify("礼物数据更新失败，请检查日志或稍后重试，或者使用本地数据重置", type="negative")

    async def reset_local_gift():
        # 重置本地数据
        try:
            await GiftManager.init_gift("data/gift_img.json")
            ui.notify("重置成功", type="positive")
        except Exception as e:
            logger.error(f"使用本地数据重置失败：{e}")
            ui.notify("重置失败", type="negative")

    if heartbeat:
        await check_refresh()
        return

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
async def capture():  # pyright: ignore[reportRedeclaration]
    global capture_cd_gift_list_show, capture_cd_rank_list_show, capture_cd_is_created

    styles.page_styles() # 加载自定义样式
    # 检查是否需要刷新页面
    def check_cd_refresh():
        global refresh_capture_cd

        if not base_config.get("bool", "show_capture_gift_list", False):
            if scroll_card.visible:
                scroll_card.set_visibility(False)
        else:
            scroll_card.set_visibility(True)

        if refresh_capture_cd:
            refresh_capture_cd = False
            # ui.run_javascript(f'window.location.href += "?{refresh_time}";')
            ui.navigate.reload()

    def change_gift_element(v_type, k, v):
        '''
        修改礼物列表UI元素
        
        :param v_type: 礼物类型：加减时为normal，随机为list，其它为special
        :param k: 礼物名称
        :param v: 设定礼物的值
        '''

        with open("data/gift_img.json", "rb") as f:
            gift_img = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        if v_type == "normal":
            gift_img_avatar.set_source(gift_img.get(k, ""))
            k_label.set_text(k)
            if k in GiftManager.custom_gifts:
                v_label.set_text(f"{format_seconds(v)} 暴击{format_seconds(v * abs(1 - app.storage.general['custom_gift_rate'][k]) + v)}")
            else:
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
        '''
        将礼物列表处理为简洁模式
        '''
        with open("data/gifts.json", "rb") as f:
            gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        with open("data/special.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        gifts.update(special) # 合并加减时和特殊玩法
        gifts = sort_dict(dictionary=gifts, sort_within_type=True) # 对字典按值的类型排序
        k = next(iter(gifts)) # 字典第一个礼物名称
        v = gifts[k] # 字典第一个礼物的值
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

        # 如果不将timer封装到函数中，在OBS的浏览器源中刷新页面后计时器会失效
        def timer_handler() -> ui.timer:
            timer = ui.timer(base_config.get("num", "short_time", 5), lambda: change(cycle_items))  # pyright: ignore[reportArgumentType]
            return timer

        timer_handler()
        app.on_disconnect(lambda: timer_handler().cancel())

    def gift_element(v_type, k, v):
        global gift_img_avatar, k_label, v_label

        if v_type == "normal":
            with ui.row().classes('w-full'):
                with ui.avatar(color=None):
                    gift_img_avatar = ui.image(gift_img.get(k, ""))
                k_label = ui.label(k).classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                ui.space()
                if k in GiftManager.custom_gifts:
                    v_label = ui.label(f"{format_seconds(v)} 暴击{format_seconds(v * abs(1 - app.storage.general['custom_gift_rate'][k]) + v)}").classes("text-3xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                else:
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
        if auth_code.value != None:
            await init_config()

    with open("data/gifts.json", "rb") as f:
        gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

    with open("data/gift_img.json", "rb") as f:
        gift_img = orjson.loads(f.read().decode("utf-8").encode("utf-8"))


    if os.path.exists("data/special.json"):
        with open("data/special.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
    else:
        special = {}
    # ui.query('body').style(f'background: url("{random.choice(config["general"]["background_image"])}") 0px 0px/cover')

    # 创建预览界面
    with ui.card(align_items="center").classes("bg-transparent").style("box-shadow: None; left: 50%; transform: translate(-50%, 0%);"): # 居中、背景透明、取消卡片阴影、置顶居中
        if not config['bool']['borderless_cd']:  # type: ignore[index]
            ui.badge(outline=True, color="", text_color=config['color']['time_color']).bind_text_from(app.storage.general, "countdown_time", lambda x: format_cd(x)).classes("text-8xl")  # type: ignore[arg-type]
        else:
            ui.label().bind_text_from(app.storage.general, "countdown_time", lambda x: format_cd(x)).classes("text-8xl").style(f"color: {config['color']['time_color']}")  # type: ignore[index]

        ui.separator() # 分割线

        await get_notes() # 获取公告信息

        # 创建礼物列表
        if not base_config.get("bool", "short_list", False):
            if gifts != {}:
                gifts = sort_dict(dictionary=gifts, sort_within_type=True)
                for k,v in gifts.items():
                    gift_element("normal", k, v)

            if special != {}:
                special = sort_dict(dictionary=special, type_order=[str, list], sort_within_type=True)
                for k,v in special.items():
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
                    if re.search(r"-2\^(\d+)倍", time):
                        time = format_seconds(float(f"-{app.storage.general['countdown_time'] / 2}"))
                    else:
                        time = f"{format_seconds(app.storage.general['countdown_time'])}"

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
                            ui.label(gift_rule).classes("text-xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]

                capture_gift_scroll.scroll_to(percent=1, duration=0.5)
                capture_cd_rank_list_show() # 每次有新礼物时更新排行榜

        def capture_cd_rank_list_show():
            def rule_to_seconds(rule):
                """将规则字符串转换为秒数，处理小时、分钟、秒，并跳过包含'倍'的规则"""

                # 首先检查输入是否为字符串，如果不是则返回None
                if not isinstance(rule, str):
                    return None
                rule = rule.strip() # 去除字符串首尾的空白字符

                # 提取符号
                sign = 1
                if rule.startswith('-'):
                    sign = -1
                    rule = rule[1:]  # 移除负号
                elif rule.startswith('+'):
                    rule = rule[1:]  # 移除正号

                # 初始化时间单位
                hours = 0
                minutes = 0
                seconds = 0

                # 使用正则表达式匹配小时、分钟、秒
                # 匹配小时（支持"小时"或"时"）
                hour_match = re.search(r'(\d+)(?:小时|时)', rule)
                if hour_match:
                    hours = int(hour_match.group(1))
                    rule = rule.replace(hour_match.group(0), '')  # 移除已匹配部分

                # 匹配分钟
                minute_match = re.search(r'(\d+)分', rule)
                if minute_match:
                    minutes = int(minute_match.group(1))
                    rule = rule.replace(minute_match.group(0), '')  # 移除已匹配部分

                # 匹配秒
                second_match = re.search(r'(\d+)秒', rule)
                if second_match:
                    seconds = int(second_match.group(1))
                    rule = rule.replace(second_match.group(0), '')  # 移除已匹配部分

                # 如果规则字符串中只有数字（可能是单独的秒数，如"+30"表示30秒）
                remaining = rule.strip()
                if remaining.isdigit():
                    seconds += int(remaining)

                # 计算总秒数
                total_seconds = hours * 3600 + minutes * 60 + seconds

                return sign * total_seconds

            if not base_config.get("bool", "show_capture_rank_list", False):
                rank_card.set_visibility(False)
            else:
                rank_card.set_visibility(True)
                capture_rank_scroll.clear()

            # 如果礼物历史数据不存在，直接返回
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
                        ui.icon("emoji_events",size="30px", color=trophy_color[0])
                        trophy_color.pop(0)
                        ui.label(f"{name}").classes("text-xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
                        ui.space()
                        ui.label(format_seconds(seconds)).classes("text-xl font-extrabold").style(f"color: {config['color']['text_color']}")  # type: ignore[index]

            capture_rank_scroll.scroll_to(percent=1, duration=0.5)

        with ui.card(align_items="stretch").classes("bg-transparent w-full").style("box-shadow: None;") as rank_card:
            with ui.scroll_area().classes('h-40 w-full') as capture_rank_scroll:
                ui.label().set_visibility(False)

        capture_cd_rank_list_show()

        with ui.card(align_items="stretch").classes("bg-transparent w-full").style("box-shadow: None;") as scroll_card:
            with ui.scroll_area().classes('h-32 w-full') as capture_gift_scroll:
                ui.label().set_visibility(False)

    ui.timer(5, callback=lambda: check_cd_refresh())

# 投喂挑战预览
@ui.page("/capture_gift", title="投喂挑战 | bili_travail")
async def capture():
    global capture_challenge_gift_list_show, capture_gift_is_created
    styles.page_styles() # 加载自定义样式
    def check_gift_refresh():
        global refresh_capture_gift

        if not base_config.get("bool", "show_capture_gift_list", False):
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
        if not auth_code.value is None:
            await init_config()

    with open("data/gifts_count.json", "rb") as f:
        gifts = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

    with open("data/gift_img.json", "rb") as f:
        gift_img = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

    if os.path.exists("data/special_count.json"):
        with open("data/special_count.json", "rb") as f:
            special = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
    else:
        special = {}
    # ui.query('body').style(f'background: url("{random.choice(config["background_image"])}") 0px 0px/cover')
    with ui.card(align_items="center").classes("bg-transparent").style("box-shadow: None; left: 50%; transform: translate(-50%, 0%);"):
        with ui.row():
            ui.label("总计").classes("text-4xl").style(f"color: {config['color']['text_color']}").classes("text-5xl")  # type: ignore[index]
            ui.label().bind_text_from(app.storage.general, "gift_challenge_count").style(f"color: {config['color']['text_color']}").classes("text-5xl")  # type: ignore[index]
            ui.label().bind_text_from(app.storage.general, "gift_challenge_unit").style(f"color: {config['color']['text_color']}").classes("text-5xl")  # type: ignore[index]
            ui.label().bind_text_from(app.storage.general, "gift_challenge_text").style(f"color: {config['color']['text_color']}").classes("text-5xl")  # type: ignore[index]

        ui.separator()

        await get_notes() # 获取公告信息

        if gifts != {}:
            for k,v in gifts.items():
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
            for k,v in special.items():
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

@ui.page("/")
def index():
    # ================================
    # 主界面GUI
    # ================================

    global show_capture_gift_list_switch, auth_code, main_card, start_button, b_connect_switch, gift_challenge_switch, cancel_button, input_hour, input_minute, input_second, login_status, start_button, pause_button, resume_button, add_button, sub_button, short_switch, custom_gift_rate

    styles.page_styles() # 加载自定义样式
    async def ping_server(servers):
        server = await ping.ping(servers.values())
        if server:
            server_name = {v: k for k, v in servers.items()}.get(server, server)
            return server_name
        else:
            return False

    def get_version():
        logs = get_log()
        version_flag = False
        num = 0

        if logs != {}:
            for i in logs.keys():
                if not version_flag:
                    num += 1
                if i == version:
                    version_flag = True
            return dict(islice(logs.items(), num - 1))
        else:
            return {}

    # 检查版本更新按钮
    async def check_update():
        def get_source():
            try:
                response = requests.get("http://version.nya-wsl.cn/bili_travail/source.json", timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    return data
                else:
                    ui.notify("获取更新源失败，尝试自动检测可用更新源", type="negative")
                    logger.error(f"获取更新源失败，状态码: {response.status_code}")
                    data = {"auto": "自动检测"}

            except Exception as e:
                logger.error(e)
                data = {"auto": "自动检测"}

            return data

        async def update(source: dict, server: str):
            if server == "auto":
                ui.notify(f"测速中，请稍候...", progress=True, timeout=3000, type="ongoing", color="blue-100")
                source_copy = deepcopy(source)
                urls = source_copy.get("url", {})
                if urls != {}:
                    for k, v in urls.items():
                        urls[k] = v.replace("https://", "").replace("http://", "").split("/")[0]
                    server = await ping_server(urls)  # pyright: ignore[reportAssignmentType]

                    if server is False:
                        ui.notify("无法连接更新服务器", type="negative")
                        return
                else:
                    server = ""

            if not server:
                logger.error("更新源为空")
                ui.notify("更新源为空，将尝试从Github获取更新", type="negative")
                server = "https://github.com/Nya-WSL/bili_travail/releases/download/update/update.zip"

            elif server in ["CN-QN"]:
                server = f'{source.get("url", {}).get(server)}/{status}.zip'

            elif server == "hi168_v2":
                url = f'{base_config.get("api", "server", None)}/update'
                try:
                    timeout = aiohttp.ClientTimeout(total=10)  # 10秒超时

                    params = {
                        "version": status,
                        "type": "zip"
                    }

                    async with aiohttp.ClientSession(timeout=timeout, connector=await dns_resolver.connector()) as session:
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                result = await response.json()
                                server = result.get("url", None)
                                if server is None:
                                    result = f"获取直链失败: {result.get('message', '未知错误')}"
                                    logger.error(result)
                                    ui.notify(result, type="negative")
                                    return
                            else:
                                error = await response.text()
                                result = f"获取直链失败:{error}，状态码: {response.status}"
                                logger.error(result)
                                ui.notify(result, type="negative")
                                return

                except aiohttp.ClientError as e:
                    result = f"获取直链失败，发生网络错误: {e}"
                    logger.error(result + "\n" + traceback.format_exc())
                    ui.notify(result, type="negative")
                    return

                except Exception as e:
                    result = f"获取直链失败，发生错误: {e}"
                    logger.error(result + "\n" + traceback.format_exc())
                    ui.notify(result, type="negative")
                    return

            else:
                server = source.get("url", {}).get(server)

            await travail_update.update(server, status) # 调用更新函数

        def version_dialog():
            with ui.dialog() as dialog, ui.card(align_items="center"):
                ui.label(f"当前版本：{version} | 最新版本：{status}")
                source = get_source()
                # server_select = ui.select(options={"auto": "自动检测", "hi168": "国内首选", "CN-HK": "国内备用", "CN-QN": "国内CDN", "GitHub": "GitHub"}, label="选择更新源", value="auto").classes("w-1/2")
                server_select = ui.select(options=source.get("source", {"auto": "自动检测"}), label="选择更新源", value="auto").classes("w-1/2")  # pyright: ignore[reportArgumentType]
                ui.button("更新", on_click=lambda: update(source, server_select.value))  # pyright: ignore[reportArgumentType]
                for k,v in get_version().items():
                    with ui.timeline(side="right", layout="dense", color="btn"):
                        with ui.timeline_entry(title=f"Release of {k}", subtitle=v["date"]):
                            with ui.column().classes("gap-3"):
                                for item in v["content"]:
                                    ui.label(f"● {item}")

            dialog.open()

        def version_check():
            url = ["http://version.nya-wsl.cn/bili_travail/version.json", "https://nya-wsl.com/bili_travail/version.json"]
            try:
                response = requests.get(url[0], timeout=30) # 优先从Nya-WSL中国服务器获取版本信息
                if response.status_code == 200:
                    data = response.json()
                    latest_version = data["version"]
                else:
                    raise ValueError("From Nya-WSL CN to get version info was error") # 抛出错误
            except Exception as e:
                logger.error(e)
                try:
                    response = requests.get(url[1], timeout=30) # 从Nya-WSL海外服务器获取版本信息
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
                with main_card:
                    version_dialog()
            else:
                with main_card:
                    ui.notify("检查更新失败", type="negative")
        else:
            with main_card:
                ui.notify("已是最新版本", type="positive")

    def save_time():
        def do_save(key):
            with open("data/time.json", "rb") as f:
                data = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
            data[key] = app.storage.general["countdown_time"]
            with open("data/time.json", "wb+") as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
            ui.notify("保存成功", type="positive")

        def save(key):
            if key is None or key == "":
                ui.notify("名称不能为空", type="negative")
                return
            with open("data/time.json", "rb") as f:
                data = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
            if data.get(key, None) != None:
                with ui.dialog() as overwrite_dialog, ui.card(align_items="center"):
                    ui.label("该名称已存在，是否覆盖？")
                    with ui.row():
                        ui.button("是", on_click=lambda: do_save(key)).on_click(lambda: overwrite_dialog.close()).on_click(lambda: save_dialog.close())
                        ui.button("否", on_click=lambda: overwrite_dialog.close())
                overwrite_dialog.open()
                overwrite_dialog.on("hide", lambda: overwrite_dialog.delete())
            else:
                do_save(key)
                save_dialog.close()
                save_dialog.on("hide", lambda: save_dialog.delete())

        with ui.dialog() as save_dialog, ui.card(align_items="center"):
            name = ui.input("保存名称").style("width: 200px")
            ui.button("保存", on_click=lambda: save(name.value))

        save_dialog.open()
        save_dialog.on("hide", lambda: save_dialog.delete())

    def load_time():
        def load(key):
            with open("data/time.json", "rb") as f:
                data = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
            seconds = float(data[key])
            app.storage.general["countdown_time"] = seconds
            countdown_timer.set_remaining_seconds(seconds)
            load_dialog.close()
            ui.notify("加载成功", type="positive")

        def delete(key):
            with open("data/time.json", "rb") as f:
                data = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
            data.pop(key)
            with open("data/time.json", "wb+") as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
            ui.notify("删除成功", type="positive")

        def reload() -> dict:
            with open("data/time.json", "rb") as f:
                data = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
            return data

        with open("data/time.json", "rb") as f:
            data = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        with ui.dialog() as load_dialog, ui.card(align_items="center"):
            name_select = ui.select(options=list(data.keys()), label="选择名称").style("width: 200px")
            with ui.row():
                ui.button("加载", on_click=lambda: load(name_select.value))
                ui.button("删除", on_click=lambda: delete(name_select.value)).on_click(lambda: name_select.set_options(list(reload().keys())))

        load_dialog.open()
        load_dialog.on("hide", lambda: load_dialog.delete())

    # 礼物设置弹窗
    def gift_setting_dialog() -> ui.dialog:
        with ui.dialog() as gift_setting_dialog, ui.card(align_items="center"):
            ui.label("自定义礼物暴击倍率")
            for custom_gift in GiftManager.custom_gifts:
                ui.number(custom_gift, min=1, step=0.01, value=1.5).style("width: 150px").bind_value(app.storage.general["custom_gift_rate"], custom_gift)

            ui.separator()

            with ui.row():
                with ui.switch("礼物列表简洁模式", value=False, on_change=lambda: base_config.save(config)).bind_value(config["bool"], "short_list").props('color="btn"') as short_switch:
                    ui.tooltip("存在bug，暂时禁用")
                short_switch.on_value_change(lambda e: short_time.set_visibility(True) if e.value else short_time.set_visibility(False))
                short_switch.set_value(False)
                short_switch.disable()
                short_time = ui.number("滚动间隔", min=0, on_change=lambda: base_config.save(config)).bind_value(config["num"], "short_time")
                if short_switch.value:
                    short_time.set_visibility(True)
                else:
                    short_time.set_visibility(False)
            with ui.row():
                ui.button("加班设置", on_click=lambda: cd_setting_dialog())
                ui.button("挑战设置", on_click=lambda: gift_count_setting_dialog())
                ui.button("更新礼物", on_click=lambda: refresh_gift())
            ui.button("关闭", on_click=lambda: gift_setting_dialog.close())

        return gift_setting_dialog

    def changelog_dialog() -> ui.dialog:
        with ui.dialog() as changelog_dialog, ui.card(align_items="center"):
            changelog()

        return changelog_dialog

    # 统计相关弹窗
    with ui.dialog() as gift_count_dialog, ui.card(align_items="center"):
        with ui.row():
            ui.button("盲盒盈亏", on_click=lambda: blind_box_value_dialog())
            ui.button("礼物统计", on_click=lambda: ui.navigate.to("/count", True))
        ui.button("关闭", on_click=lambda: gift_count_dialog.close())

    with ui.dialog() as color_dialog, ui.card(align_items="center"):
        # 颜色输入框
        with ui.row():
            ui.color_input(label="预览颜色", value="#5a85ad", on_change=lambda: base_config.save(config), preview=config["color"]["time_color"]).style(f"width: 120px").bind_value(config["color"], "time_color")  # pyright: ignore[reportIndexIssue, reportArgumentType]
            ui.color_input(label="按钮颜色", value="#eddad2", on_change=lambda: base_config.save(config), preview=config["color"]["btn_color"]).style(f"width: 120px").bind_value(config["color"], "btn_color")  # pyright: ignore[reportIndexIssue, reportArgumentType]
            ui.color_input(label="文字颜色", value="#000000", on_change=lambda: base_config.save(config), preview=config["color"]["text_color"]).style(f"width: 120px").bind_value(config["color"], "text_color")  # pyright: ignore[reportIndexIssue, reportArgumentType]
        ui.button("关闭", on_click=lambda: color_dialog.close())


    if app.storage.general["version"] != version: # 如果版本号不一致
        app.storage.general["version"] = version # 更新版本号
        changelog_dialog().open() # 打开更新日志弹窗

    # 创建主界面
    with ui.card(align_items="center").classes("absolute-center").style("width: 95%") as main_card:
        asyncio.create_task(check_update())
        time_badge = ui.badge("00:00:00", outline=True, color="").bind_text_from(app.storage.general, "countdown_time", lambda x: format_cd(x)).classes("text-9xl").style(f"color: {btn_color}") # 创建时钟

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
            cancel_button = ui.button('停止', on_click=lambda: countdown_timer.stop())
            cancel_button.disable()

        with ui.row():
            # Add time Button
            add_button = ui.button("增加", on_click=lambda: add_time())
            add_button.disable()

            # Sub Time Button
            sub_button = ui.button("减少", on_click=lambda: sub_time())
            sub_button.disable()

            save_button = ui.button("保存", on_click=lambda: save_time())
            load_button = ui.button("读取", on_click=lambda: load_time())

        ui.separator()

        with ui.row(align_items="center"):
            with ui.column(align_items="center").classes("gap-0"):
                # 身份码
                auth_code = ui.input("身份码", on_change=lambda: base_config.save(config), password=True, password_toggle_button=True).style("width: 120px")
                auth_code.bind_value(config["general"], "auth_code") # 实时写入身份码到配置文件
                with ui.row().classes("gap-0"):
                    ui.label("房间号：")
                    login_status = ui.label("未连接").classes("text-red")
                b_connect_switch = ui.switch("连接至弹幕服务器", on_change=lambda: check_b_connect_status()).props('checked-icon="check" color="green" unchecked-icon="clear"')

            with ui.column(align_items="center").classes("gap-0"):
                show_capture_rank_list_switch = ui.switch("OBS显示排行榜", value=False, on_change=lambda: base_config.save(config))
                show_capture_rank_list_switch.bind_value(config["bool"], "show_capture_rank_list").props('color="btn"')

                show_capture_gift_list_switch = ui.switch("OBS显示投喂记录", value=False, on_change=lambda: base_config.save(config))
                show_capture_gift_list_switch.bind_value(config["bool"], "show_capture_gift_list").props('color="btn"')

                with ui.switch("倒计时结束后退出程序", value=True, on_change=lambda: base_config.save(config)) as exit_timer_switch:
                    ui.tooltip(f"倒计时结束{base_config.get('num', 'exit_time', 0)}秒后是否退出程序，该值可在 config.toml -> num -> exit_time 处修改")
                exit_timer_switch.bind_value(config["bool"], "exit_timer").props('color="btn"')

            with ui.column(align_items="center").classes("gap-0"):
                with ui.switch("忽略倒计时", value=False).bind_value(app.storage.general, "ignore_cd").props('color="btn"') as ignore_cd_switch:
                    ui.tooltip("启用时在倒计时结束后（包括暂停时）仍然会触发加减时")

                with ui.switch("无边框倒计时", value=False, on_change=lambda: base_config.save(config)).bind_value(config["bool"], "borderless_cd").props('color="btn"'):
                    ui.tooltip("启用时预览界面倒计时将不显示边框，仅显示数字")

                gift_challenge_switch = ui.switch("启用投喂挑战", value=False).props('color="btn"')
                gift_challenge_switch.disable()

        ui.separator()

        # 按钮组
        with ui.row():
            ui.button("礼物设置", on_click=lambda: gift_setting_dialog().open())
            ui.button("颜色设置", on_click=lambda: color_dialog.open())
            ui.button("统计相关", on_click=lambda: gift_count_dialog.open())
            # Preview page button
            ui.button("界面预览", on_click=lambda: open_capture())

        with ui.row():
            # Login bilibili button
            ui.button("登录账号", on_click=lambda: ui.navigate.to("https://play-live.bilibili.com", new_tab=True))
            # Update version button
            ui.button("检查更新", on_click=lambda: check_update())
            # Changelog button
            ui.button("更新日志", on_click=lambda: changelog_dialog().open())
            ui.button("上传日志", on_click=lambda: upload_log(base_config.get("general", "room_id", 3)))

        # obs源
        with ui.label(f"http://{host}:{port}/capture_cd").on("click", js_handler=f'() => navigator.clipboard.writeText("http://{host}:{port}/capture_cd")').on("click", lambda: ui.notify("已复制至剪贴板", type="info")):
            ui.tooltip("OBS倒计时浏览器源URL，单击可复制至剪贴板")
        with ui.label(f"http://{host}:{port}/capture_gift").on("click", js_handler=f'() => navigator.clipboard.writeText("http://{host}:{port}/capture_gift")').on("click", lambda: ui.notify("已复制至剪贴板", type="info")):
            ui.tooltip("OBS投喂挑战浏览器源URL，单击可复制至剪贴板")
        with ui.link("使用文档", "https://docs.travail.nya-wsl.com", True):
            ui.tooltip("点击查看使用说明书")

        init_task()

    # about按钮
    with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=15):
        ui.button(on_click=lambda: ui.navigate.to("/about", new_tab=True), icon='contact_support').props('fab')

@ui.page('/count')
def _():
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

# about页面
@ui.page('/about')
async def _():
    styles.page_styles() # 加载自定义样式
    config = base_config.load()
    ui.query('body').style(f'background: url("{random.choice(config["general"]["background_image"])}") 0px 0px/cover') # 设置背景图片  # pyright: ignore[reportIndexIssue, reportArgumentType]

    # Card框
    with ui.card(align_items="center").classes("absolute-center"):
        ui.label(f"B站加班姬").classes("text-3xl").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
        ui.badge(version, outline=True)

        # 私货
        def read_or_create_file(file_path, default_content):
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                with open(file_path, "w+", encoding="utf-8") as f:
                    f.write(default_content)
                return default_content

        # 配置头像URL常量
        AVATAR_A = "https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"
        AVATAR_B = "https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"
        NAME_A = "高橋はるき"
        NAME_B = "狐日泽"

        async def fetch_text(session, url):
            """异步获取文本内容"""
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    logger.warning(f"请求失败: {url} 状态码: {response.status}")
                    return None
            except asyncio.TimeoutError:
                logger.warning(f"请求超时: {url}")
            except aiohttp.ClientError as e:
                logger.error(f"网络错误: {url} - {e}")
            except Exception as e:
                logger.error(f"未知错误: {url} - {e}")
            return None

        async def get_remote_text(session):
            """尝试从多个源获取文本"""
            urls = [
                "https://nya-wsl.com/bili_travail/chat_msg.json",
                "http://version.nya-wsl.cn/bili_travail/chat_msg.json"
            ]

            for url in urls:
                text = await fetch_text(session, url)
                if text is not None:
                    return text
            return None

        async def display_chat_messages(config, bili_api):
            """异步获取并显示聊天消息"""
            try:
                async with aiohttp.ClientSession(connector=await dns_resolver.connector()) as session:
                    # 获取远程文本
                    text = await get_remote_text(session)

                    # 如果获取到文本
                    if text:
                        # 随机选择消息组
                        if random.random() < 0.3:
                            # 排除group_a的其他消息
                            msg_groups = [k for k in text.keys() if k != "group_a"]
                            selected_group = random.choice(msg_groups) if msg_groups else "group_a"
                        else:
                            selected_group = "group_a"

                        msg = text.get(selected_group)
                        if msg:
                            await display_message_pair(msg, bili_api)
                            return

                    # 使用本地文件作为回退
                    text_a = read_or_create_file("data/text_a.txt", "代码没写完，哪有脸睡觉")
                    text_b = read_or_create_file("data/text_b.txt", 'alias cd="sudo rm -rf"')
                    
                    # 显示本地消息
                    ui.chat_message(
                        text_a, 
                        avatar=bili_api.get_bili_img(AVATAR_A), 
                        name=NAME_A, 
                        text_html=True, 
                        sent=True, 
                        sanitize=False
                    )
                    ui.chat_message(
                        text_b, 
                        avatar=bili_api.get_bili_img(AVATAR_B), 
                        name=NAME_B, 
                        text_html=True, 
                        sanitize=False
                    )

            except Exception as e:
                logger.error(f"显示聊天消息失败: {e}")
                # 显示错误消息
                ui.notify("加载聊天消息失败，请稍后再试", type="negative")

        async def display_message_pair(msg, bili_api):
            """显示一对聊天消息"""
            avatar_a = bili_api.get_bili_img(AVATAR_A)
            avatar_b = bili_api.get_bili_img(AVATAR_B)
            
            ui.chat_message(
                msg.get("text_a", "默认消息A"), 
                avatar=avatar_a, 
                name=NAME_A, 
                text_html=True, 
                sent=True, 
                sanitize=False
            )
            ui.chat_message(
                msg.get("text_b", "默认消息B"), 
                avatar=avatar_b, 
                name=NAME_B, 
                text_html=True, 
                sanitize=False
            )

        if base_config.get("bool", "remote_text", True):
            await display_chat_messages(config, bili_api)

        # 项目介绍
        ui.html('A Project of <u><a href="https://nya-wsl.com" target="_blank">Nya-WSL</a></u>.', sanitize=False)
        ui.html('Powered by <u><a href="https://nicegui.io" target="_blank">NiceGUI</a></u> - <u><a href="https://github.com/xfgryujk/blivedm" target="_blank">blivedm</a></u>.', sanitize=False)
        ui.label("Copyright © 2025 - 2026. All rights reserved. ")
        ui.separator()

        # 成员显示
        with ui.row(align_items="center"):
            with ui.column(align_items="center"):
                ui.label("程序开发").classes("text-blue")
                with ui.row(align_items="center"):
                    with ui.column(align_items="center"):
                        with ui.link(target="https://space.bilibili.com/16748991", new_tab=True):
                            with ui.avatar():
                                ui.image(bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"))
                        ui.badge("高橋はるき", outline=True)
                    with ui.column(align_items="center"):
                        with ui.link(target="https://space.bilibili.com/8907402", new_tab=True):
                            with ui.avatar():
                                ui.image(bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"))
                        ui.badge("狐日泽", outline=True)
            ui.separator().props('vertical')
            with ui.column(align_items="center"): 
                ui.label("特别鸣谢").classes("text-blue")
                with ui.row(align_items="center"):
                    with ui.column(align_items="center"):
                        with ui.link(target="https://space.bilibili.com/3546729020394298/", new_tab=True):
                            with ui.avatar():
                                ui.image(bili_api.get_bili_img("https://i1.hdslb.com/bfs/face/1c90e9c3a52b13b898f4025a5282a394b09eeda0.jpg"))
                        ui.badge("千蚀vita", outline=True)
                    with ui.column(align_items="center"):
                        with ui.link(target="https://space.bilibili.com/15104516/", new_tab=True):
                            with ui.avatar():
                                ui.image(bili_api.get_bili_img("https://i1.hdslb.com/bfs/face/316685ff90898018d3bb0eb7f0649db73e109e9b.jpg"))
                        ui.badge("青岚千柊", outline=True)
                    with ui.column(align_items="center"):
                        with ui.link(target="https://space.bilibili.com/4015420/", new_tab=True):
                            with ui.avatar():
                                ui.image(bili_api.get_bili_img("https://i1.hdslb.com/bfs/face/29b2132e3371d0c9a90a21edf6a0ad87a122a831.jpg"))
                        ui.badge("天苍八重", outline=True)
                    with ui.column(align_items="center"):
                        with ui.link(target="https://space.bilibili.com/11236317/", new_tab=True):
                            with ui.avatar():
                                ui.image(bili_api.get_bili_img("https://i0.hdslb.com/bfs/face/7b2a5c03e0caaa516dda9e238a82ebeef0e2f56d.jpg"))
                        ui.badge("冰蓝IceBlue", outline=True)

        ui.separator()

        # 联系我们
        ui.label(f"联系我们").classes("text-2xl").style(f"color: {config['color']['text_color']}")  # type: ignore[index]
        ui.link("GitHub Issues", "https://github.com/Nya-WSL/bili_travail/issues", True)
        ui.link("support@nya-wsl.com", "mailto:support@nya-wsl.com", True)
        ui.link("Nya-WSL服务与反馈群", "https://jq.qq.com/?_wv=1027&k=tSeB0sdy", True)
        ui.separator()
        ui.link("使用文档", "https://docs.travail.nya-wsl.com", True)
        # ui.html('关注<u><a href="https://space.bilibili.com/3546729020394298" target="_blank">千蚀vita</a></u>谢谢喵', sanitize=False).classes("text-2xl text-white")

@app.on_startup
async def create_job():
    scheduler.add_job(refresh_gift_loop, trigger='cron', minute=0) # 每个整点更新一次礼物数据
    scheduler.start()

@app.on_shutdown
async def shutdown():
    await client.stop_and_close()
    logger.info('ws connect shut down')
    scheduler.shutdown()

# 运行NiceGUI
if __name__ == "__main__":
    try:
        freeze_support()
        logger.info("正在检查Edge WebView2 runtime...")
        asyncio.run(check_runtime.check_runtime()) # 检查Edge WebView2 runtime

        ui.run(host=host, port=port, title=f"bili_travail | {version}", favicon="static/logo.ico", reload=False, show=False, native=True, window_size=(600, 780), reconnect_timeout=30, language="zh-CN", use_colors=False)  # pyright: ignore[reportArgumentType]
    except Exception:
        logger.error(f"run error: {traceback.format_exc()}")
