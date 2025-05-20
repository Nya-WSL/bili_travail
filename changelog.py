from nicegui import ui
import json

def changelog():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    with ui.card(align_items="center").classes("w-full").style("box-shadow: None; left: -5%"):
        with ui.row():
            ui.button("返回主页", on_click=lambda: ui.navigate.to('/'), color=config["btn_color"]).style("right: -15%")
            ui.button("GitHub", on_click=lambda: ui.navigate.to('https://github.com/Nya-WSL/bili_travail', new_tab=True), color=config["btn_color"]).style("right: -15%")
        with ui.timeline(side='right', layout='comfortable', color="btn"):
            # ui.timeline_entry('更新日志', heading=True)
            with ui.timeline_entry(title='Release of 0.26.1-dev', subtitle='2025-05-21', avatar='static/logo.ico'):
                ui.label('● 修复当每次启动程序都会将之前日志归档的问题')
            with ui.timeline_entry(title='Release of 0.26.0-alpha', subtitle='2025-05-20'):
                with ui.column().classes('gap-3'):
                    ui.label('● 移除过时的配置和代码')
                    ui.label('● 移除B站直播间爬虫')
                    ui.label('● 移除tv端登录接口代码')
                    ui.label('●  更新预设礼物数据（注：盲盒未更新）')
                    ui.label('● 将所有模块的日志合并为同一个handler')
                    ui.label('● 同时使用logging和loguru记录更详细的日志，logging仅记录未知错误和DEBUG')
                    ui.label('● 现在日志会按照日期保存')
                    ui.label('● 现在会比对配置文件和默认配置并自动更新差异')
            with ui.timeline_entry(title='Release of 0.25.5-alpha', subtitle='2025-05-09'):
                ui.label('● 尝试修复查看礼物统计无法打开新标签页的问题，现在查看礼物统计是一个按钮而不是一个超链接')
            with ui.timeline_entry(title='Release of 0.25.4-alpha', subtitle='2025-05-09'):
                ui.label('● OBS投喂记录支持自定义字体颜色')
            with ui.timeline_entry(title='Release of 0.25.3-alpha', subtitle='2025-04-22'):
                with ui.column().classes('gap-3'):
                    ui.label('● 更新NiceGUI至v2.15.0')
                    ui.label('● 支持自定义按钮、开关和更新日志的时间线颜色（需重启生效）')
            with ui.timeline_entry(title='Release of 0.25.2-alpha', subtitle='2025-04-10'):
                with ui.column().classes('gap-3'):
                    ui.label('● 初始化直播间接口现在要求更严格的鉴权，更换新接口修复该问题')
                    ui.label('● 新增实验性的日志轮转功能，日志仅保存一周，轮转时间为周五')
            with ui.timeline_entry(title='Release of 0.25.1-alpha', subtitle='2025-03-29'):
                with ui.column().classes('gap-3'):
                    ui.label('● 扫码登录移除tv端接口，新增web端接口，减少被风控的概率')
                    ui.label('● 新增获取浏览器登录状态功能，仅支持firefox，可以使用浏览器已登录的B站账号登录')
                    ui.label('● 优化登录逻辑，可以自行选择扫码登录或获取浏览器登录状态')
            with ui.timeline_entry(title='Release of 0.25.0-alpha', subtitle='2025-03-26'):
                ui.label('● 新增礼物统计功能，会自动统计程序运行时收到的所有礼物（盲盒只统计具体礼物；需连接弹幕服务器；在程序启动时将会备份后清空数据）')
            with ui.timeline_entry(title='Release of 0.24.0-alpha', subtitle='2025-03-23'):
                ui.label('● 新增登录至B站功能，无需手动获取SESSDATA')
            with ui.timeline_entry(title='Release of 0.23.8-alpha', subtitle='2025-03-23'):
                ui.label('● OBS投喂记录上限可自定义（自定义需修改配置文件，假设为x)，超过x条时只会显示最后x条，不再删除记录')
            with ui.timeline_entry(title='Release of 0.23.7-alpha', subtitle='2025-03-22'):
                ui.label('● OBS投喂记录新增3条的上限，超过时会覆盖第一条记录并写入日志，防止过长的记录会导致收到礼物时卡顿')
            with ui.timeline_entry(title='Release of 0.23.6-alpha', subtitle='2025-03-22'):
                with ui.column().classes('gap-3'):
                    ui.label('● 新增错误日志')
                    ui.label('● 进入房间、醒目留言、触发心跳、成功连接房间将会写入日志')
                    ui.label('● 调整界面预览按钮位置')
            with ui.timeline_entry(title='Release of 0.23.5-alpha', subtitle='2025-03-20'):
                with ui.column().classes('gap-3'):
                    ui.label('● OBS投喂记录框增加高度和宽度')
                    ui.label('● OBS投喂记录增加字体大小并加粗，现在不再显示礼物名字和时间')
                    ui.label('● 修复OBS投喂记录不会换行的问题')
                    ui.label('● OBS投喂记录备份将会保存至data/history，不再是data')
                    ui.label('● 修复当程序启动后，如果capture页面从未被访问过时，收到礼物会导致更新OBS投喂记录报错的问题')
            with ui.timeline_entry(title='Release of 0.23.4-alpha', subtitle='2025-03-19'):
                ui.label('● OBS投喂记录现在刷新页面后不再清空（刷新后不会显示，需收到一次存在规则的礼物），每次启动程序时会在备份后删除记录')
            with ui.timeline_entry(title='Release of 0.23.3-alpha', subtitle='2025-03-19'):
                with ui.column().classes('gap-3'):
                    ui.label('● 修复示例配置文件缺少部分配置项的问题')
                    ui.label('● 修复初始化盲盒数据时会导致收到的礼物名字被替换的问题')
                    ui.label('● capture页面新增可开关的收到礼物列表（当capture页面刷新时将丢失记录）')
                    ui.label('● 心动盲盒数据适配B站新改动')
                    ui.label('● 重写更新日志布局')
                    ui.label('● 更新nicegui至v2.13.0')
            with ui.timeline_entry(title='Release of 0.23.2-alpha', subtitle='2025-03-18'):
                with ui.column().classes('gap-3'):
                    ui.label(r"盲盒数据结构从 '盲盒: {礼物: img}' 改为 '盲盒: [礼物列表]'")
                    ui.label('● 当无法联网获取礼物数据时内置图片数据不再自动解析盲盒，礼物规则数据不受影响')
            with ui.timeline_entry(title='Release of 0.23.1-alpha', subtitle='2025-03-13'):
                ui.label('● 赌⭕统计功能新增清零按钮')
            with ui.timeline_entry(title='Release of 0.23.0-alpha', subtitle='2025-03-12'):
                with ui.column().classes('gap-3'):
                    ui.label('● 新增赌⭕统计功能')
                    ui.label('● 修复系统语言非utf-8编码可能会导致更新脚本报错的问题')
                    ui.label('● 更新预设礼物数据和盲盒数据')
                    ui.label('● 心动盲盒礼物数据适配B站新改动')
            with ui.timeline_entry(title='Release of 0.22.2-alpha', subtitle='2025-03-08'):
                ui.label('● 新增更新日志，仅在更新后第一次启动时自动显示')
            with ui.timeline_entry(title='Release of 0.22.1-alpha', subtitle='2025-03-08'):
                with ui.column().classes('gap-3'):
                    ui.label('● 修复因为获取B站图片函数无法解析本地图片导致报错从而无法触发舰队礼物规则的问题')
                    ui.label('● 适配1080p + 125%缩放：收到礼物列表高度减半，调整窗体大小，调整about按钮位置')
                    ui.label('● 修复程序初始化因意外情况中止导致的数据损坏，会在继承倒计时数据时报错的问题')
                    ui.label('● 尝试修复未设定的盲盒也会触发收到礼物列表的问题（待观察）')
            with ui.timeline_entry(title='Release of 0.22.0-alpha', subtitle='2025-03-07'):
                with ui.column().classes('gap-3'):
                    ui.label('● 修改内置更新可能会导致依赖库未更新的问题')
                    ui.label('● 修复内置更新启动新进程后不会关闭cmd窗口的问题')
                    ui.label('● 手动更新礼物数据时不再会覆盖已设定的时长和统计数据')
                    ui.label('● 修改检查更新通知')
            with ui.timeline_entry(title='Release of 0.21.1-alpha', subtitle='2025-03-07'):
                with ui.column().classes('gap-3'):
                    ui.label('● 新增内置更新功能')
                    ui.label('● 现在打包时不再会自动复制本地盲盒图片')
                    ui.label('● 更新礼物数据不再更新测试礼物')
                    ui.label('● 暂时禁用海外更新源')
            with ui.timeline_entry(title='Release of 0.21.0-alpha', subtitle='2025-03-05'):
                with ui.column().classes('gap-3'):
                    ui.label('● 获取礼物数据新增从B站API获取')
                    ui.label('● 移除storage初始化临时修复代码')
                    ui.label('● 更新nicegui至v2.12.1')
            with ui.timeline_entry(title='Release of 0.20.1-alpha', subtitle='2025-02-14'):
                ui.label('● 修复about页面因为无法访问海外服务器返回500错误的问题')
            with ui.timeline_entry(title='Release of 0.20.0-alpha', subtitle='2025-02-13'):
                with ui.column().classes('gap-3'):
                    ui.label('● 爬虫适配B站情人节新版礼物列表（移除pk礼物')
                    ui.label('● 补全盲盒数据')
                    ui.label('● 现在礼物设置可以直接指定盲盒或特定的盲盒礼物，特定礼物规则会覆盖盲盒规则')
            with ui.timeline_entry(title='Release of 0.19.1-alpha', subtitle='2025-02-13'):
                with ui.column().classes('gap-3'):
                    ui.label('● 手动更新礼物数据时会更新预定义的盲盒数据')
                    ui.label('● 修复中国服务器检查更新返回值错误的问题')
                    ui.label('● 修复手动更新礼物数据时不会更新投喂挑战数据的问题')
                    ui.label('● 修复重置计数二次确认后不会关闭弹窗的问题')
            ui.timeline_entry('● ......', title='0.9.1-alpha ~ 0.19.0-alpha', subtitle='2025')
            ui.timeline_entry('● Initial commit', title='Release of 0.9.0-alpha', subtitle='2025-01-19')