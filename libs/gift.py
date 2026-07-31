import os
import sys
import orjson
import asyncio
import aiohttp
import traceback

from .log import logger
from . import dns_resolver
from . import gift_mapping as gift_map
from . import config as travail_config

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) # 将上级目录加入路径，以便导入版本号

import env
import version as base_ver

base_config = travail_config.Config()

class BiliGiftManager:
    def __init__(self):
        room_id = base_config.get("general", "room_id", "")
        self.room_id = room_id if room_id else 3

        self.area_parent_id = 0
        self.area_id = 0
        self.custom_gifts = []
        self.wait_num = 0

    async def init_gift(self, img_path):
        """
        从服务器或本地预置数据初始化礼物
        
        :param img_path: 礼物数据字典保存路径
        :param time_path: 礼物时长字典保存路径
        :param time: 礼物时长
        """

        url = "https://travail.nya-wsl.com/bili_travail/gift/gift_img.json" # 服务器url

        # 尝试从服务器获取数据
        try:
            async with aiohttp.ClientSession(connector=await dns_resolver.connector()) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        with open(img_path, "wb+") as f:
                            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
                    else:
                        raise ValueError("无法获取Nya-WSL服务器存档数据...")

        # 读取内置数据
        except Exception:
            gift_mapping = gift_map.gift_mapping
            blind_box = gift_map.blind_box

            with open(img_path, "wb+") as f:
                f.write(orjson.dumps(gift_mapping + blind_box, option=orjson.OPT_INDENT_2))  # pyright: ignore[reportOperatorIssue]

    def set_room_id(self, room_id):
        """
        设置房间号

        :param room_id: 房间号
        """

        self.room_id = room_id

    async def get_blind_box(self, gift_ids: list) -> dict:
        """
        获取盲盒礼物列表
        
        :param gift_ids (_list_): 盲盒礼物ID
        :return dict: 盲盒礼物列表
        """

        url = f"{base_config.get('api', 'server', 'http://api.travail.nya-wsl.cn')}/gift/get_blind_boxes"
        data = {
            "gift_ids": gift_ids,
            "version": f"{base_ver.base_version}.{env.get_key().get('version', '0')}"
        }

        async with aiohttp.ClientSession(connector=await dns_resolver.connector()) as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    if resp_data:
                        return resp_data
                    else:
                        logger.error("获取盲盒礼物列表失败: API未返回错误详情")
                        return {}
                else:
                    logger.error(f"请求盲盒礼物列表失败: {response.status}")
                    return {}

    async def get_area_id(self):
        """
        获取直播分区
        """

        url = "https://api.live.bilibili.com/room/v1/Room/get_info"
        params = {
            "room_id": self.room_id
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
        }

        async with aiohttp.ClientSession(connector=await dns_resolver.connector()) as session:
            async with session.get(url, params=params, headers=headers) as response:  # pyright: ignore[reportArgumentType]
                if response.status == 200:
                    data = await response.json()
                    if data["code"] == 0:
                        self.area_parent_id = data["data"]["parent_area_id"]
                        self.area_id = data["data"]["area_id"]
                    else:
                        logger.error(f"获取{self.room_id}直播分区失败：{data}")
                else:
                    logger.error(f"请求直播分区失败：{response.status}")

    async def get_room_gift(self, platform = "android") -> list:
        """
        获取房间礼物

        Args:
            platform (_str_): pc、android
        """

        await self.get_area_id()

        url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/roomGiftList"
        params = {
            "platform": platform,
            "room_id": self.room_id,
            "area_parent_id": self.area_parent_id,
            "area_id": self.area_id
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0"
        }

        async with aiohttp.ClientSession(connector=await dns_resolver.connector()) as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["code"] == 0:
                        # 只有一个值一般是红包，大概率还未下发自定义礼物数据，继续等待；最多等待3次避免无限递归；如果房间号为3可能未输入身份码，不可能获取到自定义礼物，直接跳过
                        # 部分直播间可能有红包和人气票两个值，目前没想到啥办法，暂不处理
                        if len(data["data"]["gift_config"]["room_config"]) == 1 and self.wait_num < 3 and self.room_id != 3:
                            self.wait_num += 1
                            logger.warning(f"房间{self.room_id}的自定义礼物数据可能还未下发，继续等待...")
                            await asyncio.sleep(5)
                            return await self.get_room_gift(platform)
                        else:
                            logger.info(f"成功获取房间{self.room_id}的礼物数据")

                        for gift in data["data"]["gift_config"]["room_config"]:
                            if gift["corner_mark"] == "玩法":
                                if gift["name"] not in self.custom_gifts:
                                    self.custom_gifts.append(gift["name"])
                        return data["data"]["gift_config"]["base_config"]["list"] + data["data"]["gift_config"]["room_config"]
                    else:
                        logger.error(f"获取房间礼物失败：{data['message']}")
                        return []
                else:
                    logger.error(f"请求房间礼物失败：{response.status}")
                    return []

    async def get_global_gift(self, platform = "android", source = "live") -> list:
        """
        获取全局礼物

        Args:
            platform (_str_): pc、android
            source (_str_): live
        """

        await self.get_area_id()

        url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/roomGiftConfig"
        params = {
            "platform": platform,
            "room_id": self.room_id,
            "source": source
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0"
        }

        async with aiohttp.ClientSession(connector=await dns_resolver.connector()) as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["code"] == 0:
                        return data["data"]["global_gift"]["list"] + data["data"]["list"]
                    else:
                        logger.error(f"获取全局礼物失败：{data['message']}")
                        return []
                else:
                    logger.error(f"请求全局礼物失败：{response.status}")
                    return []

    async def get_config(self, img_path = "data/gift_img.json"):
        try:
            # 获取房间礼物
            room_gifts = await self.get_room_gift()
            global_gifts = await self.get_global_gift()

            if not room_gifts and not global_gifts:
                gifts_data = []
            elif not room_gifts:
                gifts_data = global_gifts
            elif not global_gifts:
                gifts_data = room_gifts
            else:
                gifts_data = global_gifts + room_gifts

            if not gifts_data:
                logger.error("获取礼物数据失败，无法初始化礼物配置")
                return False

            gift_mapping = {}
            box_id = []

            # 获取盲盒礼物
            for data in gifts_data:
                gift_mapping[data['name']] = data['img_basic']
                if "盒" in data['name']:
                    box_id.append(data["id"])

            blind_box = {}
            if not box_id:
                logger.error("初始化礼物时未获取到盲盒数据")
            else:
                blind_box = await self.get_blind_box(box_id)

                if blind_box:
                    for gifts in blind_box.values():
                        for gift in gifts["gifts"]:
                            gift_mapping[gift['gift']] = gift['gift_img']
                else:
                    logger.error("盲盒数据为空")

            # 更新舰队数据
            guard = {
                "舰长": "guard-level-3.png",
                "提督": "guard-level-2.png",
                "总督": "guard-level-1.png",
                "辣条": "latiao.png"
            } # 舰队列表

            url = "https://travail.nya-wsl.com/bili_travail/gift/guard/" # 舰队图片url

            for k,v in guard.items():
                if not os.path.exists(f"data/{v}"):
                    gift_mapping[k] = url + v
                else:
                    gift_mapping[k] = f"data/{v}"

            with open(img_path, "wb") as f:
                f.write(orjson.dumps(gift_mapping, option=orjson.OPT_INDENT_2))

            if not blind_box:
                return "blind_box_none"
            else:
                return True

        except Exception:
            logger.error(f"获取礼物数据失败:\n{traceback.format_exc()}")
            return False