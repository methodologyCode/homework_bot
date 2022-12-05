import logging
import os
import sys
import time
import requests
import telegram
from http import HTTPStatus
from logging import Formatter, StreamHandler
from dotenv import load_dotenv

from exceptions import (FailedRequestApi, EnvironMissing,
                        EmptyList, SendMessageError)

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
TELEGRAM_TOKEN = os.getenv('TG_TOKEN', default=None)
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
    """Проверяем переменные окружения."""
    if (TELEGRAM_TOKEN is None or PRACTICUM_TOKEN is None
            or TELEGRAM_CHAT_ID is None):
        logger.critical('Отсутствуют переменные окружения!')
        raise EnvironMissing('Задайте переменные окружения!')

    return True


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

        if response.status_code != HTTPStatus.OK:
            logger.error('Неожиданный статус код!')
            send_message(f'Неожиданный статус код, {response.status_code}')
            raise FailedRequestApi('API недоступен.')

        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f'Сервер вернул ошибку: {e}')
        send_message(f'Сервер вернул ошибку {e}')
        raise FailedRequestApi('Запрос к API провалился.')


def check_response(response):
    """Проверяем ответ от API."""
    if not isinstance(response, dict):
        raise TypeError(
            'Тип данных ответа API не является словарём'
        )

    elif 'homeworks' not in response:
        logger.error(
            'Ключ homeworks отсутствует в ответе API.'
        )
        send_message('Ключ homeworks отсутствует в ответе API.')
        raise KeyError(
            'Ключ homeworks отсутствует в ответе API.'
        )

    elif 'current_date' not in response:
        logger.error(
            'Ключ current_date отсутствует в ответе API.'
        )
        send_message('Ключ current_date отсутствует в ответе API.')
        raise KeyError(
            'Ключ current_date отсутствует в ответе API.'
        )

    homeworks = response['homeworks']

    if not isinstance(homeworks, list):
        raise TypeError(
            'Тип данных ответа API не является cписком.'
        )

    if homeworks:
        return homeworks[0]
    else:
        raise EmptyList('Пустой список домашних работ')


def parse_status(homework):
    """Получение статуса домашней.работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if not homework_name:
        logging.error('Нет нужного ключа {homework_name}')
        send_message('Нет нужного ключа - {homework_name}')
        raise KeyError('Нет нужного ключа {homework_name}')

    if homework_status not in HOMEWORK_VERDICTS:
        logging.error(f'Неожиданный статус {homework_status}')
        send_message(f'Неожиданный статус {homework_status}')
        raise KeyError(f'Неверный статус работы: {homework_status}')

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    homework_status = ''

    while check_tokens():
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                hw_status = parse_status(homework)
                if hw_status == homework_status:
                    send_message(f'Без обновлений: {hw_status}')
                    logger.debug(f'Статус не обновлён: {hw_status}')
                else:
                    homework_status = hw_status
                    send_message(bot, f'Обновлён {homework_status}')
                    logger.debug(f'Статус обновлён: {homework_status}')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
