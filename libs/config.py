import os
import tomlkit
from pathlib import Path
from tomlkit import document, table, array

def _build_default_config() -> tomlkit.TOMLDocument:
    """使用 tomlkit API 构建默认配置，避免硬编码 TOML 字符串"""
    doc = document()

    general = table()
    general.add("room_id", "")
    general["room_id"].comment("房间号")
    general.add("host", "127.0.0.1")
    general["host"].comment("监听地址")
    general.add("port", 65000)
    general["port"].comment("监听端口")
    general.add("auth_code", "")
    general["auth_code"].comment("主播身份码")
    bg = array()
    bg.append("static/bg_vita.png")
    general.add("background_image", bg)
    general["background_image"].comment("背景图片")
    doc.add("general", general)

    api = table()
    api.add("server", "http://api.travail.nya-wsl.cn")
    api["server"].comment("API地址")
    doc.add("api", api)

    open_live = table()
    open_live.add("ACCESS_KEY_ID", "")
    open_live["ACCESS_KEY_ID"].comment("开放平台 access_key_id")
    open_live.add("ACCESS_KEY_SECRET", "")
    open_live["ACCESS_KEY_SECRET"].comment("开放平台 access_key_secred")
    open_live.add("APP_ID", 0)
    open_live["APP_ID"].comment("开放平台 项目ID")
    doc.add("open_live", open_live)

    color = table()
    color.add("time_color", "#fcefe8")
    color["time_color"].comment("倒计时颜色")
    color.add("btn_color", "#fcefe8")
    color["btn_color"].comment("按钮颜色")
    color.add("text_color", "#000000")
    color["text_color"].comment("文字颜色")
    doc.add("color", color)

    bool_tbl = table()
    bool_tbl.add("remote_text", True)
    bool_tbl["remote_text"].comment("about页面对话框内容是否从服务器获取")
    bool_tbl.add("show_capture_gift_list", False)
    bool_tbl["show_capture_gift_list"].comment("是否启用收到礼物列表")
    bool_tbl.add("show_capture_rank_list", False)
    bool_tbl["show_capture_rank_list"].comment("是否启用排行榜")
    bool_tbl.add("short_list", False)
    bool_tbl["short_list"].comment("是否启用简洁模式")
    bool_tbl.add("borderless_cd", False)
    bool_tbl["borderless_cd"].comment("倒计时是否无边框")
    bool_tbl.add("exit_timer", True)
    bool_tbl["exit_timer"].comment("是否启用倒计时结束后退出程序")
    bool_tbl.add("check_update", True)
    bool_tbl["check_update"].comment("是否启用更新检查")
    bool_tbl.add("check_sha256", True)
    bool_tbl["check_sha256"].comment("是否启用更新包SHA256校验")
    doc.add("bool", bool_tbl)

    num = table()
    num.add("short_time", 5)
    num["short_time"].comment("简洁模式滚动时间")
    num.add("capture_gift_list_number", 3)
    num["capture_gift_list_number"].comment("收到礼物列表显示数量")
    num.add("exit_time", 1800)
    num["exit_time"].comment("倒计时结束后退出程序等待时间")
    doc.add("num", num)

    return doc


class Config:
    def __init__(self) -> None:
        self.file = Path("config.toml")
        self.default_data = _build_default_config()

        self.visited = set()  # 用于检测循环引用
        if not os.path.exists(self.file):
            self.default()

    def default(self):
        "初始化配置文件"
        with open("config.toml", "w+", encoding="utf-8") as f:
            tomlkit.dump(self.default_data, f)

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

    def sync_config(self):
        "检查配置文件是否有缺失或多余项"
        example_config = self.default_data
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