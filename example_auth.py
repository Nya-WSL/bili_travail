from datetime import timedelta
from nicegui import app, ui

import os
import json
import hashlib

class Countdown:
    def __init__(self):
        self.timer_status = False
        self.remaining = timedelta(seconds=0) # Variables cannot be accessed here

    def start(self, hour, minute, second):
        if self.timer_status:
            ui.notify("Please stop the timer first", type="negative")
        elif hour == 0 and minute == 0 and second == 0:
            ui.notify("Please input time", type="negative")
        else:
            self.timer_status = True
            self.remaining = timedelta(hours=hour, minutes=minute, seconds=second)
            self.timer = app.timer(1, self.update)

    def update(self):
        if self.remaining > timedelta(seconds=0):
            self.remaining -= timedelta(seconds=1)
        else:
            self.timer_status = False
            self.remaining = timedelta(seconds=0)

    def pause(self):
        self.timer.active = False

    def resume(self):
        self.timer.active = True

    def stop(self):
        self.timer_status = False
        self.remaining = timedelta(seconds=0)
        self.timer.cancel()

countdown = Countdown() # NOTE: this is global so each visitor sees the same countdown

@ui.page('/')
def page():
    if not app.storage.user.get('authenticated'):
        ui.navigate.to('/login')
    else:
        ui.navigate.to('/admin')

def format_timer(remaining_time):
    minute, second = divmod(remaining_time, 60)
    hour, minute = divmod(minute, 60)
    return "%02d:%02d:%02d" % (hour, minute, second)

@ui.page('/login')
def page():
    def try_login() -> None:
        if not os.path.exists('users.json'):
            with open('users.json', 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
        with open('users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        try:
            if users[username.value] == hashlib.sha256(str(password.value).encode('utf-8')).hexdigest():
                app.storage.user.indent = True
                app.storage.user.update({'user': username.value, 'authenticated': True})
                ui.navigate.to(app.storage.user.get('referrer_path', '/admin'))
            else:
                ui.notify('密码错误', color='negative')
        except KeyError:
            ui.notify('账号错误或不存在', color='negative')

    ui.query('body').style('background: url("static/bg.jpg") 0px 0px/cover')
    with ui.card().classes('absolute-center'):
        ui.badge('B站加班姬', outline=True, color='', text_color='#E6354F').classes('text-xl')
        username = ui.input('账号').on('keydown.enter', try_login)
        password = ui.input('密码', password=True, password_toggle_button=True).on('keydown.enter', try_login)
        with ui.row():
            ui.button('登录', on_click=try_login)
            ui.button('返回', on_click=lambda: ui.navigate.to("/"))


@ui.page('/admin')
def page():
    if not app.storage.user.get('authenticated'):
        ui.navigate.to('/login')

    with ui.card(align_items="center").classes('absolute-center'):
        ui.badge(outline=True).bind_text_from(countdown, 'remaining', lambda remaining: f'{format_timer(remaining.seconds)}')
        with ui.row():
            input_hours = ui.number("hour", value=0, min=0)
            input_minutes = ui.number("minute", value=0, min=0)
            input_seconds = ui.number("second", value=0, min=0)
        with ui.row():
            ui.button('Start', on_click=lambda: countdown.start(input_hours.value, input_minutes.value, input_seconds.value))
            ui.button('Pause', on_click=lambda: countdown.pause())
            ui.button('Resume', on_click=lambda: countdown.resume())
            ui.button('Stop', on_click=lambda: countdown.stop())

ui.run(storage_secret="vita")