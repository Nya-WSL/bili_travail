import json
import datetime

from zoneinfo import ZoneInfo
from version import base_version

tz = ZoneInfo("Asia/Shanghai")

def create_version():
    version = datetime.datetime.now(tz).strftime("%m%d%H")
    version_info = {}
    version_info["version"] = f"{base_version}.{version}"

    with open("version.json", "w", encoding="utf-8") as f:
        json.dump(version_info, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    create_version()