import base64
import requests

# GET方式请求B站图片数据并转换为base64
def get_bili_img(url):
    """
    获取B站图片数据并转换为Base64格式
    
    :param url: 图片url
    """
    # 获取图片数据
    if url != "":
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功
        # 将图片数据转换为 Base64
        bili_img = base64.b64encode(response.content).decode('utf-8')
        return f"data:image/jpeg;base64,{bili_img}"
    else:
        return ""