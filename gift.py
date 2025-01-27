import os
import json
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
                print("[INIT] 成功获取Nya-WSL服务器存档数据...")
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
            print("[ERROR] 联网获取礼物数据失败...")
            print("[INIT] 尝试重构基础礼物数据...")
            time_dict = {}
            gift_mapping = gift_map.gift_mapping
            for gift in gift_mapping.keys():
                time_dict[gift] = time
            with open(time_path, "w+", encoding="utf-8") as f:
                json.dump(time_dict, f, ensure_ascii=False, indent=4)
            with open(img_path, "w+", encoding="utf-8") as f:
                json.dump(gift_mapping, f, ensure_ascii=False, indent=4)
            print("[INIT] 数据已重构为基础预设...")

    def get_live_h5(self, room_id, h5_path = "data/saved_page.html", headless = True):
        """
        爬取B站直播间
        :param room_id: 房间号
        :param h5_path: 解析的HTML文件的路径，需指定到文件
        :param headless: 无头模式
        """

        # 初始化变量
        self.room_id = room_id
        self.h5_path = h5_path

        # 使用blive_crower爬取所连接的直播间h5代码
        self.html_content = blive_crower.get_bili_h5(room_id, h5_path, headless)

    def convert_h5_to_json(self, h5_path: str, write_img = True, write_time = True, img_path = "data/gifts_img.json", time_path = "data/gifts.json", time: Union[int, float] = 0, show = False, return_dict = False):
        """
        爬取并解析B站直播间礼物标签和URL，保存为JSON文件
        :param h5_path: 解析的HTML文件的路径，需指定到文件
        :param write_img: 是否将解析结果保存为JSON文件
        :param write_time: 是否将礼物时长保存为JSON文件
        :param img_path: write_img保存JSON文件的路径，需指定到文件
        :param time_path: write_time保存JSON文件的路径，需指定到文件
        :param time: 礼物时长
        :param show: 是否打印解析结果
        :param return_dict: 是否返回解析结果的字典
        """

        with open(h5_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser') # 使用BeautifulSoup解析HTML

        gift_mapping = {} # 创建一个空字典来存储礼物标签和URL

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
                if not os.path.exists(f"data/{k}"):
                    gift_mapping[k] = url + v
                else:
                    gift_mapping[k] = f"data/{v}"

        if show:
            # 打印映射结果
            for url, name in gift_mapping.items():
                print(f"URL: {url} -> 标签: {name}")

        if write_img:
            with open(img_path, "w", encoding="utf-8") as file:
                json.dump(gift_mapping, file, ensure_ascii=False, indent=4)

        if write_time:
            tmp_dict = {}
            for k,v in gift_mapping.items():
                tmp_dict[k] = time
            with open(time_path, "w", encoding="utf-8") as file:
                json.dump(tmp_dict, file, ensure_ascii=False, indent=4)

        if return_dict:
            # 返回字典
            return gift_mapping

    # 删除文件
    def remove_h5_file(self, h5_path):
        try:
            os.remove(h5_path)
        except FileNotFoundError:
            print(f"[WARNING] 文件 {h5_path} 不存在，跳过删除")
        except PermissionError:
            print(f"[ERROR] 没有权限删除文件：{h5_path}")