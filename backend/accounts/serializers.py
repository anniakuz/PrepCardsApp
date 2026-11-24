import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from django.utils import timezone

from .models import TERMS_VERSION, Profile, get_profile, role_of
from .tasks import send_welcome_email

User = get_user_model()
logger = logging.getLogger("prepcards.auth")

PROFILE_FIELDS = ["age", "sex", "experience", "about", "role"]
MENTOR_ABOUT_MIN = 20
ABOUT_MAX = 100


class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    age = serializers.IntegerField(min_value=14, max_value=100, write_only=True)
    sex = serializers.ChoiceField(choices=Profile.SEX_CHOICES, write_only=True)
    experience = serializers.ChoiceField(choices=Profile.EXPERIENCE_CHOICES, write_only=True)
    about = serializers.CharField(required=False, allow_blank=True, max_length=ABOUT_MAX, write_only=True)
    role = serializers.ChoiceField(choices=[("student", "Estudiante"), ("mentor", "Mentor")], default="student", write_only=True)
    accept_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "password", "age", "sex", "experience", "about", "role", "accept_terms"]

    def validate(self, attrs):
        if attrs.get("role") == "mentor" and len((attrs.get("about") or "").strip()) < MENTOR_ABOUT_MIN:
            raise serializers.ValidationError(
                {"about": [f"Los mentores deben escribir una descripción de al menos {MENTOR_ABOUT_MIN} caracteres"]}
            )
        return attrs

    def validate_accept_terms(self, value):
        if value is not True:
            raise serializers.ValidationError("Debes aceptar los términos y la política de privacidad")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este email")
        return value

    def create(self, validated_data):
        validated_data.pop("accept_terms")
        extra = {field: validated_data.pop(field) for field in PROFILE_FIELDS if field in validated_data}
        user = User.objects.create_user(**validated_data)
        profile = get_profile(user)
        for field, value in extra.items():
            setattr(profile, field, value)
        profile.terms_accepted_at = timezone.now()
        profile.terms_version = TERMS_VERSION
        profile.save()
        try:
            send_welcome_email.delay(user.pk)
        except Exception:
            # Un fallo del broker no debe impedir el registro
            logger.exception("could not queue welcome email user=%s", user.pk)
        return user


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    sex = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    about = serializers.SerializerMethodField()
    accepting_requests = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role", "age", "sex", "experience", "about", "accepting_requests"]

    def get_role(self, obj):
        return role_of(obj)

    def get_age(self, obj):
        return get_profile(obj).age

    def get_sex(self, obj):
        return get_profile(obj).sex

    def get_experience(self, obj):
        return get_profile(obj).experience

    def get_about(self, obj):
        return get_profile(obj).about

    def get_accepting_requests(self, obj):
        return get_profile(obj).accepting_requests


class ProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=60, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    email = serializers.EmailField(required=False)
    age = serializers.IntegerField(min_value=14, max_value=100, required=False)
    sex = serializers.ChoiceField(choices=Profile.SEX_CHOICES, required=False)
    experience = serializers.ChoiceField(choices=Profile.EXPERIENCE_CHOICES, required=False)
    about = serializers.CharField(required=False, allow_blank=True, max_length=ABOUT_MAX)
    accepting_requests = serializers.BooleanField(required=False)


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]
