import os
import json
from io import BytesIO
from PIL import Image

import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, URLInputFile
from aiogram.exceptions import TelegramNetworkError

from dotenv import load_dotenv

load_dotenv("API_KEYS.env")

API_TOKEN = os.getenv("TG_ID")

JPG = 0
GIF = 1

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

    filename = "photos/roulette.jpg" if image_type == JPG else "photos/roulette.gif"
    os.makedirs("photos", exist_ok=True)
    with open(filename, "wb") as f:
        f.write(img_bytes)

    return roulette_data, filename


def get_valid_image(response_bytes):
    is_pdf = False
    image = Image.open(BytesIO(response_bytes)).convert("RGB")
    w, h = image.size
    ratio = h / w

    out = BytesIO()
    out.name = "photo.jpg"

    if h + w >= 10000 or ratio >= 20:
        image.save(out, format="PDF")
        is_pdf = True
    else:
        image.save(out, format="JPEG")

    out.seek(0)
    return out, is_pdf

async def safe_send_photo(chat_id, file, caption=None, retries=3):
    for i in range(retries):
        try:
            await bot.send_photo(chat_id, file, caption=caption)
            break
        except TelegramNetworkError:
            if i < retries - 1:
                print(f"retrie {i}")
                await asyncio.sleep(2)
            else:
                bot.send_message(chat_id, "Failed to send photo")
                raise

async def cmd_start(message: types.Message):
    await message.answer("Avalible commands /random, /search")


async def cmd_random(message: types.Message):
    roulette_data, filename = await get_random_roulette()
    photo = FSInputFile(filename)
    await bot.send_photo(message.chat.id, photo, caption=roulette_data["name"])


async def cmd_search(message: types.Message, state: FSMContext):
    await message.answer("Enter filter name:")
    await state.set_state(UserStates.roulette_name)


async def process_roulette_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Enter roulettes num")
    await state.set_state(UserStates.roulette_num)


async def process_roulette_num(message: types.Message, state: FSMContext):
    try:
        num = int(message.text)
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

        async with session.get(img_url_jpg) as img_resp:
            if img_resp.status == 200:
                img_bytes = await img_resp.read()
            else:
                async with session.get(img_url_png) as img_resp2:
                    img_bytes = await img_resp2.read()

        img_data, is_pdf = get_valid_image(img_bytes)

        os.makedirs("roulettes", exist_ok=True)

        if is_pdf:
            await message.answer("The image is too big for telegram, will be sent as pdf")
            file_path = "roulettes/roulette.pdf"
            with open(file_path, "wb") as f:
                f.write(img_data.getbuffer())
            file = FSInputFile(file_path)
            await bot.send_document(message.chat.id, document=file, caption=roulette[1])
        else:
            file_path = "roulettes/roulette.jpg"
            with open(file_path, "wb") as f:
                f.write(img_data.getbuffer())
            file = FSInputFile(file_path)
            await safe_send_photo(message.chat.id, file, caption=roulette[1])

        counted_roulettes.append(roulette)

    await state.clear()
    await message.answer(str(counted_roulettes))

router.message.register(cmd_start, Command(commands=["start", "menu"]))
router.message.register(cmd_random, Command("random"))
router.message.register(cmd_search, Command("search"))
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
