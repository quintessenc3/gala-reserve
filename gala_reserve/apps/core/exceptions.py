from django.http import Http404, JsonResponse
from rest_framework import exceptions


class DomainError(Exception):
    '''
    Базовый класс для бизнес-ошибок.
    '''

    code: int
    message: str
    http_status: int

    def __init__(self, *args, **kwargs):
        super().__init__(self.message)


def django_exc_handler_stub(request, exc=None):
    '''
    Заглушка для handler- функций в URLConf Django.
    '''

    from apps.core.views import exception_handler

    if isinstance(exc, Http404):
        exc = exceptions.NotFound(
            detail="Not found",
            code="not_found",
        )
    else:
        exc = exceptions.APIException(
            detail="Internal server error.",
            code="internal_error",
        )

    response = exception_handler(
        exc,
        context={"request": request, "view": None},
    )

    headers = {
        key: value
        for key, value in response.items()
        if key.lower() != "content-type"
    }

    return JsonResponse(
        response.data,
        status=response.status_code,
        headers=headers,
    )