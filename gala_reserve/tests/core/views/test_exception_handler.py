from apps.core import error_codes
from apps.core.exceptions import DomainError
from apps.core.views import exception_handler
from rest_framework import exceptions, status


def test_response_format():
    exc = exceptions.NotFound()
    response = exception_handler(exc, {})

    assert response.status_code == status.HTTP_404_NOT_FOUND

    response_data = response.data
    
    assert 'error' in response_data

    assert 'code' in response_data['error']
    assert 'message' in response_data['error']
    assert 'details' in response_data['error']

    assert response_data['error']['code'] == exc.default_code
    assert response_data['error']['message'] == exc.default_detail
    assert response_data['error']['details'] == None


def test_domain_error_handling():
    class InvalidCode(DomainError):
        code = error_codes.INVALID_CODE
        message = 'Вы предоставили неверный верификационный код.'
        http_status = status.HTTP_400_BAD_REQUEST

    response = exception_handler(InvalidCode(), {})

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    response_data = response.data
    
    assert response_data['error']['code'] == InvalidCode.code
    assert response_data['error']['message'] == InvalidCode.message


def test_exc_with_retry_after():
    exc = exceptions.Throttled(wait=60)
    response = exception_handler(exc, {})

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    response_data = response.data 

    assert 'retry_after' in response_data['error']
    assert response_data['error']['retry_after'] == '60'
    assert 'Retry-After' in response.headers
    assert response.headers['Retry-After'] == '60'


def test_handle_unhandled_exc():
    exc = Exception()
    response = exception_handler(exc, {})
    
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR