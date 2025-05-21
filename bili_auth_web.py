import qrcode
from log import logger
import requests, json, time

class BiliPollError(Exception):
    """
    B站Web端扫码登录错误

    :param info: 扫码接口返回值
    """
    def __init__(self, info):
        self.info = info
        message = "扫码出现错误：" + info["data"]["message"]
        super().__init__(message)

def get_qrcode(path):
    """
    获取B站Web端扫码登录二维码

    :param path: 二维码保存路径，格式为: "path_时间戳.png"，例: "bili_qrcode_1743233445.png"
    :return: 扫码登录秘钥
    """
    try:
        loginInfo = requests.get(
            url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
            headers = {
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                }
            ).json()

        # 生成二维码
        img = qrcode.make(loginInfo['data']['url'])
        save_path = f"{path}_{int(time.time())}.png"
        img.save(save_path)
        return loginInfo["data"]["qrcode_key"], save_path
    except Exception as e:
        logger.exception(e)


def login(loginInfo):
    try:
        response = requests.get(
            url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
            headers = {
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                },
            params = {"qrcode_key": loginInfo}
            )

        pollInfo = response.json()

        if pollInfo["data"]['code'] == 0:
            logger.info("登录成功")

        else:
            error = BiliPollError(pollInfo)
            if error:
                logger.error(error)
            else:
                logger.exception("B站扫码出现未知错误")
            return error

        cookies = response.cookies

        for cookie in cookies:
            if cookie.name == "SESSDATA":
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                # 在写入SESSDATA前尝试清除原有的SESSDATA，防止覆盖失败
                if config.get("SESSDATA", "") != "":
                    config["SESSDATA"] = ""
                config["SESSDATA"] = cookie.value
                with open("config.json", "w+", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                return True
            else:
                return "未获取到SESSDATA"
    except Exception as e:
        logger.exception(e)