# Bili Travail - B站加班姬

基于blivedm和NiceGUI的B站直播加班姬

## Feature

- 支持倒计时玩法
- 支持投喂挑战玩法
- 支持身份码连接
- 支持显示投喂记录
- 支持自定义颜色
- 支持暂停倒计时
- 支持忽略倒计时
- 支持 `保存/读取` 倒计时
- 支持 `增加/减少` 倒计时
- 支持统计礼物、盲盒数据
- 支持根据直播间更新B站礼物数据
- 成功连接后会显示房间号
- 支持自定义api服务器（目前只支持上传日志，需服务器运行 `bili_travail_api.py`，依赖文件：`pyproject_server.toml`）

## Usage

- 运行加班姬
- 输入身份码
- 更新礼物数据（初次运行时因为无法获取房间号，默认创建空的礼物数据）
- 设置礼物和玩法
- OBS或哔哩哔哩直播姬添加浏览器源（url在控制面板最下方）
- 开始倒计时（注：不连接弹幕服务器无法开始倒计时）

## Build

```
git clone https://github.com/Nya-WSL/bili_travail.git
cd bili_travail
pip install poetry
poetry install
build.bat

# https://open-live.bilibili.com/open-manage
input your access_key_id、access_key_secred、app_id
```

## Known Issues

- 获取房间礼物时可能会缺少部分礼物
- 在极特殊的情况下可能会同时存在两个倒计时

## Change Log

[changelog](https://github.com/Nya-WSL/bili_travail/blob/open_live/changelog.json)