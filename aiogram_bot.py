import os
import random
import json
from io import BytesIO
from PIL import Image
from enum import Enum

import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, URLInputFile, CallbackQuery
from aiogram.exceptions import TelegramNetworkError

from dotenv import load_dotenv
from keyboards import Commands, CommandCallback, NumberCallback, RollCallback, keyboards, make_roll_keyboard

load_dotenv("API_KEYS.env")

API_TOKEN = os.getenv("TG_ID")

JPG = 0
GIF = 1
PNG = 2
WEBP = 3

ext_map = {
    JPG: "jpg",
    GIF: "gif",
    PNG: "png",
    WEBP: "webp"
}

dice_types = {
    0 : (0, 9),
    1 : (1, 6)
}

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

session: aiohttp.ClientSession


class UserStates(StatesGroup):
    roulette_name = State()
    roulette_num = State()


async def init_session():
    global session
    session = aiohttp.ClientSession()

async def close_session():
    await session.close()


async def get_random_roulette():
    url = "https://faproulette.co/api/random"
    async with session.get(url) as resp:
        roulette_data = await resp.json()
        img_url = roulette_data["image_url"]
        image_type = roulette_data["image_type"]

        async with session.get(img_url) as img_resp:
            img_bytes = await img_resp.read()

    filename = f"photos/roulette.{ext_map.get(image_type)}"
    os.makedirs("photos", exist_ok=True)
    with open(filename, "wb") as f:
        f.write(img_bytes)

    return roulette_data, filename


def get_valid_image(response_bytes, file_path):
    is_pdf = False

    os.makedirs("photos", exist_ok=True)

    image = Image.open(BytesIO(response_bytes)).convert("RGB")
    w, h = image.size
    ratio = h / w

    if h + w >= 10000 or ratio >= 15:
        with open("photos/roulette.pdf", "wb") as f:
            f.write(response_bytes)
        is_pdf = True
    else:
        with open(file_path, "wb") as f:
            f.write(response_bytes)

    return is_pdf

async def safe_send_photo(chat_id, file, caption=None, retries=3, reply_markup=None):
    for i in range(retries):
        try:
            message = await bot.send_photo(chat_id, file, caption=caption, reply_markup=reply_markup)
            break
        except TelegramNetworkError:
            if i < retries - 1:
                print(f"retrie {i}")
                await asyncio.sleep(2)
            else:
                message = await bot.send_message(chat_id, "Failed to send photo")
                raise
    return message

async def cmd_start(message: types.Message):
    await message.answer("Avalible commands /random, /search", reply_markup=keyboards["start_keyboard"])


async def cmd_random(message: types.Message):
    roulette_data, filename = await get_random_roulette()
    file = FSInputFile(filename)
    if roulette_data["image_type"] == GIF:
        sent_message = await bot.send_animation(
            message.chat.id, 
            file, 
            caption=roulette_data["name"], 
            )
    else:
        sent_message = await safe_send_photo(
            message.chat.id, 
            file, 
            caption=roulette_data["name"], 
            )
    await roll_dices(sent_message, roulette_data["numbers"], roulette_data["dice"], reply_markup=make_roll_keyboard(roulette_data["numbers"], roulette_data["dice"]))


async def cmd_search(message: types.Message, state: FSMContext):
    await message.answer("Enter filter name:")
    await state.set_state(UserStates.roulette_name)


async def process_roulette_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(UserStates.roulette_num)
    await message.answer("Enter roulettes num", reply_markup=keyboards["search_num_keyboard"])


