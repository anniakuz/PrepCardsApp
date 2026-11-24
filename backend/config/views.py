from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        checks = {}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
        try:
            cache.set("health", "ok", 5)
            checks["cache"] = "ok" if cache.get("health") == "ok" else "error"
        except Exception:
            checks["cache"] = "error"
        healthy = all(value == "ok" for value in checks.values())
        return Response({"status": "ok" if healthy else "error", **checks}, status=200 if healthy else 503)
