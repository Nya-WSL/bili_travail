import os
import re
import sys
import time
import json
import shutil
import zipfile
import datetime
import traceback
import subprocess

from pathlib import Path
from zoneinfo import ZoneInfo

# 版本号基于中国时区生成，避免 CI（默认 UTC）生成的时间与本地/预期不符
CN_TZ = ZoneInfo("Asia/Shanghai")

# 强制 stdout/stderr 使用 UTF-8 编码，避免 Windows CI 默认的 cp1252 编码
# 无法打印中文字符而抛出 UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from libs import hash_utils
from version import base_version
from qiniu import Auth, put_file, etag

# scp 上传参数：CI 上网络抖动较常见，允许重试
SCP_RETRY_TIMES = 3
SCP_TIMEOUT = 120 # 单次 scp 的超时时间（秒）

# 出现这些字样说明是认证/私钥问题，重试不会有不同结果，直接放弃
SCP_AUTH_ERROR_KEYWORDS = (
    "Permission denied",
    "no such identity",
    "Load key",
    "invalid format",
    "Too many authentication failures",
    "Host key verification failed",
)

def scp_upload(files: list[Path], target: str, key_file: Path, label: str) -> bool:
    '''
    用 scp 上传文件到服务器，失败只告警不中断构建（本地产物已生成）

    原先直接 subprocess.run(..., check=True) 且不捕获输出，失败时只能看到
    "returned non-zero exit status 255"，无法判断是私钥缺失、认证失败还是网络问题，
    这里把 scp 的 stdout/stderr 完整打印出来，并在上传前检查私钥是否存在。

    files: 待上传的本地文件
    target: 形如 user@host:/path 的目标地址
    key_file: SSH 私钥路径
    label: 日志中用于区分用途的名称
    '''
    if not target:
        print(f"未配置 {label} 的目标地址，跳过上传")
        return False

    if not key_file.exists():
        print(f"上传{label}失败：SSH 私钥不存在 {key_file}")
        print("请检查 GitHub Secrets 中该用途的私钥是否已配置（配置后由 gh_action.setup_ssh_key 写入）")
        return False

    # 用列表传参而不是拼接字符串，避免路径含空格时被 shell 拆错
    command = [
        "scp",
        "-o", "StrictHostKeyChecking=no", # 跳过 host key 确认，避免 CI 交互挂起
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "BatchMode=yes", # 非交互：认证失败立即报错，不等待输入密码
        "-o", "ConnectTimeout=15",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=4",
        "-i", str(key_file),
        *(str(file) for file in files),
        target,
    ]

    for attempt in range(1, SCP_RETRY_TIMES + 1):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=SCP_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            print(f"第 {attempt} 次上传{label}超时（超过 {SCP_TIMEOUT} 秒）")
        except OSError as e:
            # scp 不可用（如路径不存在）等环境问题，同样不能中断构建
            print(f"第 {attempt} 次上传{label}失败：{e}")
        else:
            if result.returncode == 0:
                print(f"已上传{label}到服务器：{target.rsplit(':', 1)[-1]}")
                return True
            print(f"第 {attempt} 次上传{label}失败（退出码 {result.returncode}）")
            if result.stdout.strip():
                print(f"scp 输出：{result.stdout.strip()}")
            if result.stderr.strip():
                print(f"scp 错误：{result.stderr.strip()}")
            if result.returncode == 255:
                print("退出码 255 一般是 SSH 层问题：私钥未授权、主机/端口/用户名有误或网络不可达")
                if any(keyword in result.stderr for keyword in SCP_AUTH_ERROR_KEYWORDS):
                    print("检测到认证/私钥问题，重试不会有不同结果，直接结束")
                    break

        if attempt < SCP_RETRY_TIMES:
            time.sleep(attempt * 3)

    print(f"上传{label}失败（不影响构建产物）")
    return False

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

