import json
import os
import logging
import requests
import sys
import telegram
import time
from dotenv import load_dotenv
from http import HTTPStatus

from custom_exception import DefectsDict, DefectsList, ServerError

load_dotenv()

handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.INFO,
    encoding='utf-8',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    handlers=[handler]
)
logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

PROGRAMM_ERROR = 'Сбой в работе программы: '
API_ERROR = (
    f'{PROGRAMM_ERROR} Эндпоинт {ENDPOINT} недоступен. '
    'Код ответа API: {0}'
)
ERROR = 'Непредвиденная ошибка: {0}'


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщеньку."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение успешно дошло до получателя.')
    except telegram.error.TelegramError:
        logger.error('Сообщение не отправилось')


def get_api_answer(current_timestamp):
    """Берем АРI."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.ConnectionError as connect_error:
        raise logger.error('Ошибка подключения:', connect_error)
    except requests.exceptions.Timeout as timout_error:
        raise logger.error('Время запроса вышло', timout_error)
    except requests.exceptions.RequestException as request_error:
        raise logger.error(request_error)
    if response.status_code != HTTPStatus.OK:
        logger.error(
            f'{PROGRAMM_ERROR}. Эндпоинт {ENDPOINT} недоступен. '
            'Код ответа API: {0}'.format(response.status_code)
        )
        raise ServerError()
    try:
        logger.info('Получен JSON-формат')
        return response.json()
    except json.JSONDecodeError():
        raise logger.error('Полученный ответ не в ожидаемом JSON-формате')


def check_response(respns):
    """Проверка пришедшего АРI-запроса на корректность."""
    if type(respns) is not dict and len(respns) == 0:
        raise DefectsDict(logger.error('Ошибка словаря'))
    elif type(respns['homeworks']) is list and len(respns['homeworks']) == 0:
        raise DefectsList(logger.info('Обновлений нет'))
    logger.info('Получены данные последней работы')
    return respns['homeworks'][0]


def parse_status(homework):
    """Чекаем статус и вообще домашку. При нуле - ничего, а так happy_end."""
    if 'homework_name' not in homework:
        raise KeyError(logger.error('Ошибка ключа \'homework_name\''))
    elif 'status' not in homework:
        raise KeyError(logger.error('Ошибка ключа \'status\''))
    elif homework['status'] not in HOMEWORK_STATUSES:
        raise logger.error('Ошибка статуса')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    logger.info('Получен статус')
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
            logger.error(FAIL_TOKEN.format(index))
            return False
    logger.info('Проверка токенов прошла успешно.')
    return True


def send_error_message(bot, error, pattern, value):
    """
    Функция, возвращающая значение ошибки в случае сбоя.
    Каждая такая ошибка логируется + отправляется смс-уведомление
    пользователю об неисправности (в случае повтора – только один раз).
    """
    if value is None:
        value = pattern.format(error)
        send_message(bot, value)
    time.sleep(RETRY_TIME)
    return value


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit(logger.critical('Аутентификация с треском провалилась'))
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    traceback_value = None
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response['current_date']
            answer = check_response(response)
            message = parse_status(answer)
            send_message(bot, message)
            traceback_value = None
        except ServerError as sv_error:
            traceback_value = send_error_message(
                bot,
                sv_error,
                API_ERROR,
                traceback_value
            )
        except DefectsDict:
            time.sleep(RETRY_TIME)
            continue
        except DefectsList:
            time.sleep(RETRY_TIME)
            continue
        except Exception as error:
            traceback_value = send_error_message(
                bot,
                error,
                ERROR,
                traceback_value
            )
        else:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
