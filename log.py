import requests

def version_log(current_version):
    """
    检查版本更新
    :param current_version: 当前程序版本
    """
    url = ["https://github.com/Nya-WSL/bili_travail/releases/download/version/version", "https://nya-wsl.com/bili_travail/version.txt"]
    try:
        latest_version = requests.get(url[0]).text
        if latest_version == "Not Found":
            raise ValueError("GitHub Repository is private")
    except ValueError:
        try:
            latest_version = requests.get(url[1])
            if latest_version.status_code == 200:
                latest_version = latest_version.text
            else:
                print("版本检查失败，请稍后再试...")
                latest_version = "Error"
        except:
            print("版本检查失败，请稍后再试...")
            latest_version = "Error"
    except:
        try:
            latest_version = requests.get(url[1])
            if latest_version.status_code == 200:
                latest_version = latest_version.text
            else:
                print("版本更新检查失败，请稍后再试...")
                latest_version = "Error"
        except:
            print("版本更新检查失败，请稍后再试...")
            latest_version = "Error"

    if current_version != latest_version:
        if latest_version != "Error":
            print(f"检查到可用更新！最新版本：v{latest_version}")
            print(f"下载最新版本：https://github.com/Nya-WSL/bili_travail/releases/tag/v{latest_version}")
            print("─────────────────────────────────────────────────────")
        else:
            print("─────────────────────────────────────────────────────")

def start_log(current_version):
    """
    A Project of Nya-WSL.
    """
    name = "B站加班姬"
    name_space_len = int((52 - (len(name.encode('gbk')))) / 2) * " "
    version_len = int(50 - (len(current_version))) * " "
    print(f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                    ┃
┃ {name_space_len}{name}{name_space_len}┃
┃{version_len}v{current_version} ┃
┃                                                    ┃
┠────────────────────────────────────────────────────┨
┃                                                    ┃
┃    Bili_travail is a program for Bilibili Live.    ┃
┃                A Project of Nya-WSL.               ┃
┃                                                    ┃
┃  For more information,visit: https://nya-wsl.com/  ┃
┃       Copyright © 2025. All rights reserved.       ┃
┠────────────────────────────────────────────────────┨
┃                         狐日泽&高橋はるき  2025/01 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
""")