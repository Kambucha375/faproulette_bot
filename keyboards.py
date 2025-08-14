from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from enum import Enum
from aiogram.filters.callback_data import CallbackData

class Commands(str, Enum):
    start = "start"
    menu = "menu"
    random = "random"
    search = "search"

class CommandCallback(CallbackData, prefix="com"):
    command: Commands


start_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="menu", callback_data=CommandCallback(command=Commands.menu).pack()),
         InlineKeyboardButton(text="random", callback_data=CommandCallback(command=Commands.random).pack()),
         InlineKeyboardButton(text="search", callback_data=CommandCallback(command=Commands.search).pack())
         ]
    ]
)

keyboards = {"start_keyboard" : start_keyboard
             }