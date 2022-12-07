class EnvironMissing(Exception):
    """Исключение для переменных окружения."""
    pass


class FailedRequestApi(Exception):
    """Исключение для неудачного запроса."""
    pass


class MissingKeyException(Exception):
    """Отсутствие нужного ключа."""
    pass


class EmptyList(Exception):
    """Пустой список."""
    pass


class SendMessageError(Exception):
    """Ошибка при отправке сообщения."""
    pass


class JsonError(Exception):
    """Ошибка при работе с методом json()."""
    pass
