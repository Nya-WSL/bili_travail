import os
import random
import asyncio
import aiohttp

from nicegui import ui
from libs import log
from libs import bili_api
from libs import config as travail_config
from libs import styles, dns_resolver

logger = log.logger


async def about_page():
    styles.page_styles()  # 加载自定义样式
    base_config = travail_config.Config()
    config = base_config.load()
    ui.query("body").style(
        f'background: url("{random.choice(config["general"]["background_image"])}") 0px 0px/cover'
    )  # 设置背景图片  # pyright: ignore[reportIndexIssue, reportArgumentType]

    # Card框
    with ui.card(align_items="center").classes("absolute-center"):
        ui.label(f"B站加班姬").classes("text-3xl")  # type: ignore[index]

        # 私货
        def read_or_create_file(file_path, default_content):
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                with open(file_path, "w+", encoding="utf-8") as f:
                    f.write(default_content)
                return default_content

        # 配置头像URL常量
        AVATAR_A = (
            "https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"
        )
        AVATAR_B = (
            "https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"
        )
        NAME_A = "高橋はるき"
        NAME_B = "狐日泽"

        async def fetch_text(session, url):
            """异步获取文本内容"""
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        return await response.json()
                    logger.warning(f"请求失败: {url} 状态码: {response.status}")
                    return None
            except asyncio.TimeoutError:
                logger.warning(f"请求超时: {url}")
            except aiohttp.ClientError as e:
                logger.error(f"网络错误: {url} - {e}")
            except Exception as e:
                logger.error(f"未知错误: {url} - {e}")
            return None

        async def get_remote_text(session):
            """尝试从多个源获取文本"""
            urls = [
                "https://nya-wsl.com/bili_travail/chat_msg.json",
                "http://version.nya-wsl.cn/bili_travail/chat_msg.json",
            ]

            for url in urls:
                text = await fetch_text(session, url)
                if text is not None:
                    return text
            return None

        async def display_chat_messages():
            """异步获取并显示聊天消息"""
            try:
                async with aiohttp.ClientSession(
                    connector=await dns_resolver.connector()
                ) as session:
                    # 获取远程文本
                    text = await get_remote_text(session)

                    # 如果获取到文本
                    if text:
                        # 随机选择消息组
                        if random.random() < 0.3:
                            # 排除group_a的其他消息
                            msg_groups = [k for k in text.keys() if k != "group_a"]
                            selected_group = (
                                random.choice(msg_groups) if msg_groups else "group_a"
                            )
                        else:
                            selected_group = "group_a"

                        msg = text.get(selected_group)
                        if msg:
                            await display_message_pair(msg)
                            return

                    # 使用本地文件作为回退
                    text_a = read_or_create_file(
                        "data/text_a.txt", "代码没写完，哪有脸睡觉"
                    )
                    text_b = read_or_create_file(
                        "data/text_b.txt", 'alias cd="sudo rm -rf"'
                    )

                    # 显示本地消息
                    ui.chat_message(
                        text_a,
                        avatar=await bili_api.get_bili_img(AVATAR_A),
                        name=NAME_A,
                        text_html=True,
                        sent=True,
                        sanitize=False,
                    )
                    ui.chat_message(
                        text_b,
                        avatar=await bili_api.get_bili_img(AVATAR_B),
                        name=NAME_B,
                        text_html=True,
                        sanitize=False,
                    )

            except Exception as e:
                logger.error(f"显示聊天消息失败: {e}")
                # 显示错误消息
                ui.notify("加载聊天消息失败，请稍后再试", type="negative")

        async def display_message_pair(msg):
            """显示一对聊天消息"""
            avatar_a = await bili_api.get_bili_img(AVATAR_A)
            avatar_b = await bili_api.get_bili_img(AVATAR_B)

            ui.chat_message(
                msg.get("text_a", "默认消息A"),
                avatar=avatar_a,
                name=NAME_A,
                text_html=True,
                sent=True,
                sanitize=False,
            )
            ui.chat_message(
                msg.get("text_b", "默认消息B"),
                avatar=avatar_b,
                name=NAME_B,
                text_html=True,
                sanitize=False,
            )

        if base_config.get("bool", "remote_text", True):
            await display_chat_messages()

        # 项目介绍
        ui.html(
            'A Project of <u><a href="https://nya-wsl.com" target="_blank">Nya-WSL</a></u>.',
            sanitize=False,
        )
        ui.html(
            'Powered by <u><a href="https://nicegui.io" target="_blank">NiceGUI</a></u> - <u><a href="https://github.com/xfgryujk/blivedm" target="_blank">blivedm</a></u>.',
            sanitize=False,
        )
        ui.label("Copyright © 2025 - 2026. All rights reserved. ")
        ui.separator()

        # 成员显示
        with ui.row(align_items="center"):
            with ui.column(align_items="center"):
                ui.label("程序开发").classes("text-blue")
                with ui.row(align_items="center"):
                    with ui.column(align_items="center"):
                        with ui.link(
                            target="https://space.bilibili.com/16748991", new_tab=True
                        ):
                            with ui.avatar():
                                ui.image(
                                    await bili_api.get_bili_img(
                                        "https://i0.hdslb.com/bfs/face/33c2e2be3e1dac286b6c13fedebd7d2b23b41df1.jpg"
                                    )
                                )
                        ui.badge("高橋はるき", outline=True)
                    with ui.column(align_items="center"):
                        with ui.link(
                            target="https://space.bilibili.com/8907402", new_tab=True
                        ):
                            with ui.avatar():
                                ui.image(
                                    await bili_api.get_bili_img(
                                        "https://i0.hdslb.com/bfs/face/ca91a679a9f14d2b38788671d63d0e311406e516.jpg"
                                    )
                                )
                        ui.badge("狐日泽", outline=True)
            ui.separator().props("vertical")
            with ui.column(align_items="center"):
                ui.label("特别鸣谢").classes("text-blue")
                with ui.row(align_items="center"):
                    with ui.column(align_items="center"):
                        with ui.link(
                            target="https://space.bilibili.com/3546729020394298/",
                            new_tab=True,
                        ):
                            with ui.avatar():
                                ui.image(
                                    await bili_api.get_bili_img(
                                        "https://i1.hdslb.com/bfs/face/1c90e9c3a52b13b898f4025a5282a394b09eeda0.jpg"
                                    )
                                )
                        ui.badge("千蚀vita", outline=True)
                    with ui.column(align_items="center"):
                        with ui.link(
                            target="https://space.bilibili.com/15104516/", new_tab=True
                        ):
                            with ui.avatar():
                                ui.image(
                                    await bili_api.get_bili_img(
                                        "https://i1.hdslb.com/bfs/face/316685ff90898018d3bb0eb7f0649db73e109e9b.jpg"
                                    )
                                )
                        ui.badge("青岚千柊", outline=True)
                    with ui.column(align_items="center"):
                        with ui.link(
                            target="https://space.bilibili.com/4015420/", new_tab=True
                        ):
                            with ui.avatar():
                                ui.image(
                                    await bili_api.get_bili_img(
                                        "https://i1.hdslb.com/bfs/face/29b2132e3371d0c9a90a21edf6a0ad87a122a831.jpg"
                                    )
                                )
                        ui.badge("天苍八重", outline=True)
                    with ui.column(align_items="center"):
                        with ui.link(
                            target="https://space.bilibili.com/11236317/", new_tab=True
                        ):
                            with ui.avatar():
                                ui.image(
                                    await bili_api.get_bili_img(
                                        "https://i0.hdslb.com/bfs/face/7b2a5c03e0caaa516dda9e238a82ebeef0e2f56d.jpg"
                                    )
                                )
                        ui.badge("冰蓝IceBlue", outline=True)

        ui.separator()

        # 联系我们
        ui.label(f"联系我们").classes("text-2xl")  # type: ignore[index]
        ui.link("GitHub Issues", "https://github.com/Nya-WSL/bili_travail/issues", True)
        ui.link("support@nya-wsl.com", "mailto:support@nya-wsl.com", True)
        ui.link("Nya-WSL服务与反馈群", "https://jq.qq.com/?_wv=1027&k=tSeB0sdy", True)
        ui.separator()
        ui.link("使用文档", "https://docs.travail.nya-wsl.com", True)
        # ui.html('关注<u><a href="https://space.bilibili.com/3546729020394298" target="_blank">千蚀vita</a></u>谢谢喵', sanitize=False).classes("text-2xl text-white")
