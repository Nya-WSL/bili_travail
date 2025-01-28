import requests

# 检查更新
def version_log(current_version):
    """
    检查版本更新
    :param current_version: 当前程序版本
    """
    url = ["https://github.com/Nya-WSL/bili_travail/releases/download/version/version", "https://nya-wsl.com/bili_travail/version.txt"]
    try:
        latest_version = requests.get(url[0]).text.replace("\n", "") # 优先从GitHub Release获取版本信息
        if latest_version == "Not Found": # GitHub的返回内容为"Not Found"，一般意味着版本文件不存在或仓库无访问权限
            raise ValueError("From github to get version info was error") # 抛出错误
    except:
        try:
            latest_version = requests.get(url[1]) # 从Nya-WSL服务器获取版本信息
            if latest_version.status_code == 200: # 服务器请求返回值
                latest_version = latest_version.text.replace("\n", "") # 服务器返回内容
            else:
                print("无法连接至服务器，版本更新检查失败...")
                print("─────────────────────────────────────────────────────")
                latest_version = "Error"
                return latest_version
        except:
            print("无法连接至服务器，版本更新检查失败...")
            print("─────────────────────────────────────────────────────")
            latest_version = "Error" # 如果请求均失败版本信息设为"Error"
            return latest_version

    if current_version != latest_version:
        if latest_version != "Error":
            print(f"检查到可用更新！最新版本：v{latest_version}")
            print(f"下载最新版本：https://github.com/Nya-WSL/bili_travail/releases/tag/v{latest_version}")
            print("─────────────────────────────────────────────────────")
        else:
            print("已是最新版本！")
            print("─────────────────────────────────────────────────────")
    else:
            print("已是最新版本！")
            print("─────────────────────────────────────────────────────")

    return latest_version

# 项目信息
def start_log(current_version):
    """
    A Project of Nya-WSL.
    """
    name = "B站加班姬"
    name_space_len = int((52 - (len(name.encode('gbk')))) / 2) * " " # 计算名称行空格
    version_len = int(50 - (len(current_version))) * " " # 计算版本行空格
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