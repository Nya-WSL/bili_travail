# 和礼物关联性不大的BILIBILI接口

import os
import json
import base64
import asyncio
import aiohttp

from urllib.parse import urlsplit

from libs import log
from libs import proxy as system_proxy

logger = log.logger

# 单张图片的请求超时：连接 5s、整体 10s，避免图床不可达时长时间卡住页面
FETCH_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=5)

# 模拟浏览器加载图片时的请求头，避免图床因缺少 Referer/UA 等字段拒绝请求
IMG_HEADERS = {
    "Accept": "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7,en-US;q=0.6,en;q=0.5",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "image",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-GPC": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:157.0) Gecko/20100101 Firefox/157.0",
}


def img_headers(url):
    """按目标地址补全 Host 与 Referer（浏览器同源加载图片时的写法）

    Host 必须由 URL 推导，不能写死：aiohttp 会把调用方传入的 Host 原样发出，
    写死成 i2.hdslb.com 而实际请求 i0/i1.hdslb.com 时，Host 与 TLS SNI 不一致会被图床拒绝。

    :param url: 图片url
    """
    host = urlsplit(url).netloc
    return {**IMG_HEADERS, "Host": host, "Referer": f"https://{host}/"}


async def _get_b64(url):
    """下载图片并转为 base64

    优先走系统代理（与浏览器使用的同一份设置），失败后回退直连：
    代理可能被中途关闭而注册表设置残留，也可能未覆盖该域名。

    :param url: 图片url
    """
    headers = img_headers(url)
    proxy = system_proxy.get_system_proxy()
    last_error = None

    for proxy_url in ([proxy, None] if proxy else [None]):
        try:
            async with aiohttp.ClientSession(timeout=FETCH_TIMEOUT) as session:
                async with session.get(url, headers=headers, proxy=proxy_url) as response:
                    response.raise_for_status()
                    content = await response.read()
            # 将图片数据转换为 Base64
            return base64.b64encode(content).decode('utf-8')
        except (asyncio.TimeoutError, aiohttp.ClientError, OSError) as e:
            last_error = e
            if proxy_url:
                logger.warning(f"图片请求经代理失败，回退直连: {url} - {e}")

    if isinstance(last_error, Exception):
        raise last_error
    raise aiohttp.ClientError(f"图片请求失败: {url}")

# GET方式请求B站图片数据并转换为base64
async def get_bili_img(url):
    """
    获取B站图片数据并转换为Base64格式

    图床不可达（如 i0/i1/i2.hdslb.com 连接超时）时返回空字符串而不是抛异常，
    避免个别头像加载失败导致整个页面渲染失败。

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
            try:
                bili_img = await _get_b64(url)
            except (asyncio.TimeoutError, aiohttp.ClientError, OSError) as e:
                # 失败结果不写入缓存，网络恢复后下次访问仍会重试
                logger.warning(f"获取B站图片失败: {url} - {e}")
                return ""
            except Exception as e:
                logger.error(f"获取B站图片时发生未知错误: {url} - {e}")
                return ""
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
