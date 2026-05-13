import os
import sys
import traceback
import aiohttp
import zipfile
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) # 将上级目录加入路径，用于导入hash模块

import hash

from .log import logger
from . import dns_resolver
from . import config as travail_config

from nicegui import ui, app

file_name = "cache\\bili_travail_update.zip"
base_config = travail_config.Config()

async def get_sha(url: str):
    async with aiohttp.ClientSession(connector=await dns_resolver.connector()) as session:
        async with session.get(url) as response:
            if response.status != 200:
                logger.error(f'获取SHA256失败：{response.status} {response.reason}')
                return None
            return await response.text()

async def update(zipUrl):
    if os.path.exists("update.bat"):
        os.remove("update.bat")

    async def download(url, save_path):
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
                cancelButton.on_click(lambda: close_session())
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
            server_hash = await get_sha(url + ".sha256")
            local_hash = hash.get_hash(save_path)
            percent_dialog.set_text(f"""服务器返回SHA256：{server_hash if server_hash else "获取失败"}
本地文件SHA256：{local_hash if local_hash else "计算失败"}""")
            await asyncio.sleep(5)
            if server_hash != local_hash:
                ui.notify("更新失败：SHA256校验失败，请检查日志", type="negative")
                logger.error(f"更新失败：SHA256校验失败, 服务器返回的SHA256：{server_hash}，本地文件的SHA256：{local_hash}")
                percent_dialog.set_text("更新失败：SHA256校验失败，请检查日志")
                return

        Unzip = zipfile.ZipFile(file_name, mode='r')
        percent_dialog.set_text("正在解压更新包...")
        await asyncio.sleep(1)
        for names in Unzip.namelist():
            Unzip.extract(names, os.getcwd())
        Unzip.close()
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
        cancelButton = ui.button("取消")
        try:
            await download(zipUrl, file_name)
        except Exception as e:
            ui.notify(f"更新失败：{e}", type="negative")
            logger.error(f"更新失败：{traceback.format_exc()}")
            return