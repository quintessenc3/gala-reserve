from rest_framework.permissions import BasePermission, IsAuthenticated


class IsVerified(BasePermission):
    '''
    Разрешение, проверяющее, что пользователь верифицирован по email.
    '''

    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'is_email_verified', False))


class IsOwnerOrAdmin(IsAuthenticated):
    '''
    Разрешение, проверяющее, является ли пользователь администратором
    или владельцем объекта.
    '''

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user.is_staff or
            request.user.pk == obj.user_id
        )