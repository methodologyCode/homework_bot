import logging
import os
import sys
import time
from http import HTTPStatus
from logging import Formatter, StreamHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (FailedRequestApi, EnvironMissing,
                        EmptyList, SendMessageError, JsonError)

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = Formatter(
    '{asctime}, {levelname}, {message}', style='{'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN', default=None)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', default=None)
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', default=None)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка переменных окружения."""
    if all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        return True
    logger.critical('Отсутствуют переменные окружения!')
    raise EnvironMissing('Задайте переменные окружения!')


def send_message(bot, message):
    """Отправление сообщений в Телеграмм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Отправлено сообщение: {message}')
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')
        raise SendMessageError(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делаем запрос к API Практикум.Домашка."""
    payload = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.exceptions.RequestException as e:
        raise FailedRequestApi(f'Запрос к API провалился: {e}, {payload}')

    if response.status_code != HTTPStatus.OK:
        raise FailedRequestApi(f'Cтатус: {response.status_code}, {payload}')

    try:
        return response.json()
    except ValueError:
        raise JsonError('Ошибка при декодировании json в словарь.')


def check_response(response):
    """Проверяем ответ от API."""
    if not isinstance(response, dict):
        raise TypeError(
            'Тип данных ответа API не является словарём'
        )

    if 'homeworks' not in response:
        raise KeyError(
            'Ключ homeworks отсутствует в ответе API.'
        )

    if 'current_date' not in response:
        raise KeyError(
            'Ключ current_date отсутствует в ответе API.'
        )

    homeworks = response['homeworks']

    if not isinstance(homeworks, list):
        raise TypeError(
            'Ожидаемый тип данных - Список.'
        )

    if not homeworks:
        raise EmptyList('Пустой список домашних работ')
    return homeworks[0]


def parse_status(homework):
    """Получение статуса домашней.работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if not homework_name:
        raise KeyError('Нет нужного ключа {homework_name}')

    if not homework_status:
        raise KeyError('Нет нужного ключа {homework_status}')

    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Неверный статус работы: {homework_status}')

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    homework_status = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                hw_status = parse_status(homework)
                if hw_status == homework_status:
                    logger.debug(f'Статус не обновлён: {hw_status}')
                else:
                    homework_status = hw_status
                    send_message(bot, f'Обновлён {homework_status}')
                    logger.debug(f'Статус обновлён: {homework_status}')

        except telegram.error.TelegramError as error:
            message = f'Сбой при отправке сообщения в телеграмм: {error}'
            logger.error(message, exc_info=True)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
