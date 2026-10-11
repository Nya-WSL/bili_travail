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

# 只声明当前 aiohttp 真能解码的编码：
#   - br 需要 brotli（或 brotlicffi）
#   - zstd 需要 compression.zstd（Python 3.14+）或 backports.zstd；
#     本项目装的是 zstandard 包，aiohttp 并不认，此环境下 HAS_ZSTD 为 False
# 声明了却解不了，会在 response.read() 抛 ContentEncodingError，图片直接变空串，
# 所以这里按 aiohttp 自己的能力表来拼，和它内部 _gen_default_accept_encoding() 一致。
try:
    from aiohttp.compression_utils import HAS_BROTLI, HAS_ZSTD
except ImportError:  # aiohttp 内部模块路径变动时保守退化为 gzip/deflate
    HAS_BROTLI = HAS_ZSTD = False

ACCEPT_ENCODING = ", ".join(
    ["gzip", "deflate"]
    + (["br"] if HAS_BROTLI else [])
    + (["zstd"] if HAS_ZSTD else [])
)

# 模拟浏览器加载图片时的请求头，避免图床因缺少 Referer/UA 等字段拒绝请求
IMG_HEADERS = {
    "Accept": "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5",
    "Accept-Encoding": ACCEPT_ENCODING,
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

# 头像缓存文件
IMG_CACHE_FILE = "data/bili_img.json"

# 缓存读写锁：关于页会用 asyncio.gather 并发预取多个头像，若不串行化缓存更新，
# 每个协程都基于自己读到的旧快照写回「只含自己那一条」的缓存，最后一次写入会
# 丢掉其他条目，导致后续访问全部重新下载
_img_cache_lock = asyncio.Lock()


def _load_img_cache() -> dict:
    """读取头像缓存，文件不存在时初始化"""
    if not os.path.exists(IMG_CACHE_FILE):
        with open(IMG_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}

    with open(IMG_CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_img_cache(cache: dict) -> None:
    """写入头像缓存"""
    with open(IMG_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)


# GET方式请求B站图片数据并转换为base64
async def get_bili_img(url):
    """
    获取B站图片数据并转换为Base64格式

    图床不可达（如 i0/i1/i2.hdslb.com 连接超时）时返回空字符串而不是抛异常，
    避免个别头像加载失败导致整个页面渲染失败。

    :param url: 图片url
    """
    if url == "":
        return ""

    async with _img_cache_lock:
        cache = _load_img_cache()
        if url in cache:
            return f"data:image/jpeg;base64,{cache[url]}"

    # 下载放在锁外：多个头像依然并发拉取，只有缓存更新被串行化
    try:
        bili_img = await _get_b64(url)
    except (asyncio.TimeoutError, aiohttp.ClientError, OSError) as e:
        # 失败结果不写入缓存，网络恢复后下次访问仍会重试
        logger.warning(f"获取B站图片失败: {url} - {e}")
        return ""
    except Exception as e:
        logger.error(f"获取B站图片时发生未知错误: {url} - {e}")
        return ""

    async with _img_cache_lock:
        # 重新读取最新缓存再合并，避免覆盖并发下载期间其他协程写入的头像
        cache = _load_img_cache()
        cache[url] = bili_img
        _save_img_cache(cache)

    return f"data:image/jpeg;base64,{bili_img}"
