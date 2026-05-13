import os
import re
import sys
import time
import json
import hash
import shutil
import zipfile
import datetime
import traceback

from pathlib import Path
from version import base_version
from qiniu import Auth, put_file, etag

def upload(localfile, file_path, version="v1"):
    '''
    localfile: 本地文件路径

    file_path: 上传到七牛云的文件路径

    version: 版本号，默认为"v1", v2需分片
    '''
    try:
        import env
        data = env.get_key()

        access_key = data["qiniu_access_key"]
        secret_key = data["qiniu_secret_key"]

        # 构建鉴权对象
        q = Auth(access_key, secret_key)

        # 要上传的空间
        bucket_name = data["bucket_name"]

        # 上传后保存的文件名
        key = file_path

        # 生成上传 Token，可以指定过期时间等
        token = q.upload_token(bucket_name, key, 3600)

        # 要上传文件的本地路径
        localfile = localfile

        ret, info = put_file(token, key, localfile, version=version)
        assert ret['key'] == key, f"返回key不匹配: {ret['key']} != {key}"
        assert ret['hash'] == etag(localfile), f"返回hash不匹配: {ret['hash']} != {etag(localfile)}"
        print("上传七牛云成功！")

    except Exception as e:
        print(f"上传七牛云失败: {e}")
        print(traceback.format_exc())

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

def build(qiniu_status: str ='y', manager: str = "uv", nuitka: str ='n', upload_status: str = 'y'):
    '''
    qiniu_status: 是否上传到七牛云，y=True, n=False, 留空为y

    manager: 要使用的包管理器，"poetry" 或 "uv", 默认为"uv"

    nuitka: 是否使用Nuitka编译，如果不使用Nuitka则使用pyinstaller，y=True, n=False, 留空为n

    upload_status: 是否上传到服务器，y=True, n=False, 留空为y
    '''

    import env
    env_data = env.get_key()

    main_py = "main.py"

    version = create_version(True)

    for directory in ['build', 'dist']:
        if Path(directory).exists():
            shutil.rmtree(Path(directory))

    if nuitka == 'y':
        os.makedirs(Path("dist", "start"), exist_ok=True)

    if manager == "poetry":
        if nuitka == 'y':
            start_time = time.time()
            os.system(f"poetry run python -m nuitka --onefile --windows-icon-from-ico=static/logo.ico {main_py} --include-package=nicegui --include-package-data=nicegui --windows-console-mode=disable --product-name=B站加班姬 --product-version={version} --copyright=Nya-WSL --output-dir=dist --output-filename=start.exe")
            end_time = time.time()
            print(f"Nuitka编译完成，耗时{end_time - start_time:.2f}秒")
            shutil.copy(Path("dist", "start.exe"), Path("dist", "start", "start.exe"))
        else:
            os.system(f"poetry run python package.py --name start --windowed --icon static/logo.ico {main_py}")
    elif manager == "uv":
        if nuitka == 'y':
            start_time = time.time()
            os.system(f"uv run nuitka --onefile --windows-icon-from-ico=static/logo.ico {main_py} --include-package=nicegui --include-package-data=nicegui --windows-console-mode=disable --product-name=B站加班姬 --product-version={version} --copyright=Nya-WSL --output-dir=dist --output-filename=start.exe")
            end_time = time.time()
            print(f"Nuitka编译完成，耗时{end_time - start_time:.2f}秒")
            shutil.copy(Path("dist", "start.exe"), Path("dist", "start", "start.exe"))
        else:
            os.system(f"uv run package.py --name start --windowed --icon static/logo.ico {main_py}")

    shutil.copy("check_runtime.ps1", Path("dist", "start", "check_runtime.ps1"))
    shutil.copytree("static", Path("dist", "start", "static"), dirs_exist_ok=True)

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
    if compress(Path("dist", "start"), Path("dist", f"bili_travail.zip")):
        shutil.copy(Path("dist", f"bili_travail.zip"), Path("dist", f"B站加班姬_{version}.zip"))
    shutil.copytree(Path("dist", "start"), Path("dist", "update"))
    if compress(Path("dist", "update"), Path("dist", f"{version}.zip"), True):
        shutil.copy(Path("dist", f"{version}.zip"), Path("dist", f"update.zip"))
    shutil.rmtree(Path("dist", "update"))

    for file in Path("dist").glob("*.zip"):
        hash.get_hash(file, save=True)

    if qiniu_status == 'y' or qiniu_status == '':
        upload(Path("dist", f"{version}.zip"), f"bili_travail/update/{version}.zip", "v1")
        upload(Path("dist", f"{version}.zip.sha256"), f"bili_travail/update/{version}.zip.sha256", "v1")

    if upload_status == 'y' or upload_status == '':
        if env_data.get("scp_url", ""):
            os.system(f'scp {Path("dist", "update.zip")} {Path("dist", "update.zip.sha256")} {env_data["scp_url"]}')
        else:
            print("未配置scp_url，无法上传到服务器")

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

    access_key = input("请输入七牛云ACCESS_KEY：")
    secret_key = input("请输入七牛云SECRET_KEY：")
    scp_url = input("请输入SCP服务器URL（例：user@host:/path/），留空为无需上传：")

    with open("env.py", "w+", encoding="utf-8") as f:
        f.write(
            f"""def get_key():
    return {{
        "ACCESS_KEY_ID": "{key_id}",
        "ACCESS_KEY_SECRET": "{key_secret}",
        "APP_ID": {app_id},
        "qiniu_access_key": "{access_key}",
        "qiniu_secret_key": "{secret_key}",
        "scp_url": "{scp_url}",
        "version": "{version}"
    }}"""
        )

def no_env(qiniu_status: str ='y', manager: str = "uv", nuitka: str ='n', upload_status: str = 'y'):
    key_id = input("请输入开放平台ACCESS_KEY_ID：")
    key_secret = input("请输入开放平台ACCESS_KEY_SECRET：")
    app_id = input("请输入开放平台APP_ID：")

    create_env_file(key_id, key_secret, app_id)

    build(qiniu_status.lower(), manager, nuitka.lower(), upload_status.lower())

def run():
    if sys.argv[-1] == "poetry":
        manager = "poetry"
    else:
        manager = "uv"

    manager_confirm = input(f"包管理器为{manager}，是否确认？(y/n), 默认为y：")

    if manager_confirm.lower() == 'n':
        print("请重新运行并输入正确的包管理器")
        sys.exit()

    nuitka_status = input("是否使用nuitka编译？(y/n), 默认为n：")

    if nuitka_status.lower() == 'y':
        print(f"将使用Nuitka编译，目录：{Path('dist', 'start')}")
        print("Nuitka编译较慢，请耐心等待...")
    else:
        print(f"将使用PyInstaller打包，目录：{Path('dist', 'start')}")

    qiniu_status = input("是否需要上传到七牛云？(y/n), 默认为y：")
    upload_status = input("是否需要上传到服务器？(y/n), 默认为y：")

    if os.path.exists("env.py"):
        status = input("检测到已有env.py文件，是否使用？(y/n), 默认为y：")
        if status.lower() == 'n':
            no_env(qiniu_status.lower(), manager, nuitka_status.lower(), upload_status.lower())
        elif status.lower() == 'y' or status.lower() == '':
            build(qiniu_status.lower(), manager, nuitka_status.lower(), upload_status.lower())
        else:
            print("参数错误")
            time.sleep(3)
            run()
    else:
        no_env(qiniu_status.lower(), manager, nuitka_status.lower(), upload_status.lower())

if __name__ == "__main__":
    run()