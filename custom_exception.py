class EmptyDict(Exception):
    """Исключение, если у пришедшего АРI-запроса ничего нет."""

    pass


class ServerError(Exception):
    """Исключение, если битая ссылка."""

    pass


class ListOutOfRange(Exception):
    """Исключение, если нет новых сообщений."""

    pass
