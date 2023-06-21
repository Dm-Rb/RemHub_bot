#!/usr/bin/python3

from os.path import join
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import InputFile
from support_functions import get_username_from_jira, get_issues_from_jira, create_list_of_obj_for_output_bot
from custom_classes import Database, UserState
import aioschedule
from messages import messages as mes
from config import Config, load_config


config: Config = load_config()
BOT_TOKEN: str = config.tg_bot.token
SERVER: str = config.tg_bot.token

storage = MemoryStorage()
data_base = Database('db_sqlite')
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands="start")
async def process_start_command(message: types.Message):

    photo = InputFile(join("media", "example.png"))
    await message.answer(text=mes['start_message'])
    await asyncio.sleep(2)

    if data_base.check_user_id_exist(message.from_user.id):
        await message.answer(text=mes['auth_message_exist'])

    else:
        await UserState.jira_token.set()  # set state
        await message.answer(text=mes['auth_message'])
        await bot.send_photo(photo=photo, chat_id=message.from_user.id)


# If auth successfully
@dp.message_handler(lambda message: bool(get_username_from_jira(message.text)), state=UserState.jira_token)
async def process_auth_success(message: types.Message, state: FSMContext):
    #  record data to db
    user_data = get_issues_from_jira(token=message.text)

    user_name, display_name = get_username_from_jira(message.text)
    data_base.add_new_row(user_id=message.from_user.id,
                          jira_token=message.text,
                          user_data=user_data,
                          user_name=user_name
                          )

    await state.finish()
    await message.reply(text=f'Аутентификация пройдена, <b>{display_name}</b>!')
    await message.answer(text=mes['auth_success_message'])


# If auth fall
@dp.message_handler(lambda message: not bool(get_username_from_jira(message.text)), state=UserState.jira_token)
async def process_auth_invalid(message: types.Message):

    return await message.reply(text=mes['auth_fall_message'])


@dp.message_handler(commands="del_stop")
async def process_del_command(message: types.Message):
    if data_base.check_user_id_exist(message.from_user.id):
        data_base.del_row(message.from_user.id)
        await message.answer(text=mes['del_yourself_message_true'])
    else:
        await message.answer(text=mes['del_yourself_message_false'])


@dp.message_handler(commands="support")
async def process_del_command(message: types.Message):
    await message.answer('Сообщить о некорректной работе бота\n<a href="https://t.me/two_and_two_isnt_five">Контакт</a>')



@dp.message_handler()
async def send_notification_to_users():
    queue: list = create_list_of_obj_for_output_bot(data_base)
    queue = [dict(s) for s in set(frozenset(d.items()) for d in queue)]  # костыль, убираем дубликаты сообщений
    if queue:
        for obj in queue:
            try:
                await bot.send_message(chat_id=obj['user_id'], text=obj['message'])
            except:
                continue



async def scheduler():
    aioschedule.every(30).seconds.do(send_notification_to_users)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(dp):
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)