import os
import re
import time
import json
import shutil
import zipfile
import datetime

from pathlib import Path
from version import base_version

def compress(folder, output=None, parent=False):
    """
    folder: 要压缩的文件夹路径
    output: 输出的zip文件路径
    parent: 是否压缩父目录（默认为False，即只压缩文件夹内的内容）
    """
    folder = Path(folder)
    if not folder.exists() or not folder.is_dir():
        print(f"错误：'{folder}' 不是有效的文件夹")
        return False

    if output is None:
        output = f"{folder.name}.zip"

    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if parent: # 是否压缩父目录
            for root, dirs, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 计算相对路径（相对于要压缩的目录）
                    rel_path = os.path.relpath(file_path, folder.parent)
                    zipf.write(file_path, rel_path)
        else:
            # 遍历文件夹内的所有内容
            for item in folder.rglob('*'):
                if item.is_file():
                    # 计算相对路径（相对于要压缩的文件夹）
                    rel_path = item.relative_to(folder)
                    zipf.write(item, rel_path)

    print(f"成功压缩到 '{output}'")
    return True

def build():
    version = create_version(True)
    os.system("poetry run python package.py --name start --windowed --icon static/logo.ico main.py")
    shutil.copytree("static", Path("dist", "start", "static"))

    data = ["guard-level-3.png", "guard-level-2.png", "guard-level-1.png", "latiao.png"]

    for i in data:
        save_path = Path("dist", "start", "data")
        save_file = Path(save_path, i)
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        shutil.copy(Path("data", i), save_file)

    try:
        shutil.copy(Path("data", "bili_img.json"), Path("dist", "start", "data", "bili_img.json")) # 复制头像缓存
    except:
        print("没有找到头像缓存文件，跳过复制")

    # 创建版本压缩包
    if compress(Path("dist", "start"), Path("dist", f"bili_travail_{version}.zip")):
        shutil.copy(Path("dist", f"bili_travail_{version}.zip"), Path("dist", f"B站加班姬_{version}.zip"))
    shutil.copytree(Path("dist", "start"), Path("dist", "update"))
    if compress(Path("dist", "update"), Path("dist", f"{version}.zip"), True):
        shutil.copy(Path("dist", f"{version}.zip"), Path("dist", f"update.zip"))
    shutil.rmtree(Path("dist", "update"))

def create_version(full: bool = False):
    '''
    full: 是否返回完整版本号（包含基础版本号）
    '''
    version = datetime.datetime.now().strftime("%m%d%H")
    version_info = {}
    version_info["version"] = f"{base_version}.{version}"

    with open("version.json", "w", encoding="utf-8") as f:
        json.dump(version_info, f, ensure_ascii=False, indent=4)
    with open("env.py", 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用正则表达式替换版本
    pattern = r'"version": *"[^"]*"'
    replacement = f'"version": "{version}"'
    new_content = re.sub(pattern, replacement, content)

    with open("env.py", 'w', encoding='utf-8') as f:
        f.write(new_content)

    if full:
        return version_info["version"]
    else:
        return version


def create_env_file(key_id, key_secret, app_id):
    version = create_version()
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