import requests
import json
import telebot
import os
from dotenv import load_dotenv
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from io import BytesIO
from PIL import Image
from telebot.types import InputFile


JPG = 0
GIF = 1

load_dotenv("API_KEYS.env")


state_storage = StateMemoryStorage()
bot = telebot.TeleBot(os.getenv("TG_ID"), state_storage=state_storage)


class UserStates(StatesGroup):
    roulette_name = State()
    roulette_num = State()

def get_random_roulette():
    url = "https://faproulette.co/api/random"
    response = requests.get(url)
    roulette_data = json.loads(response.text)
    img_data = requests.get(roulette_data["image_url"]).content
    if roulette_data["image_type"] == JPG:
        with open("photos/roulette.jpg", "wb") as photo:
            photo.write(img_data)
    elif roulette_data["image_type"] == GIF:
        with open("photos/roulette.gif", "wb") as photo:
            photo.write(img_data)
    #print(response.status_code)
    #print(roulette_data)
    return roulette_data

def get_valid_image(response):
    is_pdf = False
    
    image = Image.open(BytesIO(response.content)).convert("RGB")
    w, h = image.size
    ratio = h/w

    out = BytesIO()
    out.name = "photo.jpg"

    if h+w >= 10000 or ratio >= 20:
        image.save(out, format="PDF")
        is_pdf = True
    else:
        image.save(out, format="JPEG")
    
    out.seek(0)
    return out, is_pdf

print('~'*50)

get_random_roulette()

@bot.message_handler(commands=["start", "menu"])
def handle_promt(message):
    roulette = get_random_roulette()
    current_user_id = message.chat.id
    bot.send_photo(current_user_id, open("photos/roulette.jpg", "rb"), caption=roulette["name"])

@bot.message_handler(commands=["random"])
def handle_promt(message):
    roulette = get_random_roulette()
    current_user_id = message.chat.id
    bot.send_photo(current_user_id, open("photos/roulette.jpg", "rb"), caption=roulette["name"])

@bot.message_handler(commands=["search"])
def search_roulettes(message):
    bot.send_message(message.chat.id, "Enter roulette name")
    bot.set_state(message.from_user.id, UserStates.roulette_name, message.chat.id)

@bot.message_handler(state=UserStates.roulette_name)
def get_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = message.text
    
    bot.send_message(message.chat.id, f"How many roulettes to search?")
    bot.set_state(message.from_user.id, UserStates.roulette_num, message.chat.id)

@bot.message_handler(state=UserStates.roulette_num)
def get_roulette_num(message):
    current_chat_id = message.chat.id
    try:
        num = int(message.text)
    except ValueError:
        bot.send_message(current_chat_id, "Please enter a valid number")
        return

    with bot.retrieve_data(message.from_user.id, current_chat_id) as data:
        name = data['name']
    
    response = requests.post("https://faproulette.co/api/getRoulettes",
                             data={
                               "roulettes_page" : "home",
                               "part" : 0,
                               "order" : "trending",
                               "name" : name
                               })
    
    roulettes = json.loads(response.text)
    if type(roulettes) != list:
        print(type(roulettes))
        roulettes = json.loads(roulettes["rouletteData"])
    counted_roulettes = []

    for i in range(num):
        roulette = roulettes[i]
        response = requests.get(f"https://files.faproulette.co/images/fap/{roulette[0]}.jpg")
        if response.status_code != 200:
            response = requests.get(f"https://files.faproulette.co/images/fap/{roulette[5]}.png")
        img_data, is_pdf = get_valid_image(response)
        if is_pdf:
            bot.send_message(current_chat_id, "Image is too large for telegram, it will be sent as pdf")
            file = InputFile(img_data, file_name="roulette.pdf")
            bot.send_document(chat_id=current_chat_id, document=file, caption=roulette[1]) #roulette[1] is a name
        else:
            bot.send_photo(current_chat_id, img_data, roulette[1]) #roulette[1] is a name
        counted_roulettes.append(roulette)

    print(counted_roulettes)
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, str(counted_roulettes))


#print(search_roulettes("anal"))
bot.add_custom_filter(telebot.custom_filters.StateFilter(bot))
bot.polling(non_stop=True, interval=0)