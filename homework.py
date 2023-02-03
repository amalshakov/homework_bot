import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import OkStatusError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if not all([TELEGRAM_CHAT_ID, PRACTICUM_TOKEN, TELEGRAM_TOKEN]):
        message_error = (
            'Отсутствует обязательная переменная окружения. '
            'Программа принудительно остановлена.'
        )
        logging.critical(message_error)
        sys.exit(message_error)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    logging.debug('Отправка сообщения в Telegram чат.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logging.error(
            f'Cбой при отправке сообщения в Telegram. {error}',
            exc_info=True
        )
    else:
        logging.debug('Сообщение в Telegram успешно отправлено.')


def get_api_answer(timestamp):
    """Делает запрос к API и возвращает ответ."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise ValueError(
            f'Cбой при запросе к API: {error}. '
            f'Параметры запроса: {ENDPOINT}; {HEADERS}; {payload}.'
        )
    except Exception as error:
        raise Exception(
            f'Cбой при запросе к API: {error}. '
            f'Параметры запроса: {ENDPOINT}; {HEADERS}; {payload}.'
        )
    if response.status_code != HTTPStatus.OK:
        raise OkStatusError(
            f'API домашки возвращает код, отличный от 200. '
            f'Текст ответа: {response}. '
            f'Параметры запроса: {ENDPOINT}; {HEADERS}; {payload}.'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не соответствует ожидаемым типам данных')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Ответ API не соответствует ожидаемым типам данных')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('Отсутствуют ожидаемые ключи в ответе API')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой.
    работы и возвращает str - ответ для телеграма
    """
    if not homework.get('homework_name'):
        raise KeyError('в ответе API домашки нет ключа "homework_name"')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(
            'Неожиданный статус домашней работы, обнаруженный в ответе API'
        )
    return (f'Изменился статус проверки работы "{homework_name}". '
            f'"{HOMEWORK_VERDICTS[status]}')


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    message = None

    while True:
        try:
            homeworks = get_api_answer(timestamp)
            check_response(homeworks)
            timestamp = homeworks.get('current_date')
            print(timestamp)
            if homeworks.get('homeworks') == []:
                new_message = 'Список домашних работ на данный момент пуст'
            else:
                homework = homeworks['homeworks'][0]
                new_message = parse_status(homework)
            if message != new_message:
                message = new_message
                send_message(bot, message)
            logging.debug(message)
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}', exc_info=True)
            if message != f'Сбой в работе программы: {error}':
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