async def process_roulette_num(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        num = int(data["num"])
    except ValueError:
        await message.answer("Please, enter a valid number")
        return

    data = await state.get_data()
    name = data.get("name")
    headers = {
                "roulettes_page": "home",
                "part": 0,
                "order": "trending",
                "name": name,
            }

    async with session.post("https://faproulette.co/api/getRoulettes", data=headers) as resp:
        text = await resp.text()
        roulettes = json.loads(text)

        if isinstance(roulettes, dict):
            roulette_data = roulettes.get("rouletteData", [])
            if isinstance(roulette_data, str):
                roulettes = json.loads(roulette_data)
            elif isinstance(roulette_data, list):
                roulettes = roulette_data
    #print(roulettes)
    counted_roulettes = []

    for i in range(min(num, len(roulettes))):
        roulette = roulettes[i]
        img_url_jpg = f"https://files.faproulette.co/images/fap/{roulette[5]}.jpg"
        img_url_png = f"https://files.faproulette.co/images/fap/{roulette[5]}.png"
        file_type = roulette[6]
        file_path = f"photos/roulette.{ext_map.get(file_type)}"

        async with session.get(img_url_jpg) as img_resp:
            if img_resp.status == 200:
                img_bytes = await img_resp.read()
            else:
                async with session.get(img_url_png) as img_resp2:
                    img_bytes = await img_resp2.read()

        is_pdf = get_valid_image(img_bytes, file_path)

        if is_pdf:
            await message.answer("The image is too big for telegram, will be sent as pdf")
            file = FSInputFile(file_path)
            sent_message = await bot.send_document(
                message.chat.id, 
                document=file, 
                caption=roulette[1],
                )
        else:
            file = FSInputFile(file_path)
            if file_type == GIF:
                sent_message = await bot.send_animation(
                    message.chat.id, 
                    file, 
                    caption=roulette[1],
                    )
            else:
                sent_message = await safe_send_photo(
                    message.chat.id, 
                    file, 
                    caption=roulette[1],
                    )
        
        await roll_dices(sent_message, roulette[3], roulette[2], make_roll_keyboard(roulette[3], roulette[2]))

        counted_roulettes.append(roulette)

    await state.clear()
    await message.answer(str(counted_roulettes))


async def get_command_function(command: Commands, message: types.Message, state: FSMContext):
    if command == Commands.menu:
        return await cmd_start(message)
    elif command == Commands.random:
        return await cmd_random(message)
    elif command == Commands.search:
        return await cmd_search(message, state)
    

async def roll_dices(message: types.Message, number_of_dices: int, dice_type: int, reply_markup):
    letters = [chr(ord('Z') - i) for i in range(26)]
    number_range = dice_types.get(dice_type)

    for j in range(10):
        numbers_str = []

        for i in range(number_of_dices):
            if i >= len(letters):
                break
            
            rand_num = random.randint(number_range[0], number_range[1])
            numbers_str.insert(0, f"{letters[i]}:{rand_num}  ")
            
            if (i + 1) % 7 == 0:
                numbers_str.insert(0, "\n")
        
        await bot.edit_message_caption(chat_id=message.chat.id, message_id=message.message_id, caption=' '.join(numbers_str), reply_markup=reply_markup)
        await asyncio.sleep(0.1)


@router.callback_query(NumberCallback.filter())
async def process_number(query: CallbackQuery, callback_data: NumberCallback, state: FSMContext):
    if callback_data.target == Commands.search:
        await state.update_data(num=callback_data.num)
        data = await state.get_data()
        print(data["num"])
        await process_roulette_num(query.message, state)
    

@router.callback_query(CommandCallback.filter())
async def raise_command(query: CallbackQuery, callback_data: CommandCallback, state: FSMContext):
    await get_command_function(callback_data.command, query.message, state)
    
@router.callback_query(RollCallback.filter())    
async def roll(query: CallbackQuery, callback_data: RollCallback, state: FSMContext):
    await roll_dices(query.message, callback_data.dice_num, callback_data.dice_type, query.message.reply_markup)

router.message.register(cmd_start, Command(commands=[Commands.start, Commands.menu]))
router.message.register(cmd_random, Command(Commands.random))
router.message.register(cmd_search, Command(Commands.search))
router.message.register(process_roulette_name, StateFilter(UserStates.roulette_name))
router.message.register(process_roulette_num, StateFilter(UserStates.roulette_num))



dp.include_router(router)



async def main():
    print("~"*40)
    await init_session()

    await dp.start_polling(bot, skip_updates=True)

    await close_session()

if __name__ == "__main__":
    asyncio.run(main())