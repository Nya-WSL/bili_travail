import os
import re
import json
import aiohttp
import gift_mapping as gift_map

from log import logger

class BiliGiftManager:
    def __init__(self):
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        if config.get("room_id", "") != "":
            self.room_id = config["room_id"]
        else:
            self.room_id = 3

        self.area_parent_id = 0
        self.area_id = 0

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
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        with open(img_path, "w+", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)
                    else:
                        raise ValueError("无法获取Nya-WSL服务器存档数据...")

        # 读取内置数据
        except:
            gift_mapping = gift_map.gift_mapping
            blind_box = gift_map.blind_box

            with open(img_path, "w+", encoding="utf-8") as f:
                json.dump(gift_mapping + blind_box, f, ensure_ascii=False, indent=4)

    def set_room_id(self, room_id):
        """
        设置房间号

        :param room_id: 房间号
        """

        self.room_id = room_id

    async def get_blind_box(self, gift_id) -> dict:
        """
        获取盲盒礼物列表
        
        :param gift_id: 盲盒礼物ID
        :return dict: 盲盒礼物列表
        """

        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        url = "https://api.live.bilibili.com/xlive/general-interface/v1/blindFirstWin/getInfo"
        params = {
            "gift_id": gift_id
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0",
            "Cookie": f"SESSDATA={config.get('SESSDATA', '')}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['code'] == 0:
                        return data['data']
                    else:
                        logger.error(f"获取盲盒礼物列表({gift_id})失败: {data['message']}")
                        return {}
                else:
                    logger.error(f"请求盲盒礼物列表({gift_id})失败: {response.status}")
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

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["code"] == 0:
                        self.area_parent_id = data["data"]["parent_area_id"]
                        self.area_id = data["data"]["area_id"]
                    else:
                        logger.error(f"获取直播分区失败：{data['message']}")
                else:
                    logger.error(f"请求直播分区失败：{response.status}")

    async def get_room_gift(self, platform = "android"):
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

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["code"] == 0:
                        return data["data"]["gift_config"]["base_config"]["list"]
                    else:
                        logger.error(f"获取房间礼物失败：{data['message']}")
                else:
                    logger.error(f"请求房间礼物失败：{response.status}")

    async def get_config(self, img_path = "data/gift_img.json"):
        try:
            # 获取房间礼物
            gifts_data = await self.get_room_gift("android")

            box_gifts_list = {}
            gift_mapping = {}
            box_id = []

            # 获取盲盒礼物
            for data in gifts_data:
                gift_mapping[data['name']] = data['img_basic']
                if re.search("盲盒", data['name']):
                    box_id.append(data["id"])

            if box_id == []:
                logger.error("初始化礼物时未获取到盲盒数据")
            else:
                for id in box_id:
                    blind_box = await self.get_blind_box(id)

                    if blind_box != {}:
                        box_gifts_list = blind_box.get("gifts", {})
                        if box_gifts_list != {}:
                            for gift in box_gifts_list:
                                gift_mapping[gift["gift_name"]] = gift["gift_img"]
                        else:
                            logger.error(f"盲盒({id})数据为空，可能是因为未登录账号")
                    else:
                        logger.error(f"盲盒({id})数据为空")

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

            with open(img_path, "w", encoding="utf-8") as file:
                json.dump(gift_mapping, file, ensure_ascii=False, indent=4)

            if box_gifts_list == {}:
                return "blind_box_none"
            else:
                return True

        except Exception as e:
            logger.exception(f"获取礼物数据失败: {e}")
            return False