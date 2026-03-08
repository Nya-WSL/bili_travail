# Bili_travail | B站加班姬

基于blivedm和NiceGUI的B站直播加班姬

## Feature

- 支持身份码连接
- 支持自定义颜色
- 支持暂停倒计时
- 支持忽略倒计时
- 支持倒计时玩法
- 支持投喂挑战玩法
- 支持显示投喂记录
- 支持统计礼物、盲盒数据
- 支持 `保存/读取` 倒计时
- 支持 `增加/减少` 倒计时
- 支持根据直播间获取B站礼物数据
- 支持自定义api服务器（目前只支持 `上传日志和获取盲盒数据`，需服务器运行 `bili_travail_api.py`，依赖文件：`pyproject_server.toml`）

## Usage

- 运行加班姬
- 输入身份码
- 更新礼物数据
- 设置礼物和玩法
- OBS或哔哩哔哩直播姬添加浏览器源（url在控制面板最下方）
- 开始倒计时（注：不连接弹幕服务器无法开始倒计时）

## Build

### 环境

- python 3.13.5

#### clone project

```
git clone https://github.com/Nya-WSL/bili_travail.git
cd bili_travail
```

#### install depend

- poetry

```
pip install poetry
poetry config virtualenvs.in-project true # if need create virtualenv in project
poetry install
```

- uv

```
# use uv

# windows
winget install --id=astral-sh.uv -e

# macos
# Note: maybe not support
brew install uv

# linux desktop
# Note: maybe not support
pipx install uv

uv sync
```

#### build

```
# 如果使用mac，构建需要苹果开发者账号

# poetry
poetry run python build.py

# uv
uv run build.py

# https://open-live.bilibili.com/open-manage
input your access_key_id、access_key_secred、app_id
```

## Known Issues

- 因为B站API数据不全，获取房间礼物时可能会缺少部分特殊礼物
- 在极特殊的情况下可能会同时存在两个倒计时

## Changelog

[changelog](https://github.com/Nya-WSL/bili_travail/blob/open_live/changelog.json)