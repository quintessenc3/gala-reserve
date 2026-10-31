from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import set_rollback

from apps.core.exceptions import DomainError


def exception_handler(exc, context):
    response = {
        "error": {
            "code": None,
            "message": None,
            "details": None
        }
    }
    response_error = response['error']
    headers = {}
    status_code = None

    if isinstance(exc, Http404):
        exc = exceptions.NotFound(*(exc.args))
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied(*(exc.args))

    if isinstance(exc, exceptions.APIException):
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header

        if isinstance(exc.detail, (list, dict)):
            response_error['details'] = exc.detail
        else:
            response_error['message'] = exc.detail

        response_error['code'] = exc.default_code
        status_code = exc.status_code
    elif isinstance(exc, DomainError):
        status_code = exc.http_status
        response_error['code'] = exc.code
        response_error['message'] = exc.message
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        response_error['code'] = 'internal_error'
        response_error['message'] = 'Internal server error'

    retry_after = getattr(exc, 'wait', None) or getattr(exc, 'retry_after', None)

    if retry_after:
        wait_time = str(retry_after)
        
        headers['Retry-After'] = wait_time
        response_error['retry_after'] = wait_time

    set_rollback()

    return Response(response, status=status_code, headers=headers)