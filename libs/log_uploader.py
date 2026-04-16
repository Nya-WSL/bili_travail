"""
日志上传模块
提供日志上传功能，支持手动上传和自动上传（程序报错时）
"""

import os
import aiohttp
import traceback

from . import config
from .log import logger

class LogUploader:
    """日志上传器类"""

    def __init__(self, base_config):
        """
        初始化日志上传器

        Args:
            base_config: 配置对象
        """
        self.base_config = base_config
        self.dns_resolver = None
        self._init_dns_resolver()

    def _init_dns_resolver(self):
        """初始化DNS解析器"""
        try:
            from . import dns_resolver

            self.dns_resolver = dns_resolver
        except ImportError:
            logger.warning("dns_resolver模块未导入，将使用默认连接")
            self.dns_resolver = None

    async def upload_log(self, room_id, file_path=None, show_notification=False):
        """
        上传日志到服务器

        Args:
            room_id: 房间ID
            file_path: 日志文件路径，如果为None则使用当前日志文件
            show_notification: 是否显示通知

        Returns:
            dict: 包含成功状态和消息的字典
        """
        from nicegui import ui

        # 获取日志文件路径
        if file_path is None:
            try:
                from libs import log

                file_path = log.file_name
            except:
                return {"success": False, "message": "无法获取日志文件路径"}

        # 获取服务器地址
        url = self.base_config.get("api", "server", None)
        if url is None or url == "":
            message = "未配置服务器地址，上传日志失败"
            if show_notification:
                ui.notify(message, type="negative")
            logger.error(message)
            return {"success": False, "message": message}

        # 验证文件是否存在
        if not os.path.exists(file_path):
            message = f"文件不存在: {file_path}"
            if show_notification:
                ui.notify(message, type="negative")
            logger.error(message)
            return {"success": False, "message": message}

        url = f"{url}/log/{room_id}"
        file_obj = None

        try:
            data = aiohttp.FormData()
            file_obj = open(file_path, "rb")

            data.add_field(
                name="file",  # 参数名必须与FastAPI接口一致
                value=file_obj,
                filename=os.path.basename(file_path),
                content_type="application/octet-stream",
            )

            timeout = aiohttp.ClientTimeout(total=60)  # 60秒超时

            # 创建session，使用DNS解析器（如果可用）
            if self.dns_resolver:
                connector = await self.dns_resolver.connector()
            else:
                connector = aiohttp.TCPConnector()

            async with aiohttp.ClientSession(
                timeout=timeout, connector=connector
            ) as session:
                async with session.post(url, data=data) as response:
                    if response.status == 201:
                        result = await response.json()
                        message = f"日志上传成功，状态码：{result.get('status', None)}"
                        if show_notification:
                            ui.notify(message, type="positive")
                        logger.info(f"日志上传成功：{result}")
                        return {"success": True, "message": message, "data": result}
                    else:
                        error = await response.text()
                        message = f"日志上传失败，状态码: {response.status}"
                        if show_notification:
                            ui.notify(message, type="negative")
                        logger.error(f"{message}")
                        logger.error(f"服务器返回错误: {error}")
                        return {"success": False, "message": message, "error": error}

        except aiohttp.ClientError as e:
            message = "日志上传失败，发生网络错误: " + str(e)
            if show_notification:
                ui.notify(message, type="negative")
            logger.error(message + "\n" + traceback.format_exc())
            return {"success": False, "message": message}

        except Exception as e:
            message = "日志上传失败，发生错误: " + str(e)
            if show_notification:
                ui.notify(message, type="negative")
            logger.error(message + "\n" + traceback.format_exc())
            return {"success": False, "message": message}

        finally:
            if file_obj is not None and not file_obj.closed:
                file_obj.close()

    async def upload_on_error(self, room_id, error_info, file_path=None):
        """
        程序报错时自动上传日志

        Args:
            room_id: 房间ID
            error_info: 错误信息
            file_path: 日志文件路径，如果为None则使用当前日志文件

        Returns:
            dict: 包含成功状态和消息的字典
        """
        logger.error(f"程序发生错误，准备上传日志...")
        logger.error(f"错误信息: {error_info}")

        result = await self.upload_log(room_id, file_path, show_notification=False)

        if result["success"]:
            logger.info(f"错误日志已自动上传")
        else:
            logger.error(f"错误日志上传失败: {result['message']}")

        return result


# 全局变量，用于存储上传器实例和配置对象
_log_uploader = None
_base_config = None


def init_log_uploader(base_config=None):
    """
    初始化日志上传器（全局单例）

    Args:
        base_config: 配置对象（可选，如果不提供则使用默认配置）
    """
    global _log_uploader, _base_config
    if base_config is None:
        base_config = config.Config()
    _base_config = base_config
    _log_uploader = LogUploader(base_config)


def get_log_uploader():
    """
    获取日志上传器实例

    Returns:
        LogUploader: 日志上传器实例，如果未初始化则返回None
    """
    return _log_uploader


def setup_error_handler(base_config):
    """
    设置全局错误处理器，在程序报错时自动上传日志

    注意：这个函数需要在 libs.log 模块的 handle_exception 之后调用，
    这样可以确保异常先被记录到日志，然后再上传。

    无论用户是否启用上传，都会包装原有的异常处理器，
    确保异常始终被记录到本地日志文件。

    Args:
        base_config: 配置对象
    """
    import sys
    from loguru import logger

    # 初始化上传器
    init_log_uploader(base_config)

    # 保存原始的异常处理器（此时应该是 libs.log 中的 handle_exception）
    original_excepthook = sys.excepthook

    async def handle_error_upload():
        """异步处理错误上传"""
        try:
            # 检查用户是否启用了错误上传
            if not base_config.get("bool", "error_upload", False):
                return

            room_id = base_config.get("general", "room_id", 3)
            error_info = traceback.format_exc()

            uploader = get_log_uploader()
            if uploader:
                await uploader.upload_on_error(room_id, error_info)
        except Exception as e:
            # 使用 print 避免 logger 可能已经被关闭
            print(f"上传错误日志时发生异常: {e}")

    def custom_excepthook(exc_type, exc_value, exc_traceback):
        """自定义异常处理器"""
        # 首先调用原始处理器（ libs.log 的 handle_exception），
        # 这样确保异常被记录到日志文件
        if original_excepthook is not None:
            original_excepthook(exc_type, exc_value, exc_traceback)

        # 尝试上传日志（如果启用了上传功能）
        # 注意：这里需要在新的线程或进程中进行，避免阻塞
        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(handle_error_upload())
            finally:
                loop.close()
        except Exception as e:
            # 使用 print 避免 logger 可能已经被关闭
            print(f"错误处理器执行失败: {e}")

    # 设置自定义异常处理器，这样会包装原有的处理器
    sys.excepthook = custom_excepthook