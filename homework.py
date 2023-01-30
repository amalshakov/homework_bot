import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import NotNoneException

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

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='program.log',
    filemode='a'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if TELEGRAM_CHAT_ID is None:
        logger.critical(
            'Отсутствует обязательная переменная окружения: '
            '"TELEGRAM_CHAT_ID". Программа принудительно остановлена.'
        )
        raise NotNoneException(
            'Отсутствует обязательная переменная окружения: '
            '"TELEGRAM_CHAT_ID". Программа принудительно остановлена.'
        )
    if PRACTICUM_TOKEN is None:
        logger.critical(
            'Отсутствует обязательная переменная окружения: '
            '"PRACTICUM_TOKEN". Программа принудительно остановлена.'
        )
        raise NotNoneException(
            'Отсутствует обязательная переменная окружения: '
            '"PRACTICUM_TOKEN". Программа принудительно остановлена.'
        )
    if TELEGRAM_TOKEN is None:
        logger.critical(
            'Отсутствует обязательная переменная окружения: '
            '"TELEGRAM_TOKEN". Программа принудительно остановлена.'
        )
        raise NotNoneException(
            'Отсутствует обязательная переменная окружения: '
            '"TELEGRAM_TOKEN". Программа принудительно остановлена.'
        )


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение в Telegram успешно отправлено')
    except Exception as error:
        logger.error(f'Cбой при отправке сообщения в Telegram. {error}')


def get_api_answer(timestamp):
    """Делает запрос к API и возвращает ответ."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logger.error('API домашки возвращает код, отличный от 200')
            raise Exception('API домашки возвращает код, отличный от 200')
        if response.json().get('homeworks') == []:
            logger.debug('Отсутствие новых статусов в ответе API')
        return response.json()
    except requests.RequestException as error:
        logger.error(f'Cбой при запросе к API. {error}')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    check_dict = isinstance(response, dict)
    if check_dict is False:
        logger.error('Ответ API не соответствует ожидаемым типам данных')
        raise TypeError('Ответ API не соответствует ожидаемым типам данных')
    check_list = isinstance(response.get('homeworks'), list)
    if check_list is False:
        logger.error('Ответ API не соответствует ожидаемым типам данных')
        raise TypeError('Ответ API не соответствует ожидаемым типам данных')
    if (response.get('homeworks') is None
            or response.get('current_date') is None):
        logger.error('Отсутствуют ожидаемые ключи в ответе API')
        raise AssertionError('Отсутствуют ожидаемые ключи в ответе API')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой.
    работы и возвращает ответ для телеграма
    """
    if homework.get('homework_name') is None:
        logger.error('в ответе API домашки нет ключа "homework_name"')
        raise AssertionError('в ответе API домашки нет ключа "homework_name"')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        logger.error(
            'Неожиданный статус домашней работы, обнаруженный в ответе API'
        )
        raise AssertionError(
            'Неожиданный статус домашней работы, обнаруженный в ответе API'
        )
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            homeworks = get_api_answer(timestamp)
            check_response(homeworks)
            homework = homeworks['homeworks'][0]
            send_message(bot, parse_status(homework))

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
