import os
import re
import json
import shutil
import aiofiles
import requests
import blive_crower
import gift_mapping as gift_map
from typing import Union
from bs4 import BeautifulSoup

class BiliGiftManager:

    def init_gift(self, img_path, time_path, time: Union[int, float] = 0):
        """
        初始化礼物数据
        :param img_path: 礼物数据字典保存路径
        :param time_path: 礼物时长字典保存路径
        :param time: 礼物时长
        """

        url = "https://nya-wsl.com/bili_travail/gift/gift_img.json" # 服务器url

        # 尝试从服务器获取数据
        try:
            get_basic_gift = requests.get(url)
            if get_basic_gift.status_code == 200:
                # print("[INIT] 成功获取Nya-WSL服务器存档数据...")
                time_dict = {}
                for gift in get_basic_gift.keys():
                    time_dict[gift] = time
                with open(img_path, "w+", encoding="utf-8") as f:
                    json.dump(get_basic_gift.json(), f, ensure_ascii=False, indent=4) # 从服务器拉取返回的json数据并写入
                with open(time_path, "w+", encoding="utf-8") as f:
                    json.dump(time_dict, f, ensure_ascii=False, indent=4)
            else:
                raise ValueError("[ERROR] 无法获取Nya-WSL服务器存档数据...")

        # 读取内置数据
        except:
            # print("[ERROR] 联网获取礼物数据失败...")
            # print("[INIT] 尝试重构基础礼物数据...")
            time_dict = {}
            gift_mapping = gift_map.gift_mapping
            blind_box = gift_map.blind_box

            for gift in gift_mapping.keys():
                time_dict[gift] = time
            for v in blind_box.values():
                gift_mapping.update(v)
                for gift in v.keys():
                    time_dict[gift] = time

            with open(time_path, "w+", encoding="utf-8") as f:
                json.dump(time_dict, f, ensure_ascii=False, indent=4)
            with open(img_path, "w+", encoding="utf-8") as f:
                json.dump(gift_mapping, f, ensure_ascii=False, indent=4)
            # print("[INIT] 数据已重构为基础预设...")

    async def get_live_h5(self, room_id, h5_path = "data/saved_page.html", headless = True, init = False):
        """
        爬取B站直播间
        :param room_id: 房间号
        :param h5_path: 解析的HTML文件的路径，需指定到文件
        :param headless: 无头模式
        :param init: 是否处于初始化状态
        """

        # 初始化变量
        self.room_id = room_id
        self.h5_path = h5_path

        # 使用blive_crower爬取所连接的直播间h5代码
        self.html_content = await blive_crower.get_bili_h5(room_id, h5_path, headless, init)
        return self.html_content

    def get_gift_config(self, img_path = "data/gift_img.json", time_path = "data/gifts.json", time: Union[int, float] = 0, init = True):
        try:
            url = "https://api.live.bilibili.com/gift/v3/live/gift_config"
            User_Agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0"
            response = requests.get(url, headers={"User-Agent": User_Agent})
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

            url = "https://nya-wsl.com/images/bili_travail/"

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
            for k, v in blind_box.items():
                for gift in v.keys():
                    gift_mapping[gift] = time

            # 如果不是初始化状态，则使用已设定的礼物时长替换默认时长
            if not init:
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
                with open(time_path, "w", encoding="utf-8") as file:
                    json.dump(gift_mapping, file, ensure_ascii=False, indent=4)
                shutil.copy(time_path, "data/gifts_count.json")

            return True

        except:
            return False


    async def convert_h5_to_json(self, h5_path: str, write_img = True, write_time = True, img_path = "data/gift_img.json", time_path = "data/gifts.json", time: Union[int, float] = 0):
        """
        爬取并解析B站直播间礼物标签和URL，保存为JSON文件
        :param h5_path: 解析的HTML文件的路径，需指定到文件
        :param write_img: 是否将解析结果保存为JSON文件
        :param write_time: 是否将礼物时长保存为JSON文件
        :param img_path: write_img保存JSON文件的路径，需指定到文件
        :param time_path: write_time保存JSON文件的路径，需指定到文件
        :param time: 礼物时长
        """

        async with aiofiles.open(h5_path, "r", encoding="utf-8") as f:
            html_content = await f.read()

        soup = BeautifulSoup(html_content, 'html.parser') # 使用BeautifulSoup解析HTML

        gift_mapping = {} # 创建一个空字典来存储礼物标签和URL

        blind_box = gift_map.blind_box

        gift_items = soup.find_all('div', class_='gift-item') # 找到所有的礼物项

        for item in gift_items: # 遍历每个礼物项，提取标签和URL

            # 获取图像URL
            img_div = item.find('div', class_='img')
            if img_div:  # 确保img_div存在
                img_url = img_div['style']
                img_url = img_url.split('url("')[1].split(')')[0].strip("'").replace('webp"', "webp")
            else:
                img_url = "error"

            # 获取礼物标签
            gift_tag = item.find('p', class_='gift-label')
            if gift_tag:  # 确保gift_tag存在
                gift_name = gift_tag.text.strip()
            else:
                gift_name = "error"

            # 将标签和URL对应
            gift_mapping[gift_name] = img_url
            if 'error' in gift_mapping:
                del gift_mapping['error']

            guard = {
                "舰长": "guard-level-3.png",
                "提督": "guard-level-2.png",
                "总督": "guard-level-1.png"
            } # 舰队列表

            url = "https://nya-wsl.com/images/bili_travail/"

            for k,v in guard.items():
                if not os.path.exists(f"data/{v}"):
                    gift_mapping[k] = url + v
                else:
                    gift_mapping[k] = f"data/{v}"

        if write_img:
            for v in blind_box.values():
                gift_mapping.update(v)
            with open(img_path, "w", encoding="utf-8") as file:
                json.dump(gift_mapping, file, ensure_ascii=False, indent=4)

        if write_time:
            tmp_dict = {}
            for k,v in gift_mapping.items():
                tmp_dict[k] = time
            # 更新预定义的盲盒数据
            for v in blind_box.values():
                for gift in v.keys():
                    gift_mapping[gift] = time
            with open(time_path, "w", encoding="utf-8") as file:
                json.dump(tmp_dict, file, ensure_ascii=False, indent=4)


    # 删除文件
    def remove_h5_file(self, h5_path):
        try:
            os.remove(h5_path)
        except FileNotFoundError:
            # print(f"[WARNING] 文件 {h5_path} 不存在，跳过删除")
            pass
        except PermissionError:
            # print(f"[ERROR] 没有权限删除文件：{h5_path}")
            pass