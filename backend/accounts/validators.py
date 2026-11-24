import re

from django.core.exceptions import ValidationError

SPECIAL = r"[^A-Za-z0-9\s]"


class ComplexityValidator:
    """Exige mayúscula, minúscula, número y un carácter especial."""

    def validate(self, password, user=None):
        missing = []
        if not re.search(r"[A-Z]", password):
            missing.append("una letra mayúscula")
        if not re.search(r"[a-z]", password):
            missing.append("una letra minúscula")
        if not re.search(r"\d", password):
            missing.append("un número")
        if not re.search(SPECIAL, password):
            missing.append("un carácter especial (por ejemplo # ? ! @ $ % ^ & * - _ .)")
        if missing:
            raise ValidationError("La contraseña necesita " + ", ".join(missing) + ".", code="password_too_simple")

    def get_help_text(self):
        return "Mínimo 10 caracteres con mayúscula, minúscula, número y un carácter especial."
