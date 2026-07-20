import asyncio
import os

import requests
from aiogram import Bot, Dispatcher, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv


load_dotenv()

API_USERS_TOKENS = dict()
API_USERS_BOTS = dict()
API_USERS_OPTIONS = dict()

API_USERS_DATA = {
    os.getenv('CHATBOT_API_USERNAME'): os.getenv('CHATBOT_API_PASSWORD')
}

AVAILABLE_API_USERS = list(API_USERS_DATA.keys())
TG_USERS_API_USERS = dict()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

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
    builder.adjust(1)
    await message.answer(text_message, reply_markup=builder.as_markup())


@dp.callback_query(F.data[:7] == 'chatbot')
async def start_bot(callback):
    tg_username = callback.from_user.username
    if AVAILABLE_API_USERS:
        TG_USERS_API_USERS[tg_username] = AVAILABLE_API_USERS.pop()
    else:
        await callback.message.answer('Попробуйте позже')
        return
    username = TG_USERS_API_USERS[tg_username]
    password = API_USERS_DATA[username]
    payload = {'username': username, 'password': password}
    response = requests.post(
        'http://151.243.217.107/api-token-auth/',
        json=payload
    )
    token = response.json().get('token')
    API_USERS_TOKENS[username] = token
    chatbot_id = callback.data[8:]
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(
        f'http://151.243.217.107/api/v1/bots/{chatbot_id}/run/',
        headers=headers
    )
    answer = response.json()
    API_USERS_BOTS[username] = chatbot_id
    builder = InlineKeyboardBuilder()
    for option in answer.get('next'):
        builder.button(text=option, callback_data=f'option {option}')
    await callback.message.answer(
        answer.get('message'),
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data[:6] == 'option')
async def select_option(callback):
    tg_username = callback.from_user.username
    username = TG_USERS_API_USERS.get(tg_username)
    if username is None or username not in API_USERS_BOTS:
        await callback.message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        return
    option = callback.data[7:]
    API_USERS_OPTIONS[username] = option
    await callback.message.answer(text=f'Выбор: {option}, введите текст')


@dp.message(F.text != '')
async def get_ai_answer(message):
    tg_username = message.from_user.username
    username = TG_USERS_API_USERS.get(tg_username)
    chatbot_id = API_USERS_BOTS.get(username)
    if chatbot_id is None:
        await message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        return
    option = API_USERS_OPTIONS.get(username)
    if option is None:
        await message.answer('Выберите опцию')
        return
    payload = {'next': option, 'message': message.text}
    headers = {'Authorization': f'Token {API_USERS_TOKENS[username]}'}
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
        del API_USERS_BOTS[username]
        del API_USERS_OPTIONS[username]
        del API_USERS_TOKENS[username]
        del TG_USERS_API_USERS[tg_username]
        AVAILABLE_API_USERS.append(username)
        return
    for option in answer.get('next'):
        builder.button(text=option, callback_data=f'option {option}')
    await message.answer(
        answer.get('message'),
        reply_markup=builder.as_markup()
    )
    del API_USERS_OPTIONS[username]


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
