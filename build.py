import os
import time
import json
import shutil
import datetime

from main import base_version

def build():
    os.system("poetry run python package.py --name start --windowed --icon static/logo.ico main.py")
    shutil.copytree("static", os.path.join("dist", "start", "static"))

    data = ["guard-level-3.png", "guard-level-2.png", "guard-level-1.png", "latiao.png"]

    for i in data:
        save_path = os.path.join("dist", "start", "data")
        save_file = os.path.join(save_path, i)
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        shutil.copy(os.path.join("data", i), save_file)

def create_env_file(key_id, key_secret, app_id):
    version = datetime.datetime.now().strftime("%y%m%d%H%M")
    with open("env.py", "w+", encoding="utf-8") as f:
        f.write(
            f"""def get_key():
    return {{
        "ACCESS_KEY_ID": "{key_id}",
        "ACCESS_KEY_SECRET": "{key_secret}",
        "APP_ID": {app_id},
        "version": {version}
    }}"""
        )

    version_info = {}
    version_info["version"] = f"{base_version}-{version}"

    with open("version.json", "w", encoding="utf-8") as f:
        json.dump(version_info, f, ensure_ascii=False, indent=4)

def no_env():
    key_id = input("请输入开放平台ACCESS_KEY_ID：")
    key_secret = input("请输入开放平台ACCESS_KEY_SECRET：")
    app_id = input("请输入开放平台APP_ID：")

    create_env_file(key_id, key_secret, app_id)

    build()

def run():
    if os.path.exists("env.py"):
        status = input("检测到已有env.py文件，是否使用？(y/n)：")
        if status.lower() == 'n':
            no_env()
        elif status.lower() == 'y':
            build()
        else:
            print("参数错误")
            time.sleep(3)
            run()
    else:
        no_env()

if __name__ == "__main__":
    run()