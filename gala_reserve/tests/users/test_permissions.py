from types import SimpleNamespace

import pytest
from apps.users.permissions import IsOwnerOrAdmin, IsVerified
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

factory = APIRequestFactory()


@pytest.fixture
def mock_view():
    class MockView(RetrieveAPIView):
        def get_object(self):
            obj = SimpleNamespace(user_id=1)
            self.check_object_permissions(self.request, obj)
            return obj

        def retrieve(self, request, *args, **kwargs):
            obj = self.get_object()
            return Response({"obj_user_id": obj.user_id})

    return MockView


def make_get_request(user_for_request):
    request = factory.get("/")
    force_authenticate(request, user=user_for_request)
    return request


class TestIsVerified:
    @pytest.fixture(autouse=True)
    def _use_permission(self, mock_view):
        mock_view.permission_classes = [IsVerified]

    @pytest.mark.parametrize("is_email_verified, expected", [
            (True, status.HTTP_200_OK),
            (False, status.HTTP_403_FORBIDDEN),  
        ],
        ids=["verified", "not_verified"],
    )
    def test_permission(self, user, mock_view, is_email_verified, expected):
        user.is_email_verified = is_email_verified
        response = mock_view.as_view()(make_get_request(user))
        assert response.status_code == expected


class TestIsOwnerOrAdmin:
    @pytest.fixture(autouse=True)
    def _use_permission(self, mock_view):
        mock_view.permission_classes = [IsOwnerOrAdmin]

    @pytest.mark.parametrize('is_email_verified, expected', [
        (True, status.HTTP_200_OK),
        (False, status.HTTP_403_FORBIDDEN)
    ])
    def test_has_permission(self, user, mock_view, is_email_verified, expected):
        user.is_email_verified = is_email_verified
        user.pk = 1
        response = mock_view.as_view()(make_get_request(user))
        assert response.status_code == expected

    @pytest.mark.parametrize(
        "is_staff, pk, expected",
        [
            (True, 99, status.HTTP_200_OK),
            (False, 1, status.HTTP_200_OK),
            (True, 1, status.HTTP_200_OK),
            (False, 2, status.HTTP_403_FORBIDDEN),
        ],
        ids=["admin", "owner", "admin_and_owner", "stranger"],
    )
    def test_has_object_permission(self, user, mock_view, is_staff, pk, expected):
        user.is_email_verified = True
        user.is_staff = is_staff
        user.pk = pk

        response = mock_view.as_view()(make_get_request(user))

        assert response.status_code == expected