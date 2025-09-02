from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from enum import Enum
from aiogram.filters.callback_data import CallbackData

class Commands(str, Enum):
    start = "start"
    menu = "menu"
    random = "random"
    search = "search"

class CommandCallback(CallbackData, prefix="com"):
    command: Commands

class NumberCallback(CallbackData, prefix="num"):
    target: str
    num: int

class RollCallback(CallbackData, prefix="roll"):
    dice: int
    dice_num: int
    dice_type: int


start_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="menu", callback_data=CommandCallback(command=Commands.menu).pack()),
         InlineKeyboardButton(text="random", callback_data=CommandCallback(command=Commands.random).pack()),
         InlineKeyboardButton(text="search", callback_data=CommandCallback(command=Commands.search).pack())
         ]
    ]
)

search_num_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data=NumberCallback(target=Commands.search, num=1).pack()),
         InlineKeyboardButton(text="3", callback_data=NumberCallback(target=Commands.search, num=3).pack()),
         InlineKeyboardButton(text="5", callback_data=NumberCallback(target=Commands.search, num=5).pack()),
         InlineKeyboardButton(text="10", callback_data=NumberCallback(target=Commands.search, num=10).pack())
         ]
    ]
)


keyboards = {"start_keyboard" : start_keyboard,
             "search_num_keyboard" : search_num_keyboard,
             }


def make_roll_keyboard(dice_num: int, dice_type: int):
    builder = InlineKeyboardBuilder()
    letters = [chr(ord('Z') - i) for i in range(26)]

    builder.button(
        text="reroll all",
        callback_data=RollCallback(dice=-1, dice_num=dice_num, dice_type=dice_type).pack()
    )
    for i in range(dice_num):
        builder.button(
            text=f"reroll {letters[i]}",
            callback_data=RollCallback(dice=i, dice_num=dice_num, dice_type=dice_type).pack()
        )

    return builder.as_markup()