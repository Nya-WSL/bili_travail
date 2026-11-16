import os
import re
import orjson
import datetime
import itertools

from nicegui import ui, app

from libs import log
from libs import gift
from libs import styles
from libs.i18n import t

logger = log.logger

async def capture_blind_page(get_notes_func, init_config_func, base_config):
    """盲盒盈亏捕获页面"""
    ...