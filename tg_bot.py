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

API_USERS_DATA = dict()

for i in range(API_USERS_NUMBER):
    username = os.getenv(f'API_USERNAME_{i}')
    password = os.getenv(f'API_PASSWORD_{i}')
    API_USERS_DATA[username] = password

EXIT_PHRASES = {
    'завершить',
    'выход',
}

tg_users_tokens = dict()
tg_users_bots_ids = dict()
tg_users_bots_names = dict()
tg_users_options = dict()


available_api_users = deque(API_USERS_DATA.keys())
tg_users_api_users = dict()

bot = Bot(TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


def free_resources(tg_user_id):
    tg_users_tokens.pop(tg_user_id, None)
    tg_users_bots_ids.pop(tg_user_id, None)
    tg_users_bots_names.pop(tg_user_id, None)
    tg_users_options.pop(tg_user_id, None)
    if tg_user_id in tg_users_api_users:
        username = tg_users_api_users.pop(tg_user_id)
        available_api_users.append(username)


@dp.message(F.text == '/start')
async def start_telegram_bot(message):
    tg_user_id = str(message.from_user.id)
    free_resources(tg_user_id)
    builder = InlineKeyboardBuilder()
    response = requests.get('http://151.243.217.107/api/v1/bots/')
    chatbots = response.json()
    if not isinstance(chatbots, list):
        await message.answer('Ошибка. Попробуйте позже')
        return
    if not chatbots:
        await message.answer('Пока нет доступных чат-ботов. Попробуйте позже')
        return
    text_message = 'Выберите чат-бота:'
    for chatbot in chatbots:
        text_message += f'\n\n - {chatbot.get("name")}:'
        text_message += f'\n{chatbot.get("description")}'
        builder.button(
            text=chatbot.get('name'),
            callback_data=f'chatbot {chatbot.get("id")} {chatbot.get("name")}'
        )
    builder.adjust(1)
    await message.answer(text_message, reply_markup=builder.as_markup())


@dp.callback_query(F.data[:7] == 'chatbot')
async def start_ai_chatbot(callback):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_marup=None)
    tg_user_id = str(callback.from_user.id)
    if available_api_users:
        tg_users_api_users[tg_user_id] = available_api_users.popleft()
    else:
        await callback.message.answer('Попробуйте позже. /start')
        return
    username = tg_users_api_users[tg_user_id]
    password = API_USERS_DATA[username]
    payload = {'username': username, 'password': password}
    response = requests.post(
        'http://151.243.217.107/api-token-auth/',
        json=payload
    )
    token = response.json().get('token')
    tg_users_tokens[tg_user_id] = token
    parts = callback.data.split(' ')
    chatbot_id = parts[1]
    chatbot_name = ' '.join(parts[2:])
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(
        f'http://151.243.217.107/api/v1/bots/{chatbot_id}/run/',
        headers=headers
    )
    answer = response.json()
    if 'next' not in answer:
        await callback.message.answer(
            'Ошибка. Для просмотра списка чат-ботов введите /start'
        )
        return
    tg_users_bots_ids[tg_user_id] = chatbot_id
    tg_users_bots_names[tg_user_id] = chatbot_name
    builder = InlineKeyboardBuilder()
    for option in answer.get('next'):
        builder.button(text=option, callback_data=f'option {option}')
    builder.adjust(1)
    await callback.message.answer(
        f'- {chatbot_name}:\n{answer.get('message', 'Выберите опцию:')}',
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data[:6] == 'option')
async def process_user_option_choice(callback):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_marup=None)
    tg_user_id = str(callback.from_user.id)
    chatbot_id = tg_users_bots_ids.get(tg_user_id)
    if chatbot_id is None:
        await callback.message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        return
    chatbot_name = tg_users_bots_names.get(tg_user_id)
    option = callback.data[7:]
    if option.lower() in EXIT_PHRASES:
        await callback.message.answer(f'Выбор: {option}')
        payload = {'next': option, 'message': ''}
        headers = {'Authorization': f'Token {tg_users_tokens[tg_user_id]}'}
        response = requests.post(
            f'http://151.243.217.107/api/v1/bots/{chatbot_id}/run/',
            json=payload, headers=headers
        )
        answer = response.json()
        exit_api_message = answer.get('message')
        if exit_api_message:
            await callback.message.answer(
                f'- {chatbot_name}:\n{exit_api_message}'
            )
        free_resources(tg_user_id)
        await callback.message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        return
    tg_users_options[tg_user_id] = option
    await callback.message.answer(f'Выбор: {option}, введите текст')


@dp.message(F.text != '')
async def process_user_message(message):
    tg_user_id = str(message.from_user.id)
    chatbot_id = tg_users_bots_ids.get(tg_user_id)
    if chatbot_id is None:
        await message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        return
    chatbot_name = tg_users_bots_names.get(tg_user_id)
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
        exit_api_message = answer.get('message')
        if exit_api_message:
            await message.answer(
                f'- {chatbot_name}:\n{exit_api_message}'
            )
        free_resources(tg_user_id)
        await message.answer(
            'Чат-бот не выбран. Для просмотра списка чат-ботов введите /start'
        )
        return
    for option in answer.get('next'):
        builder.button(text=option, callback_data=f'option {option}')
    builder.adjust(1)
    await message.answer(
        f'- {chatbot_name}:\n{answer.get('message', 'Выберите опцию:')}',
        reply_markup=builder.as_markup()
    )
    tg_users_options.pop(tg_user_id)


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