def _verify_start_exe():
    """
    校验 Nuitka 是否真正产出了 dist/start.exe。

    Nuitka 编译失败时（例如缺少依赖、C 编译器问题）即使退出码为 0 也可能
    未生成可执行文件，这里给出明确错误提示，避免后续 shutil.copy 抛误导性的
    FileNotFoundError。
    """
    exe = Path("dist", "start.exe")
    if not exe.exists():
        raise FileNotFoundError(
            f"未找到 Nuitka 编译产物 {exe}，请检查上方 Nuitka 日志是否编译失败"
        )
    print(f"Nuitka 产物确认存在：{exe}")

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
    product_version = create_product_version()

    if nuitka == 'y':
        if Path("dist", "start").exists():
            shutil.rmtree(Path("dist", "start"))
    else:
        for directory in ['build', 'dist']:
            if Path(directory).exists():
                shutil.rmtree(Path(directory))

    if nuitka == 'y':
        os.makedirs(Path("dist", "start"), exist_ok=True)

    # --assume-yes-for-downloads：CI 为非交互环境，Nuitka 在 Windows --onefile 模式需要
    # Dependency Walker，此参数让它自动同意下载并缓存，避免交互式提示默认选 no 导致编译失败
    nuitka_download_flag = "--assume-yes-for-downloads"

    # 实现跨构建复用；本地若未设置则默认到 dist/nuitka-cache 启用缓存。
    nuitka_cache_dir = os.environ.get("NUITKA_CACHE_DIR", "dist/nuitka-cache")
    os.environ["NUITKA_CACHE_DIR"] = nuitka_cache_dir
    nuitka_perf_flags = f"--jobs={os.cpu_count()} --lto=no"

    # 不要给 Nuitka 传 --include-package=webview：Nuitka 内置的 pywebview 插件
    # （isAlwaysEnabled）会自行决定 webview.platforms.* 里哪些平台模块要纳入，若再用
    # --include-package 强制跟随整个 webview 包，就会与它“排除 android/cocoa/gtk/qt”的
    # 决定冲突并直接 FATAL（实测 4.0.8）：
    #   Conflict between user and plugin decision for module 'webview.platforms.android'
    # 因此只保留 --include-package-data=webview 拿 js/lib 等数据文件，Windows 平台模块
    # 由插件自动纳入（已验证包含 winforms/edgechromium/mshtml/cef）。

    if manager == "poetry":
        if nuitka == 'y':
            start_time = time.time()
            subprocess.run(f"poetry run python -m nuitka --onefile --msvc=latest {nuitka_perf_flags} {nuitka_download_flag} --windows-icon-from-ico=static/logo.ico {main_py} --include-package=nicegui --include-package-data=nicegui --include-package-data=webview --windows-console-mode=disable --windows-uac-admin --product-name=B站加班姬 --product-version={product_version} --copyright=Nya-WSL --output-dir=dist --output-filename=start.exe", check=True)
            end_time = time.time()
            print(f"Nuitka编译完成，耗时{end_time - start_time:.2f}秒")
            _verify_start_exe()
            shutil.copy(Path("dist", "start.exe"), Path("dist", "start", "start.exe"))
        else:
            subprocess.run(f"poetry run python package.py --name start --windowed --icon static/logo.ico {main_py}", check=True)
    elif manager == "uv":
        if nuitka == 'y':
            start_time = time.time()
            subprocess.run(f"uv run nuitka --onefile --msvc=latest {nuitka_perf_flags} {nuitka_download_flag} --windows-icon-from-ico=static/logo.ico {main_py} --include-package=nicegui --include-package-data=nicegui --include-package-data=webview --windows-console-mode=disable --product-name=B站加班姬 --product-version={product_version} --copyright=Nya-WSL --output-dir=dist --output-filename=start.exe", check=True)
            end_time = time.time()
            print(f"Nuitka编译完成，耗时{end_time - start_time:.2f}秒")
            _verify_start_exe()
            shutil.copy(Path("dist", "start.exe"), Path("dist", "start", "start.exe"))
        else:
            subprocess.run(f"uv run package.py --name start --windowed --icon static/logo.ico {main_py}", check=True)

    shutil.copy("check_runtime.ps1", Path("dist", "start", "check_runtime.ps1"))
    shutil.copy("LICENSE", Path("dist", "start", "LICENSE"))
    shutil.copytree("static", Path("dist", "start", "static"), dirs_exist_ok=True)
    shutil.copytree("locales", Path("dist", "start", "locales"), dirs_exist_ok=True)

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
        hash_utils.get_hash(file, save=True)

    if qiniu_status == 'y' or qiniu_status == '':
        upload(Path("dist", f"{version}.zip"), f"bili_travail/update/{version}.zip", "v1")
        upload(Path("dist", f"{version}.sha256"), f"bili_travail/update/{version}.sha256", "v1")

    if upload_status == 'y' or upload_status == '':
        # 更新包：scp 使用显式指定的 SSH 私钥（gh_action.setup_ssh_key 已写入 ~/.ssh/id_rsa），
        # 避免 Windows OpenSSH 因默认 key 找不到/权限问题导致退出码 255
        scp_upload(
            [Path("dist", "update.zip"), Path("dist", "update.sha256")],
            env_data.get("scp_url", ""),
            Path(Path.home(), ".ssh", "id_rsa"),
            "更新包",
        )

        # 构建完成后将 changelog.json 与 version.json 推送到 version_url（secrets）。
        # 使用独立的 SSH key（gh_action.setup_ssh_key 写入 ~/.ssh/version_id_rsa），
        # 与 scp_url 的 id_rsa 分离，避免密钥混用。
        scp_upload(
            [Path("changelog.json"), Path("version.json")],
            env_data.get("version_url", ""),
            Path(Path.home(), ".ssh", "version_id_rsa"),
            "版本信息",
        )

def create_version(full: bool = False):
    '''
    full: 是否返回完整版本号（包含基础版本号）
    '''
    version = datetime.datetime.now(CN_TZ).strftime("%m%d%H")
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


def create_product_version():
    '''
    生成 Nuitka 兼容的 product-version（4段，每段0-65535，无前导零）
    与 version 的 MMDDHH 对应：月*100+日 . 时
    '''
    now = datetime.datetime.now(CN_TZ)
    md = now.month * 100 + now.day
    full_version = f"{base_version}.{md}.{now.hour}"

    return full_version


def create_env_file(key_id, key_secret, app_id):
    version = create_version()

    access_key = input("请输入七牛云ACCESS_KEY：")
    secret_key = input("请输入七牛云SECRET_KEY：")
    scp_url = input("请输入SCP服务器URL（例：user@host:/path/），留空为无需上传：")
    version_url = input("请输入版本信息SCP服务器URL（例：user@host:/path/），留空为无需推送：")

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
        "version_url": "{version_url}",
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