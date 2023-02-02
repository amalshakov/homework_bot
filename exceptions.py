class NotFalseError(Exception):
    """Выбрасывает исключение при получении False."""

    pass


class OkStatusError(Exception):
    """Выбрасывает исключение при HTTP статусе отличного от 200."""

    pass


class IncorrectStatusError(Exception):
    """Выбрасывает исключение при получении
    неожиданного статуса домашней работы.
    """

    pass
