import os
import re
import json
import shutil
import requests
import gift_mapping as gift_map

from log import logger
from typing import Union

class BiliGiftManager:
    def init_gift(self, img_path, time_path, time: Union[int, float] = 0):
        """
        从服务器或本地预置数据初始化礼物
        
        :param img_path: 礼物数据字典保存路径
        :param time_path: 礼物时长字典保存路径
        :param time: 礼物时长
        """

        url = "https://travail.nya-wsl.com/bili_travail/gift/gift_img.json" # 服务器url

        # 尝试从服务器获取数据
        try:
            get_basic_gift = requests.get(url)
            if get_basic_gift.status_code == 200:
                time_dict = {}
                for gift in get_basic_gift.keys():
                    time_dict[gift] = time
                with open(img_path, "w+", encoding="utf-8") as f:
                    json.dump(get_basic_gift.json(), f, ensure_ascii=False, indent=4) # 从服务器拉取返回的json数据并写入
                with open(time_path, "w+", encoding="utf-8") as f:
                    json.dump(time_dict, f, ensure_ascii=False, indent=4)
            else:
                raise ValueError("无法获取Nya-WSL服务器存档数据...")

        # 读取内置数据
        except:
            time_dict = {}
            gift_mapping = gift_map.gift_mapping
            blind_box = gift_map.blind_box

            for gift in gift_mapping.keys():
                time_dict[gift] = time
            for v in blind_box.values():
                for gift in v:
                    time_dict[gift] = time

            with open(time_path, "w+", encoding="utf-8") as f:
                json.dump(time_dict, f, ensure_ascii=False, indent=4)
            with open(img_path, "w+", encoding="utf-8") as f:
                json.dump(gift_mapping, f, ensure_ascii=False, indent=4)

    def get_config(self, img_path = "data/gift_img.json", time_path = "data/gifts.json", time: Union[int, float] = 0, init = True):
        try:
            api = "https://api.live.bilibili.com/gift/v3/live/gift_config"
            User_Agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0"
            response = requests.get(api, headers={"User-Agent": User_Agent})
            response.encoding = "utf-8"
            response = response.json()
            gifts_data = response['data']
            gift_mapping = {}
            for data in gifts_data:
                name = data['name']
                img = data['img_basic']
                if not re.search("测试", name):
                    gift_mapping[name] = img

            # 更新舰队数据
            guard = {
                "舰长": "guard-level-3.png",
                "提督": "guard-level-2.png",
                "总督": "guard-level-1.png"
            } # 舰队列表

            url = "https://travail.nya-wsl.com/bili_travail/gift/guard/" # 舰队图片url

            for k,v in guard.items():
                if not os.path.exists(f"data/{v}"):
                    gift_mapping[k] = url + v
                else:
                    gift_mapping[k] = f"data/{v}"

            with open(img_path, "w", encoding="utf-8") as file:
                json.dump(gift_mapping, file, ensure_ascii=False, indent=4)

            for i in gift_mapping.keys():
                gift_mapping[i] = time

            # 更新预定义的盲盒数据
            blind_box = gift_map.blind_box
            for v in blind_box.values():
                for gift in v:
                    gift_mapping[gift] = time

            # 如果不是初始化状态，则使用已设定的礼物时长替换默认时长
            if not init:
                # 如果本地不存在数据，则返回None
                if os.path.exists(time_path) and os.path.exists(img_path):
                    with open(time_path, "r", encoding="utf-8") as file:
                        gifts = json.load(file)
                    with open("data/gifts_count.json", "r", encoding="utf-8") as file:
                        gifts_count = json.load(file)

                    for k, v in gifts.items():
                        if v != 0:
                            gift_mapping[k] = v

                        # 如果旧礼物不存在于新礼物中，这可能是因为B站删除了该礼物，则从新礼物数据中删除该礼物
                        if k not in gift_mapping.keys():
                            gift_mapping.pop(k)

                    with open(time_path, "w", encoding="utf-8") as file:
                        json.dump(gift_mapping, file, ensure_ascii=False, indent=4)

                    for k, v in gifts_count.items():
                        if v != 0:
                            gift_mapping[k] = v

                        if gifts_count[k] == 0:
                            gift_mapping[k] = time

                        if k not in gift_mapping.keys():
                            gift_mapping.pop(k)

                    with open("data/gifts_count.json", "w", encoding="utf-8") as file:
                        json.dump(gift_mapping, file, ensure_ascii=False, indent=4)
                else:
                    return None
            else:
                with open(time_path, "w", encoding="utf-8") as file:
                    json.dump(gift_mapping, file, ensure_ascii=False, indent=4)
                shutil.copy(time_path, "data/gifts_count.json")

            return True

        except Exception as e:
            logger.error(f"获取礼物数据失败: {e}")
            return False