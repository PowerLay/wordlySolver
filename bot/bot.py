import logging
import os
import random
import re

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ParseMode
from aiogram.utils import executor
from dotenv import load_dotenv

from solver import get_by_letters, get_by_mask, exclude_by_letters, get_letters_from_words

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )
# PROXY_URL = os.environ.get('PROXY_URL')
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = Bot(token=API_TOKEN)
# bot = Bot(token=API_TOKEN, proxy=PROXY_URL)
#bot = Bot(token=API_TOKEN, session=session)

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

    await message.reply("Привет! Введи слово (большая если на своем месте \"-\" перед буквой если не на своем месте)", reply_markup=types.ReplyKeyboardRemove())


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
        try:
            req = data['req']
        except KeyError:
            req = ['.', '.', '.', '.', '.']
        pass
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
                    req[i] = '[^{}]'.format(tmp)
                else:
                    req[i] = '[^{}]'.format(input_word[counter])

            elif input_word[counter].isupper():
                req[i] = input_word[counter].lower()
                include += input_word[counter].lower()
            else:
                exclude += input_word[counter]

            counter += 1
        if include:
            exclude = re.sub('[{}]'.format(include), '', exclude)

        res = get_by_mask(''.join(req))
        res = get_by_letters(include, res)
        res = exclude_by_letters(exclude, res)

        await state.update_data(req=req)
        data['exclude'] = exclude
        data['include'] = include
        await state.update_data(words=words)

        max_words = 90
        out_res = []
        logging.info('Word len %r', len(res))
        if len(res)> max_words:
            for w in res:
                for c in w:
                    if w.count(c) > 1:
                        break
                else:
                    out_res.append(w)
        else:
            out_res = res

        logging.info('Word len new %r', len(out_res))

        best_words_to_write = get_by_mask('.....')
        best_words_to_write = exclude_by_letters(exclude, best_words_to_write)
        best_words_to_write = exclude_by_letters(include, best_words_to_write)
        # best_words_to_write = get_by_letters(get_letters_from_words(res), best_words_to_write)

        logging.info('Best word len %r', len(best_words_to_write))
        best_words_to_write_res = []
        if len(best_words_to_write)> max_words:
            for w in best_words_to_write:
                for c in w:
                    if w.count(c) > 1:
                        break
                else:
                    best_words_to_write_res.append(w)
        else:
            best_words_to_write_res = res
        logging.info('Best word new len %r', len(best_words_to_write_res))

        # count letters at out_res
        letters = {}
        for w in out_res:
            for c in w:
                if c in letters:
                    letters[c] += 1
                else:
                    letters[c] = 1

        # get 10 words with most letters
        best_words_to_write_res = sorted(best_words_to_write_res, key=lambda x: sum([letters[c] for c in x]), reverse=True)

        if len(best_words_to_write_res) > max_words:
            best_words_to_write_res = best_words_to_write_res[:10]

        # # get 10 random words from best_words_to_write_res
        # if len(best_words_to_write_res) > 10:
        #     best_words_to_write_res = random.sample(best_words_to_write_res, 10)

        await bot.send_message(
            message.chat.id,
            md.text(
                md.text('Маска поиска:', ''.join(req)),
                md.text('Исключенные символы:', exclude),
                md.text('Обязательные символы:', include),
                md.text('История слов:', md.text(
                    *words, sep='\n'), sep='\n'),
                md.text('Всего найдено:', len(res)),
                md.text('С уникальными буквами:', len(out_res)),
                md.text('Выводится:', min(len(out_res),max_words)),
                md.text('Получившиеся слова:', md.text(', '.join(out_res[:max_words]))),
                md.text('Лучше попробовать эти слова:', md.text(', '.join(best_words_to_write_res[:max_words]))),
                sep='\n',
            ),
        )

        if len(res) <= 0:
            await message.reply("Слово не найдено.\n/next")

if __name__ == '__main__':
    # Load the environment variables from the .env file
    load_dotenv()
    # executor.start_polling(dp, skip_updates=True)
    executor.start_polling(dp)
