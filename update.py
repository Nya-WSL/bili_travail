import os
import aiohttp
import zipfile
import asyncio
from nicegui import ui, app

file_name = "cache\\bili_travail_update.zip"

async def update(server):
    if os.path.exists("update.bat"):
        os.remove("update.bat")

    async def download(url, save_path):
        async def close_session():
            await session.close()
            dialog.close()

        dialog.open()
        percent_dialog.set_text("正在下载更新包")

        if not os.path.exists("cache"):
            os.mkdir("cache")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                cancelButton.on_click(lambda: close_session())

                with open(save_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        f.write(chunk)
                        percent_dialog.set_text("下载进度：" + "%.2f%%" % (f.tell() / response.content_length * 100))

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
            f.write(f"""
cd /d {os.getcwd()}
taskkill /f /im bili_travail.exe
timeout /t 3 /nobreak
move /y update\\* ./
rmdir /s /q update
rmdir /s /q cache
bili_travail.exe
""")
        os.system("update.bat")
        app.shutdown()

    with ui.dialog() as dialog, ui.card(align_items="center"):
        percent_dialog = ui.label("")
        cancelButton = ui.button("取消")
        if server == "GitHub":
            zipUrl = "https://github.com/Nya-WSL/bili_travail/releases/download/update/update.zip"
        elif server == "Overseas":
            zipUrl = "https://cloud.nya-wsl.cn/ms-drive/bili_travail/update/update.zip"
        elif server == "CN-HK":
            zipUrl = "https://travail.nya-wsl.com/bili_travail/update/update.zip"
        else:
            ui.notify("更新源不存在", type="negative")
            return
        try:
            await download(zipUrl, file_name)
        except Exception as e:
            ui.notify(f"更新失败：{e}", type="negative")
            return