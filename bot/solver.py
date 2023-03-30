import random
import re
from xml.etree.ElementInclude import include
from pymorphy2 import MorphAnalyzer


def generate_rus_5(file='russian.txt'):
    f = open(file, "r", encoding='windows-1251')
    out = open('dict_5_big.txt', 'w', encoding='utf-8')

    # Фильтруем список слов с помощью морфологического анализатора
    morph = MorphAnalyzer()
    filtered_words = []

    for word in f:
        word = word.replace('\n', '')
        if len(word) == 5:
            parsed_word = morph.parse(word)[0]
            # skip if not in alphabetic

            if len([c for c in word if c.isalpha()]) != len(word):
                continue
            word = word.lower()
            if 'NOUN' in parsed_word.tag and 'sing' in parsed_word.tag and 'nomn' in parsed_word.tag:
                filtered_words.append(word)
                out.write(word + '\n')

    print("Total words:", len(filtered_words))

    # print 10 random words
    for i in range(10):
        print(random.choice(filtered_words))


def get_by_mask(mask: str, file='dict_5_big.txt'):
    res = []
    for line in open(file, "r", encoding='utf-8'):
        res += re.findall(mask, line.replace('\n', ''))
    return res


def get_letters_from_words(words_arr):
    res = ''
    for word in words_arr:
        for c in word:
            if not c in res:
                res += c
    return res


def get_by_letters(letters: str, arr):
    res = []
    for str in arr:
        good = True
        for c in letters:
            if not c in str.lower():
                good = False
        if good:
            res.append(str)
    return res


def exclude_by_letters(letters: str, arr):
    res = []
    for str in arr:
        good = True
        for c in letters:
            if c in str.lower():
                good = False
        if good:
            res.append(str)
    return res


# generate_rus_5()
# req = ['.', '.', '.', '.', '.']
# exclude = ""
# include = ""

# while(True):
#     input_word = input(
#         'Отправь пустую строчку для нового раунда\nВведи слово (большая на своем месте _ перед буквой не на своем месте)\n> ')
#     if len(input_word) == 0:
#         req = ['.', '.', '.', '.', '.']
#         exclude = ""
#         include = ""
#         print('\n--------------- Новое слово ---------------\n')
#         continue

#     input_word = input_word.replace('ё', 'е')

#     counter = 0
#     for i in range(5):

#         if input_word[counter] == '_':
#             counter += 1
#             include += input_word[counter]
#             if '[^' in req[i]:
#                 tmp = req[i].replace('[^', '').replace(']', '')
#                 tmp += input_word[counter]
#                 req[i] = f'[^{tmp}]'
#             else:
#                 req[i] = f'[^{input_word[counter]}]'

#         elif input_word[counter].isupper():
#             req[i] = input_word[counter].lower()
#         else:
#             exclude += input_word[counter]

#         counter += 1

#     res = get_by_mask(''.join(req))
#     # print(res)
#     res = get_by_letters(include, res)
#     # print(res)

#     res = exclude_by_letters(exclude, res)
#     print(res)
