# 和礼物关联性不大的BILIBILI接口

import os
import json
import base64
import requests

def get_b64(url):
    response = requests.get(url)
    response.raise_for_status()  # 检查请求是否成功
    # 将图片数据转换为 Base64
    bili_img = base64.b64encode(response.content).decode('utf-8')
    return bili_img

# GET方式请求B站图片数据并转换为base64
def get_bili_img(url):
    """
    获取B站图片数据并转换为Base64格式
    
    :param url: 图片url
    """

    if not os.path.exists("data/bili_img.json"):
        with open("data/bili_img.json", "w", encoding="utf-8") as f:
            json.dump({}, f)

    # 获取图片数据
    if url != "":
        status = False
        with open("data/bili_img.json", "r", encoding="utf-8") as f:
            bili_img_data = json.load(f)

        if url not in bili_img_data.keys():
            bili_img = get_b64(url)
            bili_img_data[url] = bili_img
            status = True
        else:
            bili_img = bili_img_data[url]

        if status:
            with open("data/bili_img.json", "w", encoding="utf-8") as f:
                json.dump(bili_img_data, f, ensure_ascii=False, indent=4)

        return f"data:image/jpeg;base64,{bili_img}"
    else:
        return ""