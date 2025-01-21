import os
import json
from typing import Union
from bs4 import BeautifulSoup

def get_gift(path: str, h5_path = "example.htm", show = False, write = True, time: Union[int, float] = 0, write_time = False, return_dict = False):
    """
    解析B站直播间礼物标签和URL，并保存为JSON文件
    :param path: 保存JSON文件的路径
    :param h5_path: 需解析的HTML文件的路径
    :param show: 是否打印解析结果
    :param write: 是否将解析结果保存为JSON文件
    :param time: 礼物时长
    :param write_time: 是否将礼物时长保存为JSON文件
    :param return_dict: 是否返回解析结果的字典
    """

    # 打开并读取 HTML 文件内容
    with open(h5_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # 创建一个空字典来存储礼物标签和URL
    gift_mapping = {}

    # 找到所有的礼物项
    gift_items = soup.find_all('div', class_='gift-item')

    # 遍历每个礼物项，提取标签和URL
    for item in gift_items:

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
        with open(path, "w", encoding="utf-8") as file:
            json.dump(gift_mapping, file, ensure_ascii=False, indent=4)
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