class EnvironMissing(Exception):
    """Исключения для переменных окружения."""
    pass


class FailedRequestApi(Exception):
    """Исключение для неудачного запроса."""
    pass


class MissingKeyException(Exception):
    """Отсутствие нужный ключей."""
    pass


class EmptyList(Exception):
    """Пустой список."""
    pass


class SendMessageError(Exception):
    """Ошибка при отправке сообщения."""
    pass
