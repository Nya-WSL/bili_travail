import qrcode
import logging
import sys, requests, json, time

# LEVEL: DEBUG INFO WARNING ERROR CRITICAL
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename="bili_travail.log",
                    encoding="utf-8"
                    )

# 全局异常处理钩子
def handle_exception(exc_type, exc_value, exc_traceback):
    logging.error(
        "未知错误！",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

sys.excepthook = handle_exception

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


def login(loginInfo):
    response = requests.get(
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            },
        params = {"qrcode_key": loginInfo}
        )

    pollInfo = response.json()

    if pollInfo["data"]['code'] == 0:
        logging.info("登录成功")

    else:
        error = BiliPollError(pollInfo)
        if error:
            logging.error(error)
        else:
            logging.error("B站扫码出现未知错误")
        return error

    cookies = response.cookies

    for cookie in cookies:
        if cookie.name == "SESSDATA":
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            config["SESSDATA"] = cookie.value
            with open("config.json", "w+", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        else:
            return "未获取到SESSDATA"