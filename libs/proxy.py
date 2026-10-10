"""系统代理探测

aiohttp 默认 trust_env=False，既不读 HTTP_PROXY/HTTPS_PROXY 环境变量，
也不读 Windows「Internet 选项」里的系统代理设置，因此在开启代理的机器上会直连，
出现浏览器能访问、程序却连接超时（信号灯超时时间已到）的情况。
"""

import os
import sys

from libs import log

logger = log.logger

# Windows「Internet 选项」中存放系统代理的注册表位置
_WIN_INTERNET_SETTINGS = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def _parse_proxy_server(server: str) -> str | None:
    """解析 Windows 注册表 ProxyServer 字段

    支持 "127.0.0.1:7890" 与 "http=127.0.0.1:7890;https=127.0.0.1:7890" 两种写法。
    aiohttp 只支持 http(s) 代理，仅配置了 socks 时返回 None。

    :param server: 注册表 ProxyServer 的原始值
    """
    server = (server or "").strip()
    if not server:
        return None

    if "=" not in server:
        return server if "://" in server else f"http://{server}"

    entries = {}
    for part in server.split(";"):
        key, _, value = part.partition("=")
        key, value = key.strip().lower(), value.strip()
        if key and value:
            entries[key] = value

    for scheme in ("https", "http"):
        if entries.get(scheme):
            return f"http://{entries[scheme]}"

    logger.debug("系统代理仅配置了不被支持的协议: {}", server)
    return None


def _from_env() -> str | None:
    """从环境变量读取代理"""
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        value = os.environ.get(name, "").strip()
        if not value:
            continue
        if "://" not in value:
            value = f"http://{value}"
        if value.startswith(("http://", "https://")):
            return value
        logger.debug("暂不支持的代理协议，已忽略: {}", value)
        return None
    return None


def _from_windows_registry() -> str | None:
    """从 Windows 注册表读取系统代理（浏览器使用的同一份设置）"""
    if sys.platform != "win32":
        return None

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_INTERNET_SETTINGS) as key:
            enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not enable:
                return None
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
    except OSError:
        return None

    return _parse_proxy_server(str(server))


def get_system_proxy() -> str | None:
    """返回当前系统代理地址，如 http://127.0.0.1:7890；未开启代理时返回 None"""
    return _from_env() or _from_windows_registry()
