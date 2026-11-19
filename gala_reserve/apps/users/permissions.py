from rest_framework.permissions import BasePermission


class IsVerified(BasePermission):
    '''
    Разрешение, проверяющее, что пользователь верифицирован по email.
    '''

    code = 'email_not_verified'

    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'is_email_verified', False))


class IsOwnerOrAdmin(IsVerified):
    '''
    Разрешение, проверяющее, является ли пользователь администратором
    или владельцем объекта.
    '''

    code = 'permission_denied'

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user.is_staff or
            request.user.pk == obj.user_id
        )