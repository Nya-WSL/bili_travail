import asyncio
import datetime

from nicegui import ui, app

from libs.log import logger
from libs.i18n import t
import libs.config as travail_config

base_config = travail_config.Config()

cd_status = False
reset_inherit_status = False

# 礼物翻倍/减半的指数上限：float 能表示的最大值约为 2 ** 1024，所以 2 ** 1023 以上的指数
# 与浮点数相乘时会抛 OverflowError（int too large to convert to float），这里取 1023 作为安全上限；
# 倒计时秒数本身的上限由 set_remaining_seconds 统一钳制
MAX_GIFT_EXPONENT = 1023


class CountdownTimer:
    def __init__(self, update_btn_state_func=None, cancel_button_ref=None):
        self.remaining_time = datetime.timedelta(0)  # 初始化剩余时间
        self.target_time: datetime.datetime | None = None  # 初始化目标时间
        self._paused = False  # 初始化暂停状态
        self._running = False  # 初始化运行状态
        self._paused_event = asyncio.Event()  # 初始化event
        self._paused_event.set()  # 最开始没有暂停
        self._task = None  # 初始化task
        self.exit_timer = None
        self._update_btn_state = update_btn_state_func
        self._cancel_button = cancel_button_ref
        self._b_connect_switch: ui.switch = None # 初始化blivedm连接状态开关对象

    def update_element(self, b_connect_switch):
        """更新b_connect_switch对象"""
        self._b_connect_switch = b_connect_switch

    def exit_func(self):
        if self._b_connect_switch:
            self._b_connect_switch.set_value(False)
            logger.info("计时器结束")
        else:
            logger.error("计时器结束，客户端为空")

    @property
    def remaining_seconds(self) -> float:
        if not self.target_time:
            return 0.0
        return max((self.target_time - datetime.datetime.now()).total_seconds(), 0.0)

    def set_remaining_seconds(self, seconds: float) -> None:
        if seconds < 0:
            seconds = 0
        now = datetime.datetime.now()
        # datetime 能表示的最大时长，now + delta 超出该值会抛 OverflowError: date value out of range
        max_delta = datetime.datetime.max - now

        try:
            delta = datetime.timedelta(seconds=seconds)
        except OverflowError:  # 秒数大到 timedelta 无法表示（如礼物翻倍叠加），直接取上限
            delta = max_delta

        if delta >= max_delta:
            logger.warning(f"倒计时超过上限，已限制到能表示的最大时间，当前秒数：{seconds}")
            delta = max_delta

        self.target_time = now + delta
        self.remaining_time = delta
        app.storage.general["countdown_time"] = delta.total_seconds()

    # 倒计时运行函数
    async def update(self):
        global cd_status
        while self._running and self.target_time:
            if self._paused:
                await self._paused_event.wait()  # 暂停时等待

            if self.remaining_seconds <= 0:
                self.stop()
                if not self.exit_timer and base_config.get("bool", "exit_timer", True):
                    logger.info("倒计时停止，启动计时器")
                    self.exit_timer = app.timer(base_config.get("num", "exit_time", 1800), lambda: self.exit_func(), once=True)  # pyright: ignore[reportArgumentType]
                break

            self.remaining_time = datetime.timedelta(seconds=self.remaining_seconds)
            app.storage.general["countdown_time"] = self.remaining_seconds
            cd_status = True
            await asyncio.sleep(1)

    # 运行倒计时
    def start(self):
        global cd_status
        # 如果倒计时未在运行
        if self._running:
            return

        self._running = True  # 修改运行状态
        if self.target_time is not None and self.target_time - datetime.datetime.now() != datetime.timedelta(0):  # 防止写入0时开始倒计时
            self._task = asyncio.create_task(self.update())  # 创建倒计时协程
            self._update_btn_state("start")  # 更新按钮状态
            cd_status = True  # 设置倒计时运行状态
            if self.exit_timer and self.exit_timer.active:
                logger.info("倒计时开始，停止计时器")
                self.exit_timer.cancel(with_current_invocation=True)  # 关闭退出计时器
        else:
            ui.notify(t("cd.enter_time"), type="negative")
            self._running = False

    # 暂停倒计时
    async def pause(self):
        global cd_status
        if self._running and not self._paused:  # 如果倒计时在运行且没有暂停
            self._paused = True
            self._paused_event.clear()  # 暂停计时器
            self._update_btn_state("pause")  # 更新按钮状态
            cd_status = False

    # 继续倒计时
    def resume(self):
        global cd_status
        if self._running and self._paused:
            self._paused = False
            self._paused_event.set()  # 恢复计时器
            self.set_remaining_seconds(app.storage.general["countdown_time"])
            self._update_btn_state("resume")  # 更新按钮状态
            cd_status = True

    # 停止倒计时
    def stop(self):
        global cd_status, reset_inherit_status
        if self._running:
            self._running = False
            self._paused = False
            if self._task:
                self._task.cancel()  # 结束协程
            # 取消退出计时器，防止事件循环残留
            if self.exit_timer is not None:
                self.exit_timer.cancel(with_current_invocation=True)
                self.exit_timer = None
            app.storage.general["countdown_time"] = 0
            self.remaining_time = datetime.timedelta(0)
            self._update_btn_state("stop")  # 更新按钮状态
            cd_status = False
        else:
            if reset_inherit_status:
                app.storage.general["countdown_time"] = 0
                self.remaining_time = datetime.timedelta(0)
                self._cancel_button.set_text(t("main.btn.stop"))
                self._cancel_button.disable()

    # 程序退出时的清理，只取消计时相关的 task/timer，
    # 不会清零 app.storage.general["countdown_time"]，从而保留可继承的倒计时
    def cleanup(self):
        global cd_status
        self._running = False
        self._paused = False
        if self._task:
            self._task.cancel()  # 结束协程
        if self.exit_timer is not None:
            self.exit_timer.cancel(with_current_invocation=True)
            self.exit_timer = None
        cd_status = False
