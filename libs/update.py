import os
import sys
import traceback
import aiohttp
import aiofiles
import zipfile
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) # 将上级目录加入路径，用于导入hash模块

from .log import logger
from . import hash_utils
from . import dns_resolver
from . import config as travail_config

from nicegui import ui, app

file_name = "cache\\bili_travail_update.zip"
base_config = travail_config.Config()

async def get_sha(url: str, version: str) -> str:
    async with aiohttp.ClientSession(connector=await dns_resolver.connector()) as session:
        async with session.get(url) as response:
            if response.status != 200:
                logger.error(f'获取SHA256失败：{response.status} {response.reason}')
                return None
            async with aiofiles.open(f"cache\\{version}.sha256", 'wb') as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    await f.write(chunk)

            with open(f"cache\\{version}.sha256", 'r') as f:
                return f.read()

async def update(zip_url, version):
    if os.path.exists("update.bat"):
        os.remove("update.bat")

    async def download(url, save_path, version):
        async def close_session():
            await session.close()
            dialog.close()

        dialog.open()
        percent_dialog.set_text("正在下载更新包")
        logger.debug(f"更新包：{url}")

        if not os.path.exists("cache"):
            os.mkdir("cache")

        async with aiohttp.ClientSession(connector=await dns_resolver.connector()) as session:
            async with session.get(url) as response:
                cancel_button.on_click(lambda: close_session())
                if response.status != 200:

                    ui.notify("更新失败", type="negative")
                    logger.error(f'更新包下载失败：{response.status} {response.reason}')
                    percent_dialog.set_text(f'更新失败：{response.status} {response.reason}')
                    await session.close()
                    return

                with open(save_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        f.write(chunk)
                        if response.content_length is not None and response.content_length > 0:
                            percent_dialog.set_text("下载进度：" + "%.2f%%" % (f.tell() / response.content_length * 100))
                        else:
                            percent_dialog.set_text(f"下载中... 已下载 {f.tell()} 字节")

                        if not chunk:
                            percent_dialog.set_text("下载完成！")
                            await asyncio.sleep(1)
                            break

        if base_config.get("general", "check_sha256", True):
            percent_dialog.set_text("正在校验SHA256...")
            try:
                if "hi168" in url:
                    url = base_config.get("api", "server", None)

                    if url is None:
                        raise Exception("未配置API地址，无法获取SHA256")

                    timeout = aiohttp.ClientTimeout(total=10)  # 10秒超时

                    params = {
                        "version": version,
                        "type": "sha256"
                    }

                    async with aiohttp.ClientSession(timeout=timeout, connector=await dns_resolver.connector()) as session:
                        async with session.get(f"{url}/update", params=params) as response:
                            if response.status == 200:
                                result = await response.json()
                                server = result.get("url", None)
                                sha = await get_sha(server, version)
                                server_hash = sha.strip().lower()
                                if server_hash is None:
                                    result = f"获取sha256失败: {result.get('message', '未知错误')}"
                                    logger.error(result)
                                    return
                            else:
                                error = await response.text()
                                result = f"获取sha256失败:{error}，状态码: {response.status}"
                                raise Exception(result)
                else:
                    sha = await get_sha(url.replace('.zip', '.sha256'), version)
                    server_hash = sha.strip().lower()
            except Exception:
                logger.error(traceback.format_exc())
                server_hash = None
            local_hash = hash_utils.get_hash(save_path).strip().lower()

            if server_hash != local_hash:
                ui.notify("更新失败：SHA256校验未通过，请检查日志", type="negative")
                logger.error(f"更新失败：SHA256校验未通过, 服务器返回的SHA256：{server_hash}，本地文件的SHA256：{local_hash}")
                percent_dialog.set_text("更新失败：SHA256校验未通过，请检查日志")
                return

        unzip = zipfile.ZipFile(file_name, mode='r')
        percent_dialog.set_text("正在解压更新包...")
        await asyncio.sleep(1)
        for names in unzip.namelist():
            unzip.extract(names, os.getcwd())
        unzip.close()
        percent_dialog.set_text("正在更新...")
        await asyncio.sleep(1)
        with open("update.bat", "w") as f:
            f.write(rf"""
@chcp 65001
cd /d {os.getcwd()}
taskkill /f /im bili_travail.exe
taskkill /f /im start.exe
timeout /t 3 /nobreak
rmdir /s /q _internal
timeout /t 1 /nobreak
robocopy update ./ /E /UNILOG:logs\update.log /NP /NS /V /TEE
rmdir /s /q update
rmdir /s /q cache
start start.exe
timeout /t 1 /nobreak
""")
        os.system("update.bat")
        app.shutdown()

    with ui.dialog() as dialog, ui.card(align_items="center"):
        percent_dialog = ui.label("")
        cancel_button = ui.button("取消")
        try:
            await download(zip_url, file_name, version)
        except Exception as e:
            ui.notify(f"更新失败：{e}", type="negative")
            logger.error(f"更新失败：{traceback.format_exc()}")
            return