import logging
import os
import sys
import time

from dotenv import load_dotenv
from http import HTTPStatus
import requests
from telegram import Bot

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, [%(levelname)s], %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 5
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

messages = {
    'SUCCESS_SEND_MESSAGE': 'Сообщение "{message}" успешно отправлено.',
    'ERROR_SEND_MESSAGE': 'Не удалось отправить сообщение: {error}.',
    'NO_ANSWER': (
        'Сервер не отвечает: {error}\n'
        '{endpoint}, {headers}, {params}.'
    ),
    'REQUEST_FAILD': (
        'Ошибка запроса: {status_code}\n'
        '{endpoint}, {headers}, {params}.'
    ),
    'NO_KEY_ERROR': '"homeworks" отсутствует в списке',
    'VALLUE_TYPE_ERROR': (
        'Ожидаемый тип ключа "homework" - list. '
        'Получен {resp_type}.'
    ),
    'UNKNOWN_HW_STATUS': 'Неожиданный статус проверки {status}. {error}.',
    'HW_STATUS': (
        'Изменился статус проверки работы "{name}". {verdict}'
    ),
    'NO_TOKEN': 'Для переменной окружения {name} значение не задано.',
    'PROGRAMM_ERROR': 'Сбой в работе программы: {error}.',
}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправление в чат новых сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(
            messages['SUCCESS_SEND_MESSAGE'].format(message=message)
        )
    except Exception as error:
        logger.error(
            messages['ERROR_SEND_MESSAGE'].format(error=error),
            exc_info=True
        )
        return error


def get_api_answer(current_timestamp):
    """API запрос к сервису Yandex.Practicum."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.exceptions.RequestException as error:
        logger.error(error)
        raise ConnectionError(messages['NO_ANSWER'].format(
            error=error,
            endpoint=ENDPOINT,
            headers=HEADERS,
            params=params
        ))
    if response.status_code != HTTPStatus.OK:
        raise RuntimeError(messages['REQUEST_FAILD'].format(
            status_code=response.status_code,
            endpoint=ENDPOINT,
            headers=HEADERS,
            params=params
        ))
    return response.json()


def check_response(response):
    """Проверка ответа API Yandex.Practicum на корректность."""
    homework = response['homeworks']
    if 'homeworks' not in response:
        raise ValueError(messages['NO_KEY_ERROR'])
    if not isinstance(homework, list):
        raise TypeError(
            messages['VALLUE_TYPE_ERROR'].format(resp_type=type(homework))
        )
    return homework


def parse_status(homework):
    """Получение статуса от Yandex.Practicum."""
    name = homework.get('homework_name')
    status = homework.get('status')
    try:
        HOMEWORK_VERDICTS[status]
    except ValueError as error:
        logger.error(
            messages['UNKNOWN_HW_STATUS'].format(
                status=homework['status'], error=error
            )
        )
    verdict = HOMEWORK_VERDICTS[status]
    return messages['HW_STATUS'].format(
        name=name, verdict=verdict
    )


def check_tokens():
    """Проверка наличия всех параметров в окружении."""
    veriable_env = ['PRACTICUM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_TOKEN']
    NOT_EXIST_TOKEN_LIST = []
    for name in veriable_env:
        if globals()[name] is None:
            NOT_EXIST_TOKEN_LIST.append(name)
            logger.critical(
                messages['NO_TOKEN'].format(name=name)
            )
    if len(NOT_EXIST_TOKEN_LIST) != 0:
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            print(response['current_date'])
            message = parse_status(check_response(response)[0])
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            message = messages['PROGRAMM_ERROR'].format(error=error)
            logger.error(message, exc_info=True)
        send_message(bot, message)

        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
