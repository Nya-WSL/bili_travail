from log import logger
import aiohttp
import config as travail_config

async def stat(room_id: int, uid: int, version: str, time: str) -> bool:
    base_config = travail_config.Config()

    url = f"{base_config.get('api', 'server', 'http://api.travail.nya-wsl.cn')}/stat"
    data = {
        "room_id": room_id,
        "uid": uid,
        "version": version,
        "time": time
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status != 200:
                logger.error(f"请求上传统计信息失败: {response.status}")
                return False
            else:
                return True