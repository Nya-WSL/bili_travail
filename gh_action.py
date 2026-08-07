"""
GitHub Actions 构建入口。

用法（由 GitHub Actions 调用）：
    uv run python gh_action.py --variant nuitka        # 使用 Nuitka 编译 + 上传七牛/scp
    uv run python gh_action.py --variant pyinstaller   # 使用 PyInstaller 编译，不对外上传
    uv run python gh_action.py --variant pyinstaller --no-release  # 仅编译，跳过后续收尾
"""

import argparse
import os
import sys
import shutil
import subprocess
import requests
from pathlib import Path

ISS_RAW_URL = (
    "https://raw.githubusercontent.com/Nya-WSL/installer/main/bili_travail.iss"
)

# 强制 stdout/stderr 使用 UTF-8 编码，避免 Windows CI 默认的 cp1252 编码
# 无法打印中文字符而抛出 UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from build import build


# variant 对应的构建参数
#  - qiniu_status: 是否上传到七牛云
#  - manager:      包管理器，统一使用 uv
#  - nuitka:       是否使用 Nuitka 编译（否则用 PyInstaller）
#  - upload_status: 是否上传到服务器(scp)
VARIANT_CONFIG = {
    # 对外发布的正式包：Nuitka 编译，负责七牛云/scp 上传
    "nuitka": {
        "qiniu_status": "y",
        "manager": "uv",
        "nuitka": "y",
        "upload_status": "y",
        "release_name": "bili_travail_nuitka",
        "installer_name": "bili_travail_inst_nuitka",
    },
    # 由 Nuitka 工作流统一上传，PyInstaller 包不对外发布
    "pyinstaller": {
        "qiniu_status": "n",
        "manager": "uv",
        "nuitka": "n",
        "upload_status": "n",
        "release_name": "bili_travail_pyinstaller",
        "installer_name": "bili_travail_inst_pyinstaller",
    },
}

# GitHub Actions 环境变量（secrets）
SECRET_ENV_KEYS = {
    "ACCESS_KEY_ID": "ACCESS_KEY_ID",
    "ACCESS_KEY_SECRET": "ACCESS_KEY_SECRET",
    "APP_ID": "APP_ID",
    "QINIU_ACCESS_KEY": "qiniu_access_key",
    "QINIU_SECRET_KEY": "qiniu_secret_key",
    "BUCKET_NAME": "bucket_name",
    "SCP_URL": "scp_url",
}


def get_env(name: str, default: str = "") -> str:
    """读取环境变量，去掉首尾空白，未配置则返回默认值。"""
    return os.environ.get(name, default).strip()


def create_env_file() -> None:
    """
    根据环境变量(secrets)生成 build.py 依赖的 env.py。
    """
    keys = {py_key: get_env(env_key) for env_key, py_key in SECRET_ENV_KEYS.items()}
    # 版本号由 build.create_version() 回填，这里留空
    content = (
        "def get_key():\n"
        "    return {\n"
        f'        "ACCESS_KEY_ID": "{keys["ACCESS_KEY_ID"]}",\n'
        f'        "ACCESS_KEY_SECRET": "{keys["ACCESS_KEY_SECRET"]}",\n'
        f'        "APP_ID": {keys["APP_ID"]},\n'
        f'        "qiniu_access_key": "{keys["qiniu_access_key"]}",\n'
        f'        "qiniu_secret_key": "{keys["qiniu_secret_key"]}",\n'
        f'        "bucket_name": "{keys["bucket_name"]}",\n'
        f'        "scp_url": "{keys["scp_url"]}",\n'
        '        "version": ""\n'
        "    }\n"
    )
    with open("env.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("env.py 已根据环境变量生成")


def setup_ssh_key() -> None:
    """
    配置 SSH 私钥，使 build.py 中的 scp 上传无需手动输入密码。

    Windows OpenSSH 对私钥文件权限要求严格：只能当前用户可读，
    否则会拒绝使用（报 Permissions too open），导致 scp 退出码 255。
    这里显式用 icacls 收紧权限，避免该问题。
    """
    ssh_key = get_env("SSH_PRIVATE_KEY")
    if not ssh_key:
        print("未配置 SSH_PRIVATE_KEY，scp 上传将要求密码")
        return

    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    key_file = ssh_dir / "id_rsa"

    # 清理私钥内容，避免 OpenSSH 报 "invalid format"：
    #  - secret 里的换行可能被存成字面 "\n"，这里还原为真实换行
    #  - 去除首尾空白（空行/空格会破坏 PEM 完整性）
    #  - 强制统一为 LF 换行并保持 utf-8（Windows 下 write_text 默认 CRLF，
    #    OpenSSH 私钥要求 LF，CRLF 会导致解析失败）
    ssh_key = ssh_key.replace("\\n", "\n").strip()
    ssh_key = "\n".join(line.strip() for line in ssh_key.splitlines())
    key_file.write_bytes((ssh_key + "\n").encode("utf-8"))

    # Windows OpenSSH 私钥权限加固：仅当前用户可访问
    if os.name == "nt":
        subprocess.run(
            ["icacls", str(key_file), "/inheritance:r", "/grant:r", f"{os.environ.get('USERNAME', '')}:(R)"],
            check=False,
        )
    print(f"SSH key 已配置：{key_file}")


def build_inno_installer(version: str, variant: str) -> None:
    """
    使用 Inno Setup 生成安装包（windows-latest 预装 ISCC.exe）。

    version: 形如 2.40.073119（无 v 前缀）
    variant: nuitka / pyinstaller，决定安装包命名
    """
    cfg = VARIANT_CONFIG[variant]
    iscc = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if not Path(iscc).exists():
        raise FileNotFoundError(f"未找到 Inno Setup：{iscc}")

    # 从远端仓库拉取 Inno Setup 脚本
    try:
        resp = requests.get(ISS_RAW_URL, timeout=30)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        iss_content = resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"从 {ISS_RAW_URL} 下载 Inno Setup 脚本失败：{e}") from e

    # 注意：Inno Setup 中 [Files]/[Setup] 等节的相对路径是相对【脚本所在目录】
    # 解析的，而非当前工作目录。iss 内容里的路径（dist\start\*、static\logo.ico、
    # LICENSE）都以仓库根目录为基准，因此脚本必须放到仓库根目录下编译，
    # 不能放到临时目录（否则相对路径全部失效导致退出码 2）。
    iss_file = Path("bili_travail.iss")
    try:
        iss_file.write_text(iss_content, encoding="utf-8")
        print(f"Inno Setup 脚本已从远端仓库拉取：{len(iss_content)} bytes")

        subprocess.run([
            iscc, str(iss_file),
            f"/DMyAppVersion={version}",
            f"/DMyOutputBaseName={cfg['installer_name']}",
        ], check=True)
    finally:
        # 构建结束无论成败都清理脚本，避免污染仓库工作区
        iss_file.unlink(missing_ok=True)
    output = Path("dist", f"{cfg['installer_name']}.exe")
    if not output.exists():
        raise FileNotFoundError(f"安装包未生成：{output}")
    print(f"Inno Setup 安装包生成完成：{output}")


def run_build(variant: str) -> str:
    """
    执行完整的构建流程，返回完整版本号（形如 2.40.073119）。

    复用 build.py 的 build() / create_version() / compress() 完成：
      1. 生成 env.py 与 SSH key（供 scp 上传）
      2. 生成版本号并写入 version.json / env.py
      3. 按 variant 编译（Nuitka 或 PyInstaller）
      4. 拷贝资源、生成 zip 与 sha256
      5. 按需上传七牛云 / scp
    """
    cfg = VARIANT_CONFIG[variant]

    # 生成 build.py 依赖的 env.py 与 SSH key
    create_env_file()
    setup_ssh_key()

    # 调用 build.build() 完成编译、打包、上传
    build(
        qiniu_status=cfg["qiniu_status"],
        manager=cfg["manager"],
        nuitka=cfg["nuitka"],
        upload_status=cfg["upload_status"],
    )

    # 返回完整版本号（build() 内部已调用 create_version(True) 写入 version.json）
    with open("version.json", "r", encoding="utf-8") as f:
        import json
        version = json.load(f)["version"]
    print(f"版本号: {version}")
    return version


def prepare_release_artifacts(version: str, variant: str) -> None:
    """
    重命名 zip、生成 Inno Setup 安装包。
    """
    cfg = VARIANT_CONFIG[variant]
    dist = Path("dist")

    # 重命名 zip，避免 Nuitka / PyInstaller 产物在 Release 中冲突
    shutil.copy(dist / "bili_travail.zip", dist / f"{cfg['release_name']}.zip")
    print(f"{variant} zip 重命名为 {cfg['release_name']}.zip")

    # 生成安装包
    build_inno_installer(version, variant)


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub Actions 构建入口")
    parser.add_argument(
        "--variant",
        choices=list(VARIANT_CONFIG.keys()),
        required=True,
        help="构建方式：nuitka 或 pyinstaller",
    )
    parser.add_argument(
        "--no-release",
        action="store_true",
        help="仅编译与打包，跳过重命名 zip / 生成安装包等步骤",
    )
    args = parser.parse_args()

    version = run_build(args.variant)

    if not args.no_release:
        prepare_release_artifacts(version, args.variant)
    else:
        print("--no-release：跳过产物重命名与安装包生成")


if __name__ == "__main__":
    main()
