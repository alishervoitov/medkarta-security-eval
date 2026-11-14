import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import MedicalRecord, User
from .permissions import IsAdmin, MedicalRecordObjectPermission
from .serializers import MedicalRecordSerializer, UserSerializer

log = logging.getLogger(__name__)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        username = str(request.data.get("username", ""))
        password = str(request.data.get("password", ""))
        fail = Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        user = User.objects.filter(username=username).first()
        now = timezone.now()
        if user and user.locked_until and user.locked_until > now:
            return Response({"detail": "Account temporarily locked."}, status=status.HTTP_403_FORBIDDEN)
        auth = authenticate(request, username=username, password=password) if user else None
        if not auth:
            if user:
                # FAULT F3: the counter is never increased -> lockout never triggers
                user.failed_login_attempts += 0 if "F3" in settings.FAULTS else 1
                if user.failed_login_attempts >= settings.LOCKOUT_ATTEMPTS:
                    user.locked_until = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
                    user.failed_login_attempts = 0
                user.save(update_fields=["failed_login_attempts", "locked_until"])
            return fail
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts", "locked_until"])
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class LogoutView(APIView):
    """The refresh token in the body is the credential, so no access token is required."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "logout"

    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh"))
            token.blacklist()  # absent when the blacklist app is not installed (F1)
        except Exception:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserListView(generics.ListAPIView):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    # FAULT F5: any authenticated user may list users
    permission_classes = [IsAuthenticated] if "F5" in settings.FAULTS else [IsAdmin]


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        email = str(request.data.get("email", ""))
        exists = User.objects.filter(email__iexact=email).exists()
        if exists:
            log.info("password reset requested for an existing account")  # mail sending omitted
        elif "F6" in settings.FAULTS:  # FAULT F6: reveals that the account does not exist
            return Response({"detail": "No such e-mail."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"detail": "If the e-mail exists, a message has been sent."})


class MedicalRecordList(generics.ListAPIView):
    serializer_class = MedicalRecordSerializer

    def get_queryset(self):
        qs = MedicalRecord.objects.order_by("id")
        u = self.request.user
        if u.role == "patient" and "F4" not in settings.FAULTS:  # FAULT F4: no owner filter
            qs = qs.filter(patient__user=u)
        return qs


class MedicalRecordDetail(generics.RetrieveAPIView):
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAuthenticated, MedicalRecordObjectPermission]
    queryset = MedicalRecord.objects.all()

    def get_queryset(self):
        qs = MedicalRecord.objects.all()
        u = self.request.user
        if u.role == "patient" and "F4" not in settings.FAULTS:
            qs = qs.filter(patient__user=u)  # foreign record -> 404 (as in the production system)
        return qs
