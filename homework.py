import logging
import os
import requests
import sys
import time

import exceptions

from dotenv import load_dotenv

from http import HTTPStatus

from telegram import Bot

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='hw_status_bot.log',
    filemode='a'
)

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


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправление в чат новых сообщений."""
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения {error}')
        return error
    logger.info(f'Сообщение "{message}" успешно отправлено.')


def get_api_answer(current_timestamp):
    """API запрос к сервису Yandex.Practicum."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.EndpointHomeworkError
    except exceptions.EndpointHomeworkError:
        message = (
            f'Эндпоинт {ENDPOINT} недоступен.'
            f'Код ответа API: {response.status_code}'
        )
        logger.error(message)
        raise exceptions.EndpointHomeworkError(message)
    except exceptions.ApiHomeworkError as error:
        message = (
            f'Ошибка при запросе к Yandex.Practicum: {error}'
        )
        logger.error(message)
        raise exceptions.ApiHomeworkError(message)
    return response.json()


def check_response(response):
    """Проверка ответа API Yandex.Practicum на корректность."""
    response_values = ['homeworks', 'current_date']
    for value in response_values:
        try:
            response[value]
        except KeyError:
            message = (
                f'Отсутствует ожидаемое значение {value}'
            )
            logger.error(message)
    if isinstance(response['homeworks'], list):
        return response['homeworks']
    else:
        response_type = type(response['homeworks'])
        message = (
            f'Значение запроса "homewroks" {response_type}. '
            'Ожидается "list".'
        )


def parse_status(homework):
    """Проверка полученных статусов от Yandex.Practicum."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        message = (
            f'Домашняя работа {error} отсутствует'
        )
        logger.error(message)
        raise KeyError(message)
    try:
        HOMEWORK_STATUSES[homework_status]
    except KeyError:
        message = (
            f'В полученном ответе неизвестный статус {homework_status}'
        )
        logger.error(message)
        raise KeyError(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия всех параметров в окружении."""
    veriable_env = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
    for parameter in veriable_env:
        try:
            if parameter is None:
                raise exceptions.NoneVeriableError
        except exceptions.NoneVeriableError:
            message = (
                f'Пременная окружения {parameter} отсутствует.'
            )
            logger.critical(message)
            return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit('Переменные окружения не валидны')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework[0])
            if status_message != message:
                status_message = message
                send_message(bot, status_message)
            current_timestamp = response['current_date']
        except IndexError:
            logger.debug('Отсутствует обновлённый статус')
            current_timestamp = response['current_date']
        except Exception as error:
            new_message = f'Сбой в работе программы: {error}'
            logger.error(new_message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
