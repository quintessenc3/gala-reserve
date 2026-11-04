from rest_framework.permissions import BasePermission


class IsVerified(BasePermission):
    '''
    Разрешение, проверяющее, что пользователь верифицирован по email.
    '''

    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'is_email_verified', False))