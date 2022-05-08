from http import HTTPStatus
import logging
import os
import sys
import time

from dotenv import load_dotenv
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

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
VERIABLE_ENV = ['PRACTICUM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_TOKEN']

SUCCESS_SEND_MESSAGE = 'Сообщение "{message}" успешно отправлено.'
ERROR_SEND_MESSAGE = 'Не удалось отправить сообщение "{message}": {error}.'
NO_ANSWER = (
    'Сервер не отвечает: {error}\n'
    '{url}, {headers}, {params}.'
)
REQUEST_FAILD = (
    'Ошибка запроса: {status_code}\n'
    '{url}, {headers}, {params}.'
)
SERVICE_ERROR = (
    'Ошибка обслуживания: {error}\n'
    '{url}, {headers}, {params}.'
)
NO_KEY_ERROR = '"homeworks" отсутствует в списке'
VALLUE_TYPE_RESP_ERROR = (
    'Ожидаемый тип ключа запроса - dict. '
    'Получен {resp_type}.'
)
VALLUE_TYPE_HW_ERROR = (
    'Ожидаемый тип ключа "homework" - list. '
    'Получен {resp_type}.'
)
UNKNOWN_HW_STATUS = 'Неожиданный статус проверки {status}.'
HW_STATUS = (
    'Изменился статус проверки работы "{name}". {verdict}'
)
NO_TOKEN = 'Для переменных окружения {name} значение не задано.'
PROGRAMM_ERROR = 'Сбой в работе программы: {error}.'


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
            SUCCESS_SEND_MESSAGE.format(message=message)
        )
    except Exception as error:
        logger.error(
            ERROR_SEND_MESSAGE.format(error=error, message=message),
            exc_info=True
        )


def get_api_answer(current_timestamp):
    """API запрос к сервису Yandex.Practicum."""
    params = {'from_date': current_timestamp}
    request_params = dict(
        url=ENDPOINT, headers=HEADERS, params=params
    )
    try:
        response = requests.get(**request_params)
    except requests.exceptions.RequestException as error:
        raise ConnectionError(NO_ANSWER.format(
            error=error,
            **request_params
        ))
    for error in ('code', 'error'):
        if error in response.json():
            raise RuntimeError(SERVICE_ERROR.format(
                error=error,
                **request_params
            ))
    if response.status_code != HTTPStatus.OK:
        raise RuntimeError(REQUEST_FAILD.format(
            status_code=response.status_code,
            **request_params
        ))
    return response.json()


def check_response(response):
    """Проверка ответа API Yandex.Practicum на корректность."""
    if not isinstance(response, dict):
        raise TypeError(
            VALLUE_TYPE_RESP_ERROR.format(resp_type=type(response))
        )
    if 'homeworks' not in response:
        raise ValueError(NO_KEY_ERROR)
    homework = response['homeworks']
    if not isinstance(homework, list):
        raise TypeError(
            VALLUE_TYPE_HW_ERROR.format(resp_type=type(homework))
        )
    return homework


def parse_status(homework):
    """Получение статуса от Yandex.Practicum."""
    name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(
            UNKNOWN_HW_STATUS.format(
                status=homework['status']
            )
        )
    return HW_STATUS.format(
        name=name, verdict=HOMEWORK_VERDICTS[status]
    )


def check_tokens():
    """Проверка наличия всех параметров в окружении."""
    not_exist_token_list = [
        name for name in VERIABLE_ENV if globals()[name] is None
    ]
    if not_exist_token_list:
        logger.critical(
            NO_TOKEN.format(name=not_exist_token_list)
        )
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
            if check_response(response):
                message = parse_status(check_response(response)[0])
                send_message(bot, message)
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            message = PROGRAMM_ERROR.format(error=error)
            logger.error(message, exc_info=True)
            send_message(bot, message)

        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
