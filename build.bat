@echo off
chcp 65001
setlocal enabledelayedexpansion

if exist env.py (
    echo 检测到env.py文件，是否使用已保存的密钥？
    set /p choice="请选择: "
    
    if /i "!choice!"=="Y" (
        echo 使用已保存的密钥
        poetry run python build.py --name start --windowed --icon static/logo.ico main.py
    ) else (
        echo 请手动输入密钥
        set /p key_id="ACCESS_KEY_ID: "
        set /p key_secret="ACCESS_KEY_SECRET: "
        set /p app_id="APP_ID: "
        
        poetry run python build.py --name start --windowed --icon static/logo.ico main.py --access_key_id !key_id! --access_key_secret !key_secret! --app_id !app_id!
    )
) else (
    echo 未找到env.py文件，请手动输入密钥
    set /p key_id="ACCESS_KEY_ID: "
    set /p key_secret="ACCESS_KEY_SECRET: "
    set /p app_id="APP_ID: "
    
    poetry run python build.py --name start --windowed --icon static/logo.ico main.py --access_key_id !key_id! --access_key_secret !key_secret! --app_id !app_id!
)

endlocal