import os
import aiohttp
import zipfile
import asyncio

from .log import logger
from . import dns_resolver
from nicegui import ui, app

file_name = "cache\\bili_travail_update.zip"

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
                        if response.content_length is not None:
                            percent_dialog.set_text("下载进度：" + "%.2f%%" % (f.tell() / response.content_length * 100))
                        else:
                            percent_dialog.set_text(f"下载中... 已下载 {f.tell()} 字节")

                        if not chunk:
                            percent_dialog.set_text("下载完成！")
                            await asyncio.sleep(1)
                            break

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
            logger.error(f"更新失败：{e}")
            return