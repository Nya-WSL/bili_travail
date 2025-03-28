import qrcode
import logging
import asyncio
import time, sys, requests, aiohttp, json, urllib, hashlib

def tvsign(params, appkey='4409e2ce8ffd12b8', appsec='59b43e04ad6965f34319062b478f83dd'):
    '为请求参数进行 api 签名'
    params.update({'appkey': appkey})
    params = dict(sorted(params.items())) # 重排序参数 key
    query = urllib.parse.urlencode(params) # 序列化参数
    sign = hashlib.md5((query+appsec).encode()).hexdigest() # 计算 api 签名
    params.update({'sign':sign})
    return params

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

def get_qrcode():
    # 获取二维码
    loginInfo = requests.post('https://passport.bilibili.com/x/passport-tv-login/qrcode/auth_code',params=tvsign({
        'local_id':'0',
        'ts':int(time.time())
    }),headers={
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }).json()

    # 生成二维码
    # qrcode_terminal.draw(loginInfo['data']['url'])
    img = qrcode.make(loginInfo['data']['url'])
    img.save("bili_qrcode.png")
    return loginInfo

async def login(loginInfo):
    number = 0
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://passport.bilibili.com/x/passport-tv-login/qrcode/poll',params=tvsign({
                'auth_code':loginInfo['data']['auth_code'],
                'local_id':'0',
                'ts':int(time.time())
            }),headers={
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            }) as response:

                pollInfo = await response.json()

                if pollInfo['code'] == 0:
                    loginData = pollInfo['data']
                    logging.info(f"登录成功, 有效期至{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + int(loginData['expires_in'])))}")
                    break

                elif pollInfo['code'] == -3:
                    logging.error('API校验密匙错误')
                    return False, Exception('API校验密匙错误')

                elif pollInfo['code'] == -400:
                    logging.error('请求错误')
                    return False, Exception('请求错误')

                elif pollInfo['code'] == 86038:
                    logging.error('二维码已失效')
                    return False, Exception('二维码已失效')

                elif pollInfo['code'] == 86039:
                    logging.error('未扫码')
                    await asyncio.sleep(3)
                    if number >= 10:
                        logging.error('登录超时')
                        return False, Exception('登录超时')
                    number += 1

                else:
                    logging.error('未知错误')
                    return False, Exception('未知错误')

    for info in loginData['cookie_info']["cookies"]:
        if info["name"] == "SESSDATA":
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            config["SESSDATA"] = info["value"]
            with open("config.json", "w+", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True, loginData