import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import get_profile
from quiz.tests.helpers import PASSWORD, make_user

pytestmark = pytest.mark.django_db

FORM = {
    "username": "nueva", "first_name": "Ana", "last_name": "García López", "email": "nueva@example.com", "password": PASSWORD,
    "age": 29, "sex": "female", "experience": "1y", "about": "Quiero cambiar de trabajo", "accept_terms": True,
}


def test_register_saves_profile_and_sends_welcome_email():
    response = APIClient().post("/api/auth/register/", FORM, format="json")
    assert response.status_code == 201
    profile = get_profile(get_user_model().objects.get(username="nueva"))
    assert (profile.age, profile.sex, profile.experience, profile.role) == (29, "female", "1y", "student")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["nueva@example.com"]


def test_register_requires_age_sex_experience_but_not_about():
    data = {k: v for k, v in FORM.items() if k not in ("age", "about")}
    response = APIClient().post("/api/auth/register/", data, format="json")
    assert response.status_code == 400 and "age" in response.data


def test_register_without_about_is_valid():
    data = {k: v for k, v in FORM.items() if k != "about"}
    assert APIClient().post("/api/auth/register/", data, format="json").status_code == 201


def test_register_rejects_duplicate_email():
    make_user("otra")
    data = {**FORM, "email": "otra@example.com"}
    assert APIClient().post("/api/auth/register/", data, format="json").status_code == 400


def test_login_me_and_profile_update():
    APIClient().post("/api/auth/register/", FORM, format="json")
    cache.clear()
    api = APIClient()
    token = api.post("/api/auth/token/", {"username": "nueva", "password": PASSWORD}, format="json").data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    me = api.get("/api/auth/me/").data
    assert me["experience"] == "1y" and me["role"] == "student" and me["first_name"] == "Ana"
    updated = api.patch("/api/auth/me/", {"experience": "2y", "about": "Nuevo", "last_name": "Pérez"}, format="json").data
    assert updated["experience"] == "2y" and updated["about"] == "Nuevo" and updated["last_name"] == "Pérez"


def test_change_password():
    user = make_user("cambio")
    from quiz.tests.helpers import api_for

    api = api_for(user)
    assert api.post("/api/auth/change-password/", {"old_password": "mal", "new_password": "Otra-Clave-2026"}).status_code == 400
    assert api.post("/api/auth/change-password/", {"old_password": PASSWORD, "new_password": "Otra-Clave-2026"}).status_code == 200
    user.refresh_from_db()
    assert user.check_password("Otra-Clave-2026")


def test_password_reset_flow():
    user = make_user("olvido")
    api = APIClient()
    assert api.post("/api/auth/password-reset/", {"email": "nadie@example.com"}).status_code == 200
    assert len(mail.outbox) == 0
    assert api.post("/api/auth/password-reset/", {"email": user.email}).status_code == 200
    assert len(mail.outbox) == 1
    link = [line for line in mail.outbox[0].body.splitlines() if "/reset/" in line][0]
    uid, token = link.split("/reset/")[1].split("/")
    assert api.post("/api/auth/password-reset/confirm/", {"uid": uid, "token": token, "password": "Nueva-Clave-2026"}).status_code == 200
    user.refresh_from_db()
    assert user.check_password("Nueva-Clave-2026")
    assert api.post("/api/auth/password-reset/confirm/", {"uid": uid, "token": token, "password": "Otra-Clave-2027"}).status_code == 400


def test_register_requires_accepting_terms_and_stores_consent():
    data = {**FORM, "accept_terms": False}
    assert APIClient().post("/api/auth/register/", data, format="json").status_code == 400
    assert APIClient().post("/api/auth/register/", {k: v for k, v in FORM.items() if k != "accept_terms"}, format="json").status_code == 400
    assert not get_user_model().objects.filter(username="nueva").exists()
    assert APIClient().post("/api/auth/register/", FORM, format="json").status_code == 201
    profile = get_profile(get_user_model().objects.get(username="nueva"))
    assert profile.terms_accepted_at is not None and profile.terms_version == "2026-11"


def test_export_and_delete_account():
    from quiz.tests.helpers import api_for

    user = make_user("borrar")
    api = api_for(user)
    assert api.get("/api/auth/export/").data["usuario"]["username"] == "borrar"
    assert api.post("/api/auth/delete-account/", {"password": "mal"}, format="json").status_code == 400
    assert api.post("/api/auth/delete-account/", {"password": PASSWORD}, format="json").status_code == 204
    assert not get_user_model().objects.filter(username="borrar").exists()


def test_register_requires_first_and_last_name():
    for missing in ("first_name", "last_name"):
        data = {k: v for k, v in FORM.items() if k != missing}
        assert APIClient().post("/api/auth/register/", data, format="json").status_code == 400


def test_refresh_token_of_deleted_user_gives_401_not_500(db):
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    user = get_user_model().objects.create_user("fantasma", "f@example.com", "x-Pass-12345")
    refresh = str(RefreshToken.for_user(user))
    user.delete()
    response = APIClient().post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 401


@pytest.mark.parametrize("password", ["Corta1!a", "sinmayuscula1!", "SINMINUSCULA1!", "SinNumeros!!!", "SinEspecial123"])
def test_password_rules_reject_weak_passwords(password):
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        validate_password(password)


def test_password_rules_accept_a_strong_password():
    from django.contrib.auth.password_validation import validate_password

    validate_password("Contrasena-Segura9")


def test_register_can_choose_mentor_but_never_admin():
    api = APIClient()
    data = {**FORM, "username": "mentora", "email": "m@example.com", "role": "mentor"}
    assert api.post("/api/auth/register/", {**data, "about": ""}, format="json").status_code == 400
    assert api.post("/api/auth/register/", {**data, "about": "corto"}, format="json").status_code == 400
    data["about"] = "Desarrolladora backend con experiencia en Java y entrevistas."
    assert api.post("/api/auth/register/", data, format="json").status_code == 201
    assert get_profile(get_user_model().objects.get(username="mentora")).role == "mentor"
    admin = {**FORM, "username": "intruso", "email": "i@example.com", "role": "admin"}
    assert api.post("/api/auth/register/", admin, format="json").status_code == 400


def test_about_is_short_because_other_users_can_see_it():
    api = APIClient()
    data = {**FORM, "username": "larga", "email": "l@example.com", "about": "x" * 101}
    assert api.post("/api/auth/register/", data, format="json").status_code == 400
    assert api.post("/api/auth/register/", {**data, "about": "x" * 100}, format="json").status_code == 201
