'''
该模块为服务器模块，用于接收加班姬发送的数据
'''

import os
import uvicorn
import aiohttp
import orjson
import traceback

from typing import List, Literal
from minio import Minio
from pathlib import Path
from pydantic import BaseModel
from aiohttp.resolver import AsyncResolver
from fastapi import FastAPI, UploadFile, File, HTTPException, status

class GiftIdsRequest(BaseModel):
    gift_ids: List[int]
    version: str | None

class StatRequest(BaseModel):
    room_id: int
    uid: int
    version: str
    time: str

class UpdateRequest(BaseModel):
    version: str

def bytes_to_kb(bytes_size: int) -> float:
    """将字节大小转换为 KB"""
    return round(bytes_size / 1024, 2)  # 保留两位小数

app = FastAPI()

blind_box = {}

example_config = {
    "host": "0.0.0.0",
    "port": 65200,
    "save_path": os.getcwd() + "/logs/",
    "SESSDATA": "",
    "endpoint": "s3.hi168.com",
    "bucket_name": "",
    "access_key": "",
    "secret_key": "",
    "region": "us-east-1"
}

def init_config():
    if not os.path.exists("config.json"):
        with open("config.json", "wb") as f:
            f.write(orjson.dumps(example_config, option=orjson.OPT_INDENT_2))

    # 加载配置文件
    with open("config.json", "rb") as f:
        config = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

    # 检查配置文件缺失项
    diff = example_config.keys() - config.keys()

    for key in diff:
        config[key] = example_config[key]

    # 检查配置文件多余项
    diff = config.keys() - example_config.keys()

    for key in diff:
        config.pop(key, None)

    with open("config.json", "wb") as f:
        f.write(orjson.dumps(config, option=orjson.OPT_INDENT_2))

async def get_blind_box(gift_ids: list, version: str | None) -> dict:
    """
    获取盲盒礼物列表

    :param gift_ids (_list_) : 盲盒礼物ID
    :param version (str) : 客户端版本号
    :return dict: 盲盒礼物列表
    """

    with open("config.json", "rb") as f:
        config = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

    blind_box = {}

    resolver = AsyncResolver(nameservers=["8.8.8.8", "114.114.114.114"])
    connector = aiohttp.TCPConnector(resolver=resolver)

    async with aiohttp.ClientSession(connector=connector) as session:
        for gift_id in gift_ids:
            url = "https://api.live.bilibili.com/xlive/general-interface/v1/blindFirstWin/getInfo"
            params = {
                "gift_id": gift_id
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0",
                "Cookie": f"SESSDATA={config.get('SESSDATA', '')}"
            }

            try:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['code'] == 0:
                            for gift in data['data']['gifts']:
                                if data['data']['blind_gift_name'] not in blind_box:
                                    if version is not None and version > "1.38.041001" and version != "1.38.0":
                                        blind_box[data['data']['blind_gift_name']] = {"price": data['data']['blind_price'], "gifts": []}
                                    else:
                                        blind_box[data['data']['blind_gift_name']] = []
                                if version is not None and version > "1.38.041001" and version != "1.38.0":
                                    blind_box[data['data']['blind_gift_name']]['gifts'].append({
                                        'gift': gift['gift_name'], 
                                        "gift_img": gift['gift_img']
                                    })
                                else:
                                    blind_box[data['data']['blind_gift_name']].append({
                                        'gift': gift['gift_name'], 
                                        "gift_img": gift['gift_img']
                                    })
                        else:
                            print(f"获取盲盒礼物列表({gift_id})失败: {data['message']}")
                    else:
                        print(f"请求盲盒礼物列表({gift_id})失败: {response.status}")

            except aiohttp.ClientError as e:
                print(f"网络请求失败({gift_id}): {traceback.format_exc()}")
                continue
            except Exception as e:
                print(f"获取盲盒礼物列表({gift_id})失败: {traceback.format_exc()}")
                continue

    return blind_box

@app.post("/gift/get_blind_boxes", status_code=status.HTTP_200_OK)
async def index(request: GiftIdsRequest):  # pyright: ignore[reportRedeclaration]
    try:
        blind_box = await get_blind_box(request.gift_ids, request.version)

        if blind_box == {}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="盲盒数据为空")

        return blind_box

    except HTTPException as he:
        raise he

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/log/{room_id}", status_code=status.HTTP_201_CREATED)
async def hook(room_id: str, file: UploadFile = File(...)):
    try:
        with open("config.json", "rb") as f:
            config = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        save_path = config.get("save_path", os.getcwd() + "/logs/")

        # 读取文件内容
        contents = await file.read()

        if not contents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不允许上传空文件")

        # 创建房间目录
        # 校验 room_id（房间号仅允许数字）
        if not room_id.isdigit():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法 room_id")

        # 安全化文件名，防止路径穿越
        safe_filename = os.path.basename(file.filename or "")
        if safe_filename in ("", ".", ".."):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法文件名")

        # 规范化并校验路径必须位于 save_path 下
        base_dir = Path(save_path).resolve()
        room_dir = (base_dir / room_id).resolve()
        try:
            room_dir.relative_to(base_dir)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法保存路径")

        room_dir.mkdir(parents=True, exist_ok=True)

        file_path = (room_dir / safe_filename).resolve()

        try:
            file_path.relative_to(base_dir)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法文件路径")

        # 处理文件
        with open(file_path, "wb") as f:
            f.write(contents)

        return {
                "status": status.HTTP_201_CREATED,
                "message": "文件上传成功",
                "room_id": room_id,
                "filename": safe_filename,
                "size": f"{bytes_to_kb(len(contents))} KB"
            }

    except HTTPException as he:
        raise he

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/stat", status_code=status.HTTP_200_OK)
async def index(request: StatRequest):  # pyright: ignore[reportRedeclaration]
    try:
        if not Path("stat.json").exists():
            with open("stat.json", "wb+") as f:
                f.write(orjson.dumps({}, option=orjson.OPT_INDENT_2))

        with open("stat.json", "rb") as f:
            stat_data = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        stat_data[f"{request.room_id}"] = {"uid": request.uid, "time": request.time, "version": request.version}

        with open("stat.json", "wb+") as f:
            f.write(orjson.dumps(stat_data, option=orjson.OPT_INDENT_2))

    except HTTPException as he:
        raise he

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/notes", status_code=status.HTTP_200_OK)
async def index():
    try:
        if not Path("notes.json").exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")

        try:
            with open("notes.json", "rb") as f:
                data = orjson.loads(f.read().decode("utf-8").encode("utf-8"))
        except Exception as e:
            return {"code": 1, "message": str(e)}

        return {"code": 0, "data": data}

    except HTTPException as he:
        raise he

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/update", status_code=status.HTTP_200_OK)
async def index(version: str, type: Literal["zip", "sha256"]):
    """_向S3兼容的储存桶请求直链_

    Args:
        version (str): _请求的版本_
        type (Literal["zip", "sha256"]): _请求的文件类型_

    Raises:
        he: _HTTPException_

    Returns:
        _dict_: _包含code和url或message的字典_
    """
    try:
        with open("config.json", "rb") as f:
            config = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

        endpoint = config.get("endpoint", "s3.hi168.com")
        bucket_name = config.get("bucket_name", "")
        access_key = config.get("access_key", "")
        secret_key = config.get("secret_key", "")
        region = config.get("region", "us-east-1")

        client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            secure=True
        )

        url = client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=f"bili_travail/{version}.{type}"
        )

        return {"code": 0, "url": url}

    except HTTPException as he:
        raise he

    except Exception as e:
        print(traceback.format_exc())
        return {"code": 1, "message": f"{e}"}

if __name__ == "__main__":
    init_config()

    with open("config.json", "rb") as f:
        config = orjson.loads(f.read().decode("utf-8").encode("utf-8"))

    uvicorn.run(
        app=app,
        host=config.get("host", "0.0.0.0"),
        port=config.get("port", 65200)
    )