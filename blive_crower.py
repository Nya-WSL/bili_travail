import os
import time
import base64
import fnmatch
import asyncio
import aiofiles
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# GET方式请求B站图片数据并转换为base64
def get_bili_img(url):
    """
    :param url: 图片url
    """
    # 获取图片数据
    response = requests.get(url)
    response.raise_for_status()  # 检查请求是否成功
    # 将图片数据转换为 Base64
    bili_img = base64.b64encode(response.content).decode('utf-8')
    return f"data:image/jpeg;base64,{bili_img}"

async def get_bili_h5(room_id, h5_path = "data/saved_page.html", headless = True):
    get_bili_h5_status = True
    # 环境初始化
    cache_path = os.getcwd()+r"\\driver"                  # 定义下载路径
    options = Options()                                   # 配置 Selenium WebDriver
    if headless:
        options.add_argument("--headless")                # 以无头模式启动
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--mute-audio")                  # 静音音频

    if os.path.exists(os.getcwd()+r"\\driver\\msedgedriver\\win64") == False:                                 # 若webdriver不存在则下载并运行
        print("[INFO] 未找到 Edge WebDriver 环境...下载中...")
        os.system(f'selenium-manager.exe --cache-path "{cache_path}" --browser edge')
        print("[INFO] Edge WebDriver 环境下载完成...")
        dir_list = os.listdir(os.getcwd()+r"\\driver\\msedgedriver\\win64")
        pattern = '*'
        latest_dir = fnmatch.filter(dir_list, pattern)[-1]
        driver_path = os.getcwd()+r"\\driver\\msedgedriver\\win64\\"+latest_dir+r"\\msedgedriver.exe"         # 指定浏览器路径
        service = Service(driver_path)                                                                        # 使用 Service 指定已下载的路径
        driver = webdriver.Edge(service=service, options=options)                                             # 创建 Edge WebDriver 实例
        print("[INFO] 创建 Edge WebDriver 实例中...")
    else:
        try:
            dir_list = os.listdir(os.getcwd()+r"\\driver\\msedgedriver\\win64")                               # 尝试在文件夹内寻找是否存在msedgedriver.exe,若存在则直接运行
            pattern = '*'
            latest_dir = fnmatch.filter(dir_list, pattern)[-1]
            driver_path = os.getcwd()+r"\\driver\\msedgedriver\\win64\\"+latest_dir+r"\\msedgedriver.exe"
            service = Service(driver_path)
            driver = webdriver.Edge(service=service, options=options)
        except:
            print("[ERROR] Edge WebDriver 环境已损坏...重新下载中...")                                                    # 如抛出错误则重新下载
            os.system(f"selenium-manager.exe --cache-path {cache_path} --browser edge")
            driver = webdriver.Edge(service=service, options=options)
            print("[INFO] Edge WebDriver 环境下载完成...")
        else:
            print("[INFO] 创建 Edge WebDriver 实例中...")

    # 目标 URL
    url = f"https://live.bilibili.com/{room_id}"
    driver.get(url)


    # 模拟click进入gift-panel
    button_xpath = "/html/body/div[1]/main/div[1]/section[1]/div[2]/div[3]/div/div[2]/div[1]/div/div/div[3]/div[1]/div"

    try:
        # 捕捉按钮状态是否可用，不可用则等待10秒
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, button_xpath))
        )
        # 滚动到按钮可见并点击
        actions = ActionChains(driver)
        actions.move_to_element(button).perform()
        button.click()
        print("[INFO] 成功获取基础礼物数据...")

    except Exception:
        get_bili_h5_status = False

    if get_bili_h5_status:
        async with aiofiles.open(h5_path, "w+", encoding="utf-8") as file:
            await file.write(driver.page_source)

        # 模拟click进入PK
        button_xpath = "/html/body/div[1]/main/div[1]/section[1]/div[2]/div[3]/div/div[2]/div[1]/div/div/div[2]/div/div/div[2]/div/div[2]/div[1]"
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            actions = ActionChains(driver)
            actions.move_to_element(button).perform()
            button.click()
            print("[INFO] 成功获取PK礼物数据...")
            async with aiofiles.open(h5_path, "a", encoding="utf-8") as file:
                await file.write(driver.page_source)
        except Exception:
            print(f"[ERROR] 未能获取PK礼物数据...")


        # 模拟click进入粉丝团
        button_xpath = "/html/body/div[1]/main/div[1]/section[1]/div[2]/div[3]/div/div[2]/div[1]/div/div/div[2]/div/div/div[2]/div/div[3]/div[1]"
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            actions = ActionChains(driver)
            actions.move_to_element(button).perform()
            button.click()
            print("[INFO] 成功获取粉丝团专属礼物数据...")
            async with aiofiles.open(h5_path, "a", encoding="utf-8") as file:
                await file.write(driver.page_source)
        except Exception:
            print(f"[ERROR] 未能获取粉丝团专属礼物数据...")


        # 模拟click进入航海
        button_xpath = "/html/body/div[1]/main/div[1]/section[1]/div[2]/div[3]/div/div[2]/div[1]/div/div/div[2]/div/div/div[2]/div/div[4]/div[1]"
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            actions = ActionChains(driver)
            actions.move_to_element(button).perform()
            button.click()
            print("[INFO] 成功获取航海专属礼物数据...")
            async with aiofiles.open(h5_path, "a", encoding="utf-8") as file:
                await file.write(driver.page_source)
        except Exception:
            print(f"[ERROR] 未能获取航海专属礼物数据...")


        # 模拟click进入专属礼物
        button_xpath = "/html/body/div[1]/main/div[1]/section[1]/div[2]/div[3]/div/div[2]/div[1]/div/div/div[2]/div/div/div[2]/div/div[5]/div[1]"
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            actions = ActionChains(driver)
            actions.move_to_element(button).perform()
            button.click()
            print("[INFO] 成功获取直播间专属礼物数据...")
            async with aiofiles.open(h5_path, "a", encoding="utf-8") as file:
                await file.write(driver.page_source)
        except Exception:
            print(f"[ERROR] 未能获取直播间专属礼物数据...")
        print("[INFO] 等待缓存数据...")
        await asyncio.sleep(3)

        print("[INFO] 数据缓存完成!")

    # 关闭浏览器
    driver.quit()
    return get_bili_h5_status