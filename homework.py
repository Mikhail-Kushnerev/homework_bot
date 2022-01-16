import json
import os
import logging
import requests
import sys
import telegram
import time
from dotenv import load_dotenv
from http import HTTPStatus

from custom_exception import EmptyDict, ServerError, ListOutOfRange

load_dotenv()

handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.INFO,
    encoding='utf-8',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    handlers=[handler]
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 60 * 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

PROGRAMM_ERROR = 'Сбой в работе программы: '
API_ERROR = (
    f'{PROGRAMM_ERROR} Эндпоинт {ENDPOINT} недоступен. '
    'Код ответа API: {0}'
)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщеньку."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info('Сообщение успешно дошло до получателя.')
    except telegram.error.TelegramError:
        logging.error('Сообщение не отправилось')


def get_api_answer(current_timestamp):
    """Берем АРI."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as request_error:
        raise logging.error(request_error)
    if response.status_code != HTTPStatus.OK:
        logging.error(
            f'{PROGRAMM_ERROR}. Эндпоинт {ENDPOINT} недоступен. '
            'Код ответа API: {0}'.format(response.status_code)
        )
        raise ServerError()
    try:
        return response.json()
    except json.JSONDecodeError():
        logging.error('q')


def check_response(response):
    """Проверка пришедшего АРI-запроса на корректность."""
    if type(response) != dict:
        raise
    elif len(response) == 0:
        raise EmptyDict(logging.info('Пустой словарь!'))
    elif 'homeworks' not in response:
        raise
    elif type(response['homeworks']) != list:
        raise
    elif len(response['homeworks']) == 0:
        raise ListOutOfRange(logging.info('Нет обновлений'))
    return response['homeworks'][0]


def parse_status(homework):
    """Чекаем статус и вообще домашку. При нуле - ничего, а так happy_end."""
    if 'homework_name' not in homework:
        raise KeyError()
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """АУТЕНТИФИКАЦИЯ."""
    params = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    FAIL_TOKEN = (
        "Отсутсвует обязательная переменная окружения: '{0}'\n"
        "Программа принудительно остановлена"
    )
    for index, value in params.items():
        if value is None:
            logging.error(FAIL_TOKEN.format(index))
            return False
    logging.info('Проверка токенов прошла успешно.')
    return True


def send_error_message(bot, error, value):
    """
    Функция, возвращающая значение ошибки в случае сбоя.
    Каждая такая ошибка логируется + отправляется смс-уведомление
    пользователю об неисправности (в случае повтора – только один раз).
    """
    logging.error(f'Ошибка {error}')
    if value is None:
        value = API_ERROR.format(error)
        send_message(bot, value)
    time.sleep(RETRY_TIME)
    return value


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit(logging.critical('Аутентификация с треском провалилась'))
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    traceback_value = None
    while True:
        current_timestamp = int(time.time()) - RETRY_TIME
        try:
            response = check_response(get_api_answer(current_timestamp))
        except ServerError as sv_error:
            traceback_value = send_error_message(
                bot,
                sv_error,
                traceback_value
            )
        except EmptyDict:
            time.sleep(RETRY_TIME)
            continue
        except ListOutOfRange:
            time.sleep(RETRY_TIME)
            continue
        except Exception as error:
            traceback_value = send_error_message(bot, error, traceback_value)
        else:
            send_message(bot, parse_status(response))
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
