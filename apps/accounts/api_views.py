from django.contrib.auth import authenticate, login, logout
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from .serializers import UserSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        base_request = getattr(request, "_request", request)
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response(
                {"detail": _("Username and password are required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = authenticate(base_request, username=username, password=password)
        if not user:
            return Response(
                {"detail": _("Invalid credentials.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(base_request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        base_request = getattr(request, "_request", request)
        logout(base_request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        base_request = getattr(request, "_request", request)
        user = getattr(base_request, "user", None) or request.user
        return Response(UserSerializer(user).data)


class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class CsrfView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"detail": "CSRF cookie set."})
