import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
USERS_TOKENS = dict()
USERS_BOTS = dict()
USERS_OPTIONS = dict()

bot = Bot(TG_BOT_TOKEN)
dp = Dispatcher()


@dp.message(F.text == '/start')
async def cmd_start(message):
    builder = InlineKeyboardBuilder()
    bots = 'GET api/v1/bots/'
    for bot in bots:
        builder.button(text=bot.name, callback_data={'type': 'bot selection', 'bot_id': bot.id})
    builder.adjust()
    await message.answer('Выберите чат-бота', reply_markup=builder.as_markup())


@dp.callback_query(F.data.get('type') == 'bot selection')
async def start_bot(callback):
    bot_id = callback.data.get('bot_id')
    answer = 'GET api/v1/bots/bot_id/run/'
    USERS_BOTS[username] = bot_id
    builder = InlineKeyboardBuilder()
    for option in answer.next:
        builder.button(text=option, callback_data={'type': 'option selection', 'bot_id': bot_id, 'option': option})
    await callback.message.answer(answer.message, reply_markup=builder.as_markup())


@dp.callback_query(F.data.get('type') == 'option selection')
async def select_option(callback):
    option = callback.data.get('option')
    USERS_OPTIONS[username] = option
    await callback.message.answer(text=f'выбор-{option}, отправьте текст')


@dp.message(F.text != '')
async def get_ai_answer(message):
    if username not in USERS_OPTIONS:
        ...
    option = USERS_OPTIONS[username]
    bot_id = USERS_BOTS[username]
    answer = 'POST api/v1/bots/bot_id/run/ next:option, message:message'
    builder = InlineKeyboardBuilder()
    if answer.next == '-':
        del USERS_BOTS[username]
        del USERS_OPTIONS[username]
        await message.answer(answer.message)
    else:
        for option in answer.next:
            builder.button(text=option, callback_data={'type': 'option selection', 'bot_id': bot_id, 'option': option})
        await message.answer(answer.message, reply_markup=builder.as_markup())


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
