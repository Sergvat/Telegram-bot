class ApiConnectionError(Exception):
    """Нет подключения к API."""


class AnyInvEndpointError(Exception):
    """Другие сбои при запросе к эндпоинту."""


class InvalidKeysResponseError(Exception):
    """Отсутствие ожидаемых ключей в ответе API."""


class NoStatusResponseError(Exception):
    """Отсутствие в ответе новых статусов."""


class UnexpectedHmwStatus(Exception):
    """Неожиданный статус домашней работы."""

class ResponseNotJson(Exception):
    """Ответ не в формате JSON."""