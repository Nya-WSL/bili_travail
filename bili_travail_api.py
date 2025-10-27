'''
该模块为服务器模块，用于接收加班姬发送的调试数据
'''

import os
import json
import uvicorn
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, status

def bytes_to_kb(bytes_size: int) -> float:
    """将字节大小转换为 KB"""
    return round(bytes_size / 1024, 2)  # 保留两位小数

app = FastAPI()

example_config = {
    "host": "0.0.0.0",
    "port": 65200,
    "save_path": os.getcwd() + "/logs/"
}

if not os.path.exists("config.json"):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(example_config, f, ensure_ascii=False, indent=4)

# 加载配置文件
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# 检查配置文件缺失项
diff = example_config.keys() - config.keys()

for key in diff:
    config[key] = example_config[key]

# 检查配置文件多余项
diff = config.keys() - example_config.keys()

for key in diff:
    config.pop(key, None)

with open("config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=4)

@app.post("/log/{room_id}", status_code=status.HTTP_201_CREATED)
async def hook(room_id, file: UploadFile = File(...)):
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        save_path = config.get("save_path", os.getcwd() + "/logs/")

        # 读取文件内容
        contents = await file.read()

        if not contents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不允许上传空文件")

        # 创建房间目录
        room_dir = Path(save_path) / room_id
        room_dir.mkdir(parents=True, exist_ok=True)

        file_path = room_dir / file.filename

        # 处理文件
        with open(file_path, "wb") as f:
            f.write(contents)

        return {
                "status": status.HTTP_201_CREATED,
                "message": "文件上传成功",
                "path": str(file_path),
                "room_id": room_id,
                "filename": file.filename,
                "size": f"{bytes_to_kb(len(contents))} KB"
            }

    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

if __name__ == "__main__":
    with open("config.json", "r") as f:
        config = json.load(f)

    uvicorn.run(
        app=app,
        host=config.get("host", "0.0.0.0"),
        port=config.get("port", 65200)
    )