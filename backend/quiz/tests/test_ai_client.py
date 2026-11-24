import io
import json
from unittest import mock

import pytest

from config import ai_client


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def gemini_reply(text):
    return FakeResponse(json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode())


TOOL = {"name": "x", "description": "d", "input_schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}}}


@pytest.fixture
def gemini(settings):
    settings.GEMINI_API_KEY = "clave"
    settings.AI_PROVIDER = ""
    settings.ANTHROPIC_API_KEY = ""


def test_gemini_is_chosen_when_it_has_a_key(gemini):
    assert ai_client.provider() == "gemini" and ai_client.is_configured()


def test_gemini_call_tool_returns_parsed_json(gemini):
    with mock.patch("urllib.request.urlopen", return_value=gemini_reply('{"ok": true}')) as urlopen:
        assert ai_client.call_tool("sistema", "hola", TOOL, 100) == {"ok": True}
    sent = json.loads(urlopen.call_args[0][0].data)
    assert sent["generationConfig"]["responseJsonSchema"] == TOOL["input_schema"]


def test_gemini_call_text_maps_assistant_to_model(gemini):
    history = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}, {"role": "user", "content": "c"}]
    with mock.patch("urllib.request.urlopen", return_value=gemini_reply("respuesta")) as urlopen:
        assert ai_client.call_text("sistema", history, 100) == "respuesta"
    roles = [c["role"] for c in json.loads(urlopen.call_args[0][0].data)["contents"]]
    assert roles == ["user", "model", "user"]


def test_gemini_rate_limit_is_temporary(gemini):
    import urllib.error
    error = urllib.error.HTTPError("u", 429, "limit", {}, None)
    with mock.patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(ai_client.AITemporaryError):
            ai_client.call_text("s", [{"role": "user", "content": "a"}], 10)


def test_invalid_json_from_gemini_is_temporary(gemini):
    with mock.patch("urllib.request.urlopen", return_value=gemini_reply("no es json")):
        with pytest.raises(ai_client.AITemporaryError):
            ai_client.call_tool("s", "u", TOOL, 10)


def test_missing_key_is_unavailable(settings):
    settings.GEMINI_API_KEY = settings.ANTHROPIC_API_KEY = ""
    assert not ai_client.is_configured()
    with pytest.raises(ai_client.AIUnavailable):
        ai_client.call_text("s", [{"role": "user", "content": "a"}], 10)
