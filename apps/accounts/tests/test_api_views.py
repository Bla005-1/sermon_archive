from types import SimpleNamespace
from unittest import mock

from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts import api_views


factory = APIRequestFactory()


def test_login_requires_credentials():
    request = factory.post("/api/login", data={}, format="json")
    response = api_views.LoginView.as_view()(request)

    assert response.status_code == 400
    assert "required" in response.data["detail"].lower()


def test_login_authenticates_and_serializes_user():
    user = SimpleNamespace(username="tester")
    serializer = mock.Mock()
    serializer.data = {"username": "tester"}

    request = factory.post("/api/login", data={"username": "tester", "password": "pw"}, format="json")
    with mock.patch.object(api_views, "authenticate", return_value=user), \
         mock.patch.object(api_views, "login") as login_mock, \
         mock.patch.object(api_views, "UserSerializer", return_value=serializer):
        response = api_views.LoginView.as_view()(request)

    login_mock.assert_called_once_with(request, user)
    assert response.status_code == 200
    assert response.data == {"username": "tester"}


def test_login_rejects_invalid_credentials():
    request = factory.post("/api/login", data={"username": "tester", "password": "pw"}, format="json")
    with mock.patch.object(api_views, "authenticate", return_value=None):
        response = api_views.LoginView.as_view()(request)

    assert response.status_code == 400
    assert "invalid" in response.data["detail"].lower()


def test_logout_clears_session():
    request = factory.post("/api/logout", data={}, format="json")
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))

    with mock.patch.object(api_views, "logout") as logout_mock:
        response = api_views.LogoutView.as_view()(request)

    logout_mock.assert_called_once_with(request)
    assert response.status_code == 204


def test_me_and_refresh_return_serialized_user():
    user = SimpleNamespace(username="tester")
    serializer = mock.Mock()
    serializer.data = {"username": "tester"}

    refresh_request = factory.get("/api/refresh")
    refresh_request.user = user

    with mock.patch.object(api_views, "UserSerializer", return_value=serializer):
        refresh_response = api_views.RefreshView.as_view()(refresh_request)

    assert refresh_response.status_code == 200
    assert refresh_response.data == {"username": "tester"}

    me_request = factory.get("/api/me")
    force_authenticate(me_request, user=user)
    with mock.patch.object(api_views, "UserSerializer", return_value=serializer):
        me_response = api_views.MeView.as_view()(me_request)

    assert me_response.status_code == 200
    assert me_response.data == {"username": "tester"}
