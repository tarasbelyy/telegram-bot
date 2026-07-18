import asyncio
import os

import requests
from aiogram import Bot, Dispatcher, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
USERS_TOKENS = dict()
USERS_BOTS = dict()
USERS_OPTIONS = dict()
username = os.getenv('CHATBOT_API_USERNAME')
password = os.getenv('CHATBOT_API_PASSWORD')

bot = Bot(TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(F.text == '/start')
async def cmd_start(message):
    builder = InlineKeyboardBuilder()
    response = requests.get('http://151.243.217.107/api/v1/bots/')
    chatbots = response.json()
    for chatbot in chatbots:
        builder.button(text=chatbot.get('name'), callback_data=f'chatbot {chatbot.get("id")}')
    builder.adjust()
    await message.answer('Выберите чат-бота', reply_markup=builder.as_markup())


@dp.callback_query(F.data[:7] == 'chatbot')
async def start_bot(callback):
    payload = {'username': username, 'password': password}
    response = requests.post('http://151.243.217.107/api-token-auth/', json=payload)
    token = response.json().get('token')
    USERS_TOKENS[username] = token
    chatbot_id = callback.data[8:]
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(f'http://151.243.217.107/api/v1/bots/{chatbot_id}/run/', headers=headers) 
    answer = response.json()
    USERS_BOTS[username] = chatbot_id
    builder = InlineKeyboardBuilder()
    for option in answer.get('next'):
        builder.button(text=option, callback_data=f'option {option}')
    await callback.message.answer(answer.get('message'), reply_markup=builder.as_markup())


@dp.callback_query(F.data[:6] == 'option')
async def select_option(callback):
    option = callback.data[7:]
    USERS_OPTIONS[username] = option
    await callback.message.answer(text=f'выбор-{option}, введите текст')


@dp.message(F.text != '')
async def get_ai_answer(message):
    option = USERS_OPTIONS[username]
    chatbot_id = USERS_BOTS[username]
    payload = {'next': option, 'message': message.text}
    headers = {'Authorization': f'Token {USERS_TOKENS[username]}'}
    response = requests.post(f'http://151.243.217.107/api/v1/bots/{chatbot_id}/run/', json=payload, headers=headers)
    answer = response.json()
    builder = InlineKeyboardBuilder()
    if answer.get('next') == '-':
        del USERS_BOTS[username]
        del USERS_OPTIONS[username]
        del USERS_TOKENS[username]
        await message.answer(answer.get('message'))
    else:
        for option in answer.get('next'):
            builder.button(text=option, callback_data=f'option {option}')
        await message.answer(answer.get('message'), reply_markup=builder.as_markup())


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
