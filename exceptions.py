class OkStatusError(Exception):
    """Выбрасывает исключение при HTTP статусе отличного от 200."""

    pass


class UnavailableApiError(Exception):
    """Выбрасывает исключение при недоступности API."""

    pass
