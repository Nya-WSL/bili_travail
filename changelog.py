from nicegui import ui

def changelog():
    with ui.card(align_items="center").classes("w-full").style("box-shadow: None; left: -5%"):
        with ui.row():
            ui.button("返回主页", on_click=lambda: ui.navigate.to('/')).style("right: -15%")
            ui.button("GitHub", on_click=lambda: ui.navigate.to('https://github.com/Nya-WSL/bili_travail', new_tab=True)).style("right: -15%")
        with ui.timeline(side='right', layout='comfortable'):
            ui.timeline_entry('B站加班姬更新日志', heading=True)
            with ui.timeline_entry(title='Release of 0.23.8-alpha', subtitle='2025-03-23', avatar='static/logo.ico'):
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