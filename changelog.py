import json
import requests

from nicegui import ui


def get_log():
    url = "http://version.nya-wsl.cn/bili_travail/changelog.json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return False


def changelog():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    logs = get_log()

    with (
        ui.card(align_items="center")
        .classes("w-full")
        .style("box-shadow: None; left: -5%")
    ):
        with ui.row():
            ui.button(
                "返回主页",
                on_click=lambda: ui.navigate.to("/"),
                color=config["btn_color"],
            ).style("right: -15%")

            ui.button(
                "GitHub",
                on_click=lambda: ui.navigate.to(
                    "https://github.com/Nya-WSL/bili_travail", new_tab=True
                ),
                color=config["btn_color"],
            ).style("right: -15%")

        if logs:
            with ui.timeline(side="right", layout="comfortable", color="btn"):
                for k, v in logs.items():
                    with ui.timeline_entry(title=f"Release of {k}", subtitle=v["date"]):
                        with ui.column().classes("gap-3"):
                            for item in v["content"]:
                                ui.label(f"● {item}")
