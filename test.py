import requests
import json
import telebot
import os
from dotenv import load_dotenv
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage


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



print('~'*50)

get_random_roulette()

@bot.message_handler(commands=["random"])
def handle_promt(message):
    roulette = get_random_roulette()
    current_user_id = message.chat.id
    bot.send_photo(current_user_id, roulette["image_url"], caption=roulette["name"])

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
def get_age(message):
    try:
        num = int(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid number")
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        name = data['name']
    
    response = requests.post("https://faproulette.co/api/getRoulettes",
                             data={
                               "roulettes_page" : "home",
                               "part" : 0,
                               "order" : "trending",
                               "name" : name
                               })
    
    raw_data = json.loads(response.text)
    roulettes = json.loads(raw_data["rouletteData"])
    counted_roulettes = []

    for i in range(num):
        counted_roulettes.append(roulettes[i])
    print(counted_roulettes)
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, str(counted_roulettes))


#print(search_roulettes("anal"))
bot.add_custom_filter(telebot.custom_filters.StateFilter(bot))
bot.polling(non_stop=True, interval=0)