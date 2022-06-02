import logging
import os

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ParseMode
from aiogram.utils import executor

from solver import get_by_letters, get_by_mask, exclude_by_letters

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.environ.get('API_TOKEN')
bot = Bot(token=API_TOKEN)

# For example use simple MemoryStorage for Dispatcher.
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands='start')
@dp.message_handler(commands='next')
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Conversation's entry point
    """
    await state.finish()

    async with state.proxy() as data:
        data['req'] = ['.', '.', '.', '.', '.']
        data['exclude'] = ""
        data['include'] = ""
        data['words'] = []

    logging.info('User start new word %r', message.chat.username)

    await message.reply("Привет! Введи слово (большая если на своем месте . перед буквой если не на своем месте)", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands='help')
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Help
    """
    await message.reply("Бот который умеет решать wordly. Это игра где загадывают слово из 5 букв и вы подбираете слова. Если вы не угадали букву, напишите ее маленькой буквой. Если буква есть в слове но вы не угадали с позицией то поставьте перед буквой \"-\". А если буква на своем месте напишите ее заглавной.", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler()
async def process_name(message: types.Message, state: FSMContext):
    """
    Calc word
    """
    input_word = message.text

    async with state.proxy() as data:
        input_word = input_word.replace('ё', 'е')
        req = data['req']
        exclude = data['exclude']
        include = data['include']
        words = data['words']
        words.append(input_word)

        counter = 0
        if len(input_word.replace('-', '')) != 5:
            await message.reply("Должно быть 5 букв.\n/help")
            return
        for i in range(5):

            if input_word[counter] == '-':
                counter += 1
                include += input_word[counter]
                if '[^' in req[i]:
                    tmp = req[i].replace('[^', '').replace(']', '')
                    tmp += input_word[counter]
                    req[i] = f'[^{tmp}]'
                else:
                    req[i] = f'[^{input_word[counter]}]'

            elif input_word[counter].isupper():
                req[i] = input_word[counter].lower()
            else:
                exclude += input_word[counter]

            counter += 1

        res = get_by_mask(''.join(req))
        res = get_by_letters(include, res)

        res = exclude_by_letters(exclude, res)

        await state.update_data(req=req)
        await state.update_data(exclude=exclude)
        await state.update_data(include=include)
        await state.update_data(words=words)

        logging.info('Word len %r', len(res))

        await bot.send_message(
            message.chat.id,
            md.text(
                md.text('Маска поиска:', md.escape_md(''.join(req))),
                md.text('Исключенные символы:', md.bold(exclude)),
                md.text('Обязательные символы:', md.bold(include)),
                md.text('История слов:', md.text(
                    *words, sep='\n'), sep='\n'),
                md.text('Получившиеся слова:', md.code(', '.join(res[:60]))),
                sep='\n',
            ),
        )

        if len(res) <= 0:
            await message.reply("Слово не найдено.\n/next")

if __name__ == '__main__':
    # executor.start_polling(dp, skip_updates=True)
    executor.start_polling(dp)
