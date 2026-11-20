from rest_framework.permissions import BasePermission


class IsTicketEventOwnerOrAdmin(BasePermission):
    '''
    Разрешение, проверяющее, что мероприятие билета
    принадлежит владельцу мероприятия или пользователь
    является администратором.
    '''

    def has_object_permission(self, request, view, obj):
        if not request.user:
            return False

        if request.user.is_staff == True:
            return True

        event = getattr(obj, 'event', None)
        if not event:
            return False

        event_user_id = getattr(event, 'user_id', None)
        return request.user.pk == event_user_id