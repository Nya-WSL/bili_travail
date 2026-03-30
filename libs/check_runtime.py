import os
import winreg
import aiohttp
import tempfile
import traceback

from .log import logger
from . import dns_resolver

install_path = os.path.join(tempfile.gettempdir(), "MicrosoftEdgeWebview2Setup.exe")

def webview2_check():
    """
    Edge WebView2 检测
    """
    # 检查注册表
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}")
    ]

    for hive, path in reg_paths:
        try:
            winreg.OpenKey(hive, path)
            logger.info(f"检测到 Edge WebView2 runtime 注册表项: {hive}\\{path}")
            return True
        except:
            continue

    # pywebview似乎也是检测的注册表，所以不检测安装路径

    # 检查常见安装路径
    # common_paths = [
    #     r"C:\Program Files (x86)\Microsoft\EdgeWebView\Application",
    #     os.path.join(os.environ.get('programfiles(x86)', ''), r"Microsoft\EdgeWebView\Application")
    # ]

    # for path in common_paths:
    #     if os.path.exists(path):
    #         logger.info(f"检测到 Edge WebView2 runtime 安装目录: {path}")
    #         return True

    return False

async def download_webview2():
    try:
        async with aiohttp.ClientSession(connector=await dns_resolver.connector()) as session:
            async with session.get("https://go.microsoft.com/fwlink/p/?LinkId=2124703") as response:
                if response.status == 200:
                    logger.info("正在下载 Edge WebView2 runtime 常青在线安装程序")
                    with open(install_path, "wb") as f:
                        f.write(await response.read())
                    logger.info("Edge WebView2 runtime 常青在线安装程序下载完成")
                    return True
                else:
                    logger.error(f"Edge WebView2 runtime 常青在线安装程序请求失败，状态码: {response.status}")
                    return False
    except:
        logger.error("Edge WebView2 runtime 常青在线安装程序下载失败:")
        logger.error(traceback.format_exc())
        return False

async def check_runtime():
    """
    检测运行时环境
    """
    if not webview2_check():
        logger.warning("未检测到 Edge WebView2 runtime，正在安装...")
        winget_status = os.system("winget --version >null 2>&1")

        try:
            if winget_status == 0:
                logger.info("检测到 winget，正在安装 Edge WebView2 runtime...")
                winget_status = os.system("winget install Microsoft.EdgeWebview2Runtime --accept-source-agreements --accept-package-agreements >null 2>&1")
                if winget_status == 0:
                    logger.info("Edge WebView2 runtime 安装成功")
                    return True
                else:
                    logger.error("使用 winget 安装 Edge WebView2 runtime 失败，错误代码: {winget_status}")
                    raise Exception("winget 安装失败")
        except:
            logger.warning("未检测到 winget，尝试使用在线安装程序安装...")
            download_status = await download_webview2()
            if download_status:
                logger.info("正在安装 Edge WebView2 runtime...")
                os.system(install_path)
                return True
            else:
                logger.error("无法下载 Edge WebView2 runtime，请手动安装")
                return False
    else:
        logger.info("已检测到 Edge WebView2 runtime")
        return True