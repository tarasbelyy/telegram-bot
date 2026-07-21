import asyncio
import os
from collections import deque

import requests
from aiogram import Bot, Dispatcher, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_USERS_NUMBER = int(os.getenv('API_USERS_NUMBER', '1'))

api_users_data = dict()

for i in range(API_USERS_NUMBER):
    username = os.getenv(f'API_USERNAME_{i}')
    password = os.getenv(f'API_PASSWORD_{i}')
    api_users_data[username] = password

tg_users_tokens = dict()
tg_users_bots = dict()
tg_users_options = dict()


available_api_users = deque(api_users_data.keys())
tg_users_api_users = dict()

bot = Bot(TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(F.text == '/start')
async def cmd_start(message):
    tg_user_id = str(message.from_user.id)
    tg_users_tokens.pop(tg_user_id, None)
    tg_users_bots.pop(tg_user_id, None)
    tg_users_options.pop(tg_user_id, None)
    if tg_user_id in tg_users_api_users:
        username = tg_users_api_users[tg_user_id]
        del tg_users_api_users[tg_user_id]
        available_api_users.append(username)
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
    tg_user_id = str(callback.from_user.id)
    if available_api_users:
        tg_users_api_users[tg_user_id] = available_api_users.popleft()
    else:
        await callback.message.answer('Попробуйте позже')
        return
    await callback.message.edit_reply_markup(reply_marup=None)
    username = tg_users_api_users[tg_user_id]
    password = api_users_data[username]
    payload = {'username': username, 'password': password}
    response = requests.post(
        'http://151.243.217.107/api-token-auth/',
        json=payload
    )
    token = response.json().get('token')
    tg_users_tokens[tg_user_id] = token
    chatbot_id = callback.data[8:]
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(
        f'http://151.243.217.107/api/v1/bots/{chatbot_id}/run/',
        headers=headers
    )
    answer = response.json()
    tg_users_bots[tg_user_id] = chatbot_id
    builder = InlineKeyboardBuilder()
    for option in answer.get('next'):
        builder.button(text=option, callback_data=f'option {option}')
    await callback.message.answer(
        answer.get('message'),
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data[:6] == 'option')
async def select_option(callback):
    tg_user_id = str(callback.from_user.id)
    if tg_user_id not in tg_users_bots:
        await callback.message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        return
    option = callback.data[7:]
    tg_users_options[tg_user_id] = option
    await callback.message.answer(text=f'Выбор: {option}, введите текст')


@dp.message(F.text != '')
async def get_ai_answer(message):
    tg_user_id = str(message.from_user.id)
    username = tg_users_api_users.get(tg_user_id)
    chatbot_id = tg_users_bots.get(tg_user_id)
    if chatbot_id is None:
        await message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        return
    option = tg_users_options.get(tg_user_id)
    if option is None:
        await message.answer('Выберите опцию')
        return
    payload = {'next': option, 'message': message.text}
    headers = {'Authorization': f'Token {tg_users_tokens[tg_user_id]}'}
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
        await message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        del tg_users_bots[tg_user_id]
        del tg_users_options[tg_user_id]
        del tg_users_tokens[tg_user_id]
        del tg_users_api_users[tg_user_id]
        available_api_users.append(username)
        return
    for option in answer.get('next'):
        builder.button(text=option, callback_data=f'option {option}')
    await message.answer(
        answer.get('message'),
        reply_markup=builder.as_markup()
    )
    del tg_users_options[tg_user_id]


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
