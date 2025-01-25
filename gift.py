import os
import json
import requests
from blive_crower import get_bili_h5
from typing import Union
from bs4 import BeautifulSoup

def init_gift(img_path, time_path, time: Union[int, float] = 0):
    """
    初始化礼物数据
    :param img_path: 礼物数据字典保存路径
    :param time_path: 礼物时长字典保存路径
    :param time: 礼物时长
    """
    url = "https://nya-wsl.com/bili_travail/gift/gift_img.json"
    try:
        get_basic_gift = requests.get(url)
        if get_basic_gift.status_code == 200:
            print("[INIT] 成功获取Nya-WSL服务器存档数据...")
            with open(img_path, "w+", encoding="utf-8") as f:
                json.dump(get_basic_gift.json(), f, ensure_ascii=False, indent=4) # 从服务器拉取返回的json数据并写入
        else:
            raise ValueError("[ERROR] 无法获取Nya-WSL服务器存档数据...")
    except:
        print("[ERROR] 联网获取礼物数据失败...")
        print("[INIT] 尝试重构基础礼物数据...")
        import gift_mapping as gift_map
        time_dict = {}
        gift_mapping = gift_map.gift_mapping
        for gift in gift_mapping.keys():
            time_dict[gift] = time
        with open(time_path, "w+", encoding="utf-8") as f:
            json.dump(time_dict, f, ensure_ascii=False, indent=4)
        print("[INIT] 数据已重构为基础预设...")

def get_gift(room_id, path = "data/gifts.json", json_path = "data/gift_img.json", h5_path = "data/saved_page.html", show = False, write = True, time: Union[int, float] = 0, write_time = False, return_dict = False):
    """
    爬取并解析B站直播间礼物标签和URL，保存为JSON文件
    :param room_id: 房间号
    :param path: write_time保存JSON文件的路径，需指定到文件
    :param json_path: get_bili_h5()和write的json文件的路径，需指定到文件
    :param h5_path: 需解析的HTML文件的路径，需指定到文件
    :param show: 是否打印解析结果
    :param write: 是否将解析结果保存为JSON文件
    :param time: 礼物时长
    :param write_time: 是否将礼物时长保存为JSON文件
    :param return_dict: 是否返回解析结果的字典
    """

    # 使用blive_crower爬取所连接的直播间h5代码
    is_html = False
    html_content = get_bili_h5(room_id, json_path, h5_path)
    if html_content: # 如果返回的是return_json_status = True
        with open(json_path, "r", encoding="utf-8") as f:
            gift_mapping = json.load(f)
    else:
        is_html = True
        with open(h5_path, "r", encoding="utf-8") as f:
            html_content = f.read()

    if is_html:
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

            # 将标签和URL对应起来
            gift_mapping[gift_name] = img_url
            gift_mapping.pop('error', "None")

            guard = {
                "舰长": "guard-level-3.png",
                "提督": "guard-level-2.png",
                "总督": "guard-level-1.png"
            }
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
    if write:
        # 写入json文件
        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(gift_mapping, file, ensure_ascii=False, indent=4)
        os.remove(h5_path)
    if write_time:
        tmp_dict = {}
        for k,v in gift_mapping.items():
            tmp_dict[k] = time
        # 写入json文件
        with open(path, "w", encoding="utf-8") as file:
            json.dump(tmp_dict, file, ensure_ascii=False, indent=4)
    if return_dict:
        # 返回字典
        return gift_mapping