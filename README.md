# Bili_travail | B站加班姬

基于blivedm和NiceGUI的B站直播加班姬

#### [当前迭代和路线图](https://github.com/orgs/Nya-WSL/projects/4)

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
- 支持自定义api服务器（需服务器运行 `bili_travail_api.py`，安装依赖：`uv sync --group server`）

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

- uv

```
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

uv sync --group dev
uv run build.py

# https://open-live.bilibili.com/open-manage
input your access_key_id、access_key_secred、app_id
```

> 如果使用Nuitka编译需安装 `Visual Studio 2022 or higher`，并选择 `使用 C++ 的桌面开发`，在单个组件中勾选 `MSVC v*** - VS YYYY C++ x64/x86 生成工具(v***)` 或 `适用于Windows的 C++ Clang 编译器`
>
> 无论安装MSVC还是Clang都必须勾选 `Windows 11 SDK`
>
> 或者可以尝试将Python版本降级至3.12及以下，使用从Nuitka下载的 `MinGW64` 编译器

## Known Issues

- 在极特殊的情况下可能会同时存在两个倒计时

## Changelog

[changelog](https://github.com/Nya-WSL/bili_travail/blob/open_live/changelog.json)

## License

本产品采用基于 MIT 协议修改的自定义许可协议（含附加限制条款），并非标准 MIT 协议。使用时需遵守以下附加限制：

- 未经重大更改（即未对核心逻辑/功能进行实质性重写）的版本，禁止上传至 [Bilibili 开放平台](https://open-live.bilibili.com)，亦禁止在任何电商平台（淘宝、京东、拼多多、闲鱼、亚马逊等）出售或提供销售
- 软件名称和图标不得在任何衍生作品中二次使用或重新品牌化
- 不得冒用作者组织 `Nya-WSL` 及其名下成员的身份
- 本产品与哔哩哔哩（Bilibili）公司无任何隶属、背书或关联关系

完整条款见 [LICENSE](LICENSE)。

This project is licensed under a custom license based on the MIT License (with additional restrictions), not the standard MIT License. See [LICENSE](LICENSE) for full terms.