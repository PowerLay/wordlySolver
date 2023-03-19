import logging
import os
import random
import re

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ParseMode, BotCommand
from aiogram.utils import executor
from dotenv import load_dotenv

from solver import get_by_letters, get_by_mask, exclude_by_letters, get_letters_from_words, generate_rus_5

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )
# Load the environment variables from the .env file
load_dotenv()
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = Bot(token=API_TOKEN)
# bot = Bot(token=API_TOKEN, proxy=PROXY_URL)
#bot = Bot(token=API_TOKEN, session=session)
# PROXY_URL = os.environ.get('PROXY_URL')

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

    # get top words
    top_words = get_by_mask('.....')
    top_words = remove_repeating_letters(top_words)

    top_letters = get_top_letters(top_words)
    top_words = sorted(top_words, key=lambda x: sum([1 if c in top_letters else 0 for c in x]), reverse=True)


    await message.reply("Привет! Введи слово (большая если на своем месте \"-\" перед буквой если не на своем месте)\n\nЛучше начать с %s" % top_words[0],
                        reply_markup=types.ReplyKeyboardRemove())


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
    input_words = message.text

    async with state.proxy() as data:
        try:
            req = data['req']
        except KeyError:
            req = ['.', '.', '.', '.', '.']
        pass
        exclude = data['exclude']
        include = data['include']
        words = data['words']

        for input_word in input_words.split('\n'):
            input_word = input_word.replace('ё', 'е')
            if len(input_word.replace('-', '')) != 5:
                await message.reply("Должно быть 5 букв.\n/help")
                return

            words.append(input_word)

            counter = 0
            for i in range(5):

                if input_word[counter] == '-':
                    counter += 1
                    include += input_word[counter]
                    include = ''.join(set(include))
                    req[i] = set_exclude_mask(input_word[counter], req[i])

                elif input_word[counter].isupper():
                    req[i] = input_word[counter].lower()
                    include += input_word[counter].lower()
                    include = ''.join(set(include))
                else:
                    exclude += input_word[counter]
                    exclude = ''.join(set(exclude))
                    req[i] = set_exclude_mask(input_word[counter], req[i])

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
        logging.info('Word len %r', len(res))
        if len(res)> max_words:
            out_res = remove_repeating_letters(res)
        else:
            out_res = res

        logging.info('Word len new %r', len(out_res))

        # Составление слов в которых есть самые частые буквы из out_res
        scored_words = {}
        words_by_score = get_by_mask('.....')
        tmp_top_letters = get_top_letters(out_res)

        for word in words_by_score:
            scored_words[word] = 0
            for c in word:

                if c in include:
                    scored_words[word] -= 1
                elif c in exclude:
                    scored_words[word] -= 1
                else:
                    scored_words[word] += tmp_top_letters[c] * 2

                if word.count(c) > 1:
                    scored_words[word] -= 1000


        # words = sorted(words, key=lambda x: sum([top_letters[c] for c in x]), reverse=True)
        words_by_score = sorted(words_by_score, key=lambda x: scored_words[x], reverse=True)
        for word in words_by_score[:10]:
            print(word, scored_words[word])

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
                md.text('\nСлова для уточнения:', md.text(', '.join(words_by_score[:10]))),
                sep='\n',
            ),
        )

        if len(res) <= 0:
            await message.reply("Слово не найдено.\n/next")

def remove_repeating_letters(res):
    out_res = []
    for w in res:
        for c in w:
            if w.count(c) > 1:
                break
        else:
            out_res.append(w)
    return out_res

def get_top_letters(res):
    # count letters at res
        letters = {}
        # set letters by kirillic
        for c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя-':
            letters[c] = 0

        for w in res:
            for c in w:
                if c in letters:
                    letters[c] += 1
        # letters = sorted(letters.items(), key=lambda x: x[1], reverse=True)
        return letters

def set_exclude_mask(input_char, current_mask_char):
    if '[^' in current_mask_char:
        tmp = current_mask_char.replace('[^', '').replace(']', '')
        tmp += input_char
        tmp = ''.join(set(tmp))
        return '[^{}]'.format(tmp)
    elif not '.' in current_mask_char:
        return current_mask_char
    else:
        return '[^{}]'.format(input_char)

async def setup_bot_commands(dp):
    bot_commands = [
        types.BotCommand(command="/help", description="Помощь"),
        types.BotCommand(command="/next", description="Следующее слово"),
        types.BotCommand(command="/start", description="Начать заново"),
    ]
    await bot.set_my_commands(bot_commands)

if __name__ == '__main__':
    # generate_rus_5()
    # executor.start_polling(dp, skip_updates=True)
    executor.start_polling(dp, on_startup=setup_bot_commands)
