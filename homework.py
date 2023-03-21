import logging
import os
import sys
import time
import json
from http import HTTPStatus
from dotenv import load_dotenv

import requests
import telegram

from exceptions import (AnyInvEndpointError, ApiConnectionError,
                        InvalidKeysResponseError, NoStatusResponseError,
                        UnexpectedHmwStatus, ResponseNotJson)

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
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler(sys.stdout)
)


def check_tokens():
    """Проверка доступности переменных."""
    logger.debug('Проверка наличия токенов.')
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug(f'Отправлено сообщение в чат: {message}')
    except telegram.TelegramError as err:
        logger.error(f'Cообщение в чат не отправлено: {err}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params)
    except requests.exceptions.ConnectionError as error:
        raise SystemExit(error)
    except requests.exceptions.Timeout as error:
        raise SystemExit(error)
    except requests.exceptions.RequestException:
        raise ApiConnectionError('Нет подключения к API.')
    except Exception:
        raise AnyInvEndpointError('Сбои при запросе к эндпоинту.')
    if homework_statuses.status_code != HTTPStatus.OK:
        raise ApiConnectionError(f'Api {ENDPOINT} недоступен')
    try:
        return homework_statuses.json()
    except json.decoder.JSONDecodeError:
        raise ResponseNotJson('Не формат JSON.')


def check_response(response):
    """Проверяет ответ API."""
    if type(response) is not dict:
        raise TypeError
    if not response:
        raise NoStatusResponseError('Отсутствуют новые статусы.')
    if 'homeworks' not in response:
        raise InvalidKeysResponseError('В ответе нет ключа "homeworks".')
    if 'current_date' not in response:
        raise InvalidKeysResponseError('В ответе нет ключа "current_date".')
    if type(response.get('homeworks')) is not list:
        raise TypeError('Тип ответа не соотвествует ожидаемому.')
    return response.get('homeworks')


def parse_status(homework):
    """Получает информацию о статусе домашней работы."""
    try:
        homework_name = homework['homework_name']
        hm_status = homework['status']
    except KeyError:
        raise KeyError('Ошибка, несуществующий ключ')
    if hm_status not in HOMEWORK_VERDICTS:
        raise UnexpectedHmwStatus(
            f'Неожиданный статус работы - {hm_status}'
        )
    verdict = HOMEWORK_VERDICTS[hm_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time() / 10)
    status_bot = ''
    last_error = ''
    if not check_tokens():
        logger.critical('Отсутствуют токены!')
        raise SystemExit('Отсутствуют токены!')
    while True:
        try:
            response = get_api_answer(timestamp)
            updates_exist = check_response(response)
            timestamp = response.get('current_date')
            if not updates_exist:
                message = 'Нет домашней работы'
            else:
                message = parse_status(updates_exist[0])
            if status_bot != message:
                send_message(bot, message)
                status_bot = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_error != error:
                send_message(bot, message)
                last_error = error
            logger.exception(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
