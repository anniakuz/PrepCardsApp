from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from .models import Enrollment
from .services import broadcast, create_message, group_name

User = get_user_model()


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Chat de una mentoría activa. Autenticación con el JWT de acceso en ?token=."""

    async def connect(self):
        self.enrollment_id = int(self.scope["url_route"]["kwargs"]["enrollment_id"])
        user = await self._user_from_token()
        if user is None or not await self._can_join(user):
            await self.close(code=4403)
            return
        self.user = user
        self.group = group_name(self.enrollment_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        text = str(content.get("text") or "").strip()[:2000]
        if not text:
            return
        message = await self._save(text)
        if message:
            await database_sync_to_async(broadcast)(message)

    async def chat_message(self, event):
        await self.send_json(event["message"])

    @database_sync_to_async
    def _user_from_token(self):
        query = parse_qs(self.scope.get("query_string", b"").decode())
        token = (query.get("token") or [""])[0]
        try:
            user_id = AccessToken(token)["user_id"]
        except (TokenError, KeyError):
            return None
        return User.objects.filter(pk=user_id, is_active=True).first()

    @database_sync_to_async
    def _can_join(self, user):
        return Enrollment.objects.filter(pk=self.enrollment_id, status="active").filter(
            mentor=user
        ).exists() or Enrollment.objects.filter(pk=self.enrollment_id, status="active", student=user).exists()

    @database_sync_to_async
    def _save(self, text):
        enrollment = Enrollment.objects.filter(pk=self.enrollment_id, status="active").first()
        if not enrollment:
            return None
        message = create_message(enrollment, self.user, text)
        return message
