class DefectsDict(Exception):
    """Исключение, если у пришедшего АРI-запроса ничего нет."""

    pass


class DefectsList(Exception):
    """Исключение, если нет новых сообщений."""

    pass


class ServerError(Exception):
    """Исключение, если битая ссылка."""

    pass
