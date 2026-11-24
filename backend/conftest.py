import pytest
from django.core.cache import cache
from django.core.management import call_command

from quiz.tests.helpers import api_for, make_user


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def seeded(db):
    call_command("seed_questions")


@pytest.fixture
def user(seeded):
    return make_user("annia")


@pytest.fixture
def client(user):
    return api_for(user)


@pytest.fixture
def mentor(seeded):
    return make_user("profe", role="mentor")
