import os
import tomlkit
from pathlib import Path

class Config:
    def __init__(self) -> None:
        self.file = Path("config.toml")
        self.default_data = '''[general]
room_id = "" # 房间号
host = "127.0.0.1" # 监听地址
port = 65000 # 监听端口
auth_code = "" # 主播身份码
background_image = [
    "static/bg_vita.png"
] # 背景图片

[api]
server = "http://api.travail.nya-wsl.cn" # API地址

[open_live]
ACCESS_KEY_ID = "" # 开放平台 access_key_id
ACCESS_KEY_SECRET = "" # 开放平台 access_key_secred
APP_ID = 0 # 开放平台 项目ID

[color]
time_color = "#fcefe8" # 倒计时颜色
btn_color = "#fcefe8" # 按钮颜色
text_color = "#000000" # 文字颜色

[bool]
remote_text = true # about页面对话框内容是否从服务器获取
show_capture_gift_list = false # 是否启用收到礼物列表
show_capture_rank_list = false # 是否启用排行榜
short_list = false # 是否启用简洁模式
borderless_cd = false # 倒计时是否无边框
exit_timer = true # 是否启用倒计时结束后退出程序
check_update = true # 是否启用更新检查
check_sha256 = true # 是否启用更新包SHA256校验

[num]
short_time = 5 # 简洁模式滚动时间
capture_gift_list_number = 3 # 收到礼物列表显示数量
exit_time = 1800 # 倒计时结束后退出程序等待时间'''

        self.visited = set()  # 用于检测循环引用
        if not os.path.exists(self.file):
            self.default()

    def default(self):
        "初始化配置文件"
        with open("config.toml", "w+", encoding="utf-8") as f:
            tomlkit.dump(tomlkit.parse(self.default_data), f)

    def load(self):
        "加载配置文件"
        with open(self.file, "r", encoding="utf-8") as f:
            config = tomlkit.load(f)
        return config

    def save(self, data):
        "保存配置文件"
        with open("config.toml", "w+", encoding="utf-8") as f:
            if isinstance(data, tomlkit.TOMLDocument):
                tomlkit.dump(data, f)
            else:
                tomlkit.dump(tomlkit.parse(data), f)

    def get(self, table, value, default=None):
        """
        使用dict.get()获取配置文件中的值，不支持嵌套table

        params:
            table: 配置文件的table，如果为None则视为隐式table
            value: 配置文件中的值
            default: 值不存在时的默认值
        """
        data = self.load()

        if table is None:
            return data.get(value, default)
        else:
            return data.get(table, {}).get(value, default)

    def sync_config(self, config, example_config):
        "检查配置文件是否有缺失或多余项"
        example_config = tomlkit.parse(self.default_data)
        config = self.load()

        for example_table, example_data in example_config.items():
            if example_table not in config:
                # 如果键不存在，直接复制默认值
                config[example_table] = example_data

            for example_key, example_value in example_data.items():
                if example_key not in config[example_table]:
                    # 如果子键不存在,直接复制默认值
                    config[example_table][example_key] = example_value  # type: ignore[index]
                else:
                    # 检查配置文件缺失项
                    diff = example_data.keys() - config[example_table].keys()  # type: ignore[attr-defined]

                    for key in diff:
                        config[example_table][key] = example_config[example_table][key]  # type: ignore[index]

                    # 检查配置文件多余项
                    diff = config[example_table].keys() - example_data.keys()  # type: ignore[attr-defined]

                    for key in diff:
                        config[example_table].pop(key, None)  # type: ignore[attr-defined]

        self.save(config)