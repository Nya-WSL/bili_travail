import aiohttp
from aiohttp.resolver import AsyncResolver


async def connector():
    # 创建自定义解析器
    resolver = AsyncResolver(
        nameservers=["8.8.8.8", "114.114.114.114"]
    )

    # 创建连接器并设置解析器
    connector = aiohttp.TCPConnector(resolver=resolver)

    return connector