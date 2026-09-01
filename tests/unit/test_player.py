import json
from pathlib import Path

import pytest

from myyt.exceptions import FormatExtractionError
from myyt.youtube.player import YouTubePlayer

FIXTURES = Path(__file__).parents[1] / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class StubClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[tuple[str, dict, dict, dict]] = []

    def post_json(
        self,
        url: str,
        payload: dict,
        *,
        params: dict,
        headers: dict,
    ) -> dict:
        self.calls.append((url, payload, params, headers))
        return self.response


def test_uses_non_token_required_player_for_direct_audio() -> None:
    client = StubClient(json.loads(fixture("player_android_formats.json")))
    initial = {
        "streamingData": {
            "adaptiveFormats": [
                {"itag": 140, "mimeType": 'audio/mp4; codecs="mp4a.40.2"'}
            ],
            "serverAbrStreamingUrl": "https://example.test/sabr",
        }
    }

    resolved = YouTubePlayer(client=client).resolve(
        "M7lc1UVf-VE",
        fixture("watch_page_formats.html"),
        initial,
    )

    assert resolved.client_name == "VISIONOS"
    _, payload, params, headers = client.calls[0]
    assert payload["context"]["client"]["clientName"] == "VISIONOS"
    assert payload["context"]["client"]["userAgent"].startswith("Mozilla/5.0")
    assert "contentCheckOk" not in payload
    assert "racyCheckOk" not in payload
    assert params["key"] == "fixture-player-key"
    assert headers["X-YouTube-Client-Name"] == "101"


def test_does_not_trust_web_media_url_without_gvs_token_context() -> None:
    client = StubClient(json.loads(fixture("player_android_formats.json")))
    initial = {
        "streamingData": {
            "adaptiveFormats": [
                {
                    "itag": 140,
                    "mimeType": 'audio/mp4; codecs="mp4a.40.2"',
                    "url": "https://media.example.test/audio?sig=direct",
                }
            ]
        }
    }

    resolved = YouTubePlayer(client=client).resolve(
        "M7lc1UVf-VE",
        fixture("watch_page_formats.html"),
        initial,
    )

    assert resolved.client_name == "VISIONOS"
    assert len(client.calls) == 1


def test_reports_missing_client_configuration() -> None:
    with pytest.raises(FormatExtractionError, match="client configuration"):
        YouTubePlayer(client=StubClient({})).resolve("M7lc1UVf-VE", "<html></html>", {})
