class EndpointHomeworkError(Exception):
    """Эндпоинт Yandex.Practicum недоступен."""

    pass


class ApiHomeworkError(Exception):
    """Ошибка обращения к API Yandex.Practicum."""

    pass


class NoneVeriableError(Exception):
    """Ошибка наличия переменных окружения."""

    pass


class VallueError(Exception):
    """Недокументированный статус домашней работы в ответе API."""

    pass
