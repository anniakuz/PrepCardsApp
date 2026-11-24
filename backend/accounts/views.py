import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import get_profile
from .serializers import ProfileUpdateSerializer, RegisterSerializer, UserSerializer

User = get_user_model()
logger = logging.getLogger("prepcards.auth")


class SafeTokenRefreshView(TokenRefreshView):
    """Si el usuario del token ya no existe (por ejemplo, base de datos reiniciada) devuelve 401 en vez de 500."""

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except User.DoesNotExist:
            raise InvalidToken("El usuario de este token ya no existe")


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class LoginView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class LogoutView(APIView):
    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh")).blacklist()
        except TokenError:
            return Response({"detail": "Token no válido"}, status=status.HTTP_400_BAD_REQUEST)
        logger.info("logout user=%s", request.user.pk)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if "email" in data:
            email = data.pop("email")
            if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
                return Response({"email": ["Ya existe una cuenta con este email"]}, status=status.HTTP_400_BAD_REQUEST)
            request.user.email = email
            request.user.save(update_fields=["email"])
        for field in ("first_name", "last_name"):
            if field in data:
                setattr(request.user, field, data.pop(field).strip())
                request.user.save(update_fields=[field])
        profile = get_profile(request.user)
        for field, value in data.items():
            setattr(profile, field, value)
        profile.save()
        return Response(UserSerializer(request.user).data)


class DeleteAccountView(APIView):
    """Derecho de supresión. Pide la contraseña y borra la cuenta con todos sus datos."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        if not request.user.check_password(str(request.data.get("password") or "")):
            return Response({"password": ["La contraseña no es correcta"]}, status=status.HTTP_400_BAD_REQUEST)
        pk = request.user.pk
        request.user.delete()
        logger.info("account deleted user=%s", pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExportDataView(APIView):
    """Derecho de acceso y portabilidad. Devuelve los datos del usuario en JSON."""

    def get(self, request):
        user = request.user
        profile = get_profile(user)
        data = {
            "usuario": UserSerializer(user).data,
            "aceptacion_terminos": {"fecha": profile.terms_accepted_at, "version": profile.terms_version},
            "temas_creados": list(user.created_topics.values("name", "visibility", "created_at")),
            "respuestas": list(user.reviews.values("question__text", "is_correct", "level", "created_at")),
            "preguntas_guardadas": list(user.saved_questions.values("question__text", "created_at")),
            "mensajes_chatbot": list(user.assistant_messages.values("question__text", "role", "text", "created_at")),
            "ofertas": list(user.offers.values("title", "company", "raw_text", "created_at")),
            "mentorias": list(
                user.mentors.values("mentor__username", "status", "request_message")
            ) + list(user.mentees.values("student__username", "status", "request_message")),
            "mensajes_enviados": list(user.sent_messages.values("text", "created_at")),
        }
        return Response(data)


class ChangePasswordView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        old = str(request.data.get("old_password") or "")
        new = str(request.data.get("new_password") or "")
        if not request.user.check_password(old):
            return Response({"old_password": ["La contraseña actual no es correcta"]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(new, request.user)
        except ValidationError as exc:
            return Response({"new_password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new)
        request.user.save(update_fields=["password"])
        logger.info("password changed user=%s", request.user.pk)
        return Response({"detail": "Contraseña cambiada"})


class PasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        email = str(request.data.get("email") or "").strip()
        user = User.objects.filter(email__iexact=email, is_active=True).first() if email else None
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL}/reset/{uid}/{token}"
            send_mail(
                "Recupera tu contraseña de PrepCards",
                f"Hola {user.username}.\n\nAbre este enlace para elegir una contraseña nueva.\n{link}\n\n"
                "Si no lo has pedido tú, ignora este mensaje.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            logger.info("password reset requested user=%s", user.pk)
        return Response({"detail": "Si el email existe, recibirás un enlace para cambiar la contraseña"})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        try:
            pk = force_str(urlsafe_base64_decode(str(request.data.get("uid") or "")))
            user = User.objects.filter(pk=pk).first()
        except (ValueError, TypeError, OverflowError):
            user = None
        if not user or not default_token_generator.check_token(user, str(request.data.get("token") or "")):
            return Response({"detail": "El enlace no es válido o ha caducado"}, status=status.HTTP_400_BAD_REQUEST)
        password = str(request.data.get("password") or "")
        try:
            validate_password(password, user)
        except ValidationError as exc:
            return Response({"password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save(update_fields=["password"])
        logger.info("password reset done user=%s", user.pk)
        return Response({"detail": "Contraseña cambiada"})
