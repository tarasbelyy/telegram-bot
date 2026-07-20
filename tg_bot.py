import asyncio
import os

import requests
from aiogram import Bot, Dispatcher, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv


USERS_TOKENS = dict()
USERS_BOTS = dict()
USERS_OPTIONS = dict()

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

username = os.getenv('CHATBOT_API_USERNAME')
password = os.getenv('CHATBOT_API_PASSWORD')

bot = Bot(TELEGRAM_BOT_TOKEN)

dp = Dispatcher()


@dp.message(F.text == '/start')
async def cmd_start(message):
    builder = InlineKeyboardBuilder()
    response = requests.get('http://151.243.217.107/api/v1/bots/')
    chatbots = response.json()
    text_message = 'Выберите чат-бота:'
    for chatbot in chatbots:
        text_message += f'\n\n - {chatbot.get("name")}:'
        text_message += f'\n{chatbot.get("description")}'
        builder.button(
            text=chatbot.get('name'),
            callback_data=f'chatbot {chatbot.get("id")}'
        )
    await message.answer(text_message, reply_markup=builder.as_markup())


@dp.callback_query(F.data[:7] == 'chatbot')
async def start_bot(callback):
    payload = {'username': username, 'password': password}
    response = requests.post(
        'http://151.243.217.107/api-token-auth/',
        json=payload
    )
    token = response.json().get('token')
    USERS_TOKENS[username] = token
    chatbot_id = callback.data[8:]
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(
        f'http://151.243.217.107/api/v1/bots/{chatbot_id}/run/',
        headers=headers
    )
    answer = response.json()
    USERS_BOTS[username] = chatbot_id
    builder = InlineKeyboardBuilder()
    for option in answer.get('next'):
        builder.button(text=option, callback_data=f'option {option}')
    await callback.message.answer(
        answer.get('message'),
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data[:6] == 'option')
async def select_option(callback):
    if username not in USERS_BOTS:
        await callback.message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        return
    option = callback.data[7:]
    USERS_OPTIONS[username] = option
    await callback.message.answer(text=f'Выбор: {option}, введите текст')


@dp.message(F.text != '')
async def get_ai_answer(message):
    chatbot_id = USERS_BOTS.get(username)
    if chatbot_id is None:
        await message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        return
    option = USERS_OPTIONS.get(username)
    if option is None:
        await message.answer('Выберите опцию')
        return
    payload = {'next': option, 'message': message.text}
    headers = {'Authorization': f'Token {USERS_TOKENS[username]}'}
    response = requests.post(
        f'http://151.243.217.107/api/v1/bots/{chatbot_id}/run/',
        json=payload, headers=headers
    )
    answer = response.json()
    if 'next' not in answer:
        await message.answer(
            'Ошибка. Для просмотра списка чат-ботов введите /start'
        )
        return
    builder = InlineKeyboardBuilder()
    if answer.get('next') == '-':
        await message.answer(answer.get('message'))
        del USERS_BOTS[username]
        del USERS_OPTIONS[username]
        del USERS_TOKENS[username]
        return
    for option in answer.get('next'):
        builder.button(text=option, callback_data=f'option {option}')
    await message.answer(
        answer.get('message'),
        reply_markup=builder.as_markup()
    )
    del USERS_OPTIONS[username]


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
