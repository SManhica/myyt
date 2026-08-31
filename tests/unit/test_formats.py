import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from myyt.exceptions import FormatExtractionError
from myyt.youtube.formats import (
    classify_codecs,
    manifest_urls,
    parse_mime_type,
    parse_streaming_formats,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"


def load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_normalizes_muxed_adaptive_audio_and_video_formats() -> None:
    response = load_json("player_android_formats.json")

    formats = parse_streaming_formats(response)
    by_itag = {media_format.itag: media_format for media_format in formats}

    assert len(formats) == 4
    assert by_itag[18].has_audio is True
    assert by_itag[18].has_video is True
    assert by_itag[18].adaptive is False
    assert by_itag[137].has_video is True
    assert by_itag[137].has_audio is False
    assert by_itag[137].fragmented is True
    assert by_itag[140].container == "m4a"
    assert by_itag[140].audio_codec == "mp4a.40.2"
    assert by_itag[140].sample_rate == 44100
    assert by_itag[140].content_length == 3560000
    assert by_itag[140].expires_at == 2000000000
    assert by_itag[251].container == "webm"
    assert by_itag[251].protocol == "https"


def test_exposes_manifest_urls_separately() -> None:
    dash, hls = manifest_urls(load_json("player_android_formats.json"))

    assert dash == "https://manifest.example.test/dash.mpd"
    assert hls == "https://manifest.example.test/master.m3u8"


def test_marks_encrypted_signature_as_unresolved_and_accepts_plain_signature() -> None:
    formats = parse_streaming_formats(load_json("player_cipher_formats.json"))
    by_itag = {media_format.itag: media_format for media_format in formats}

    assert by_itag[18].is_ciphered is True
    assert by_itag[18].media_url is None
    assert by_itag[22].is_ciphered is True
    assert parse_qs(urlparse(by_itag[22].media_url).query)["sig"] == ["plain-signature"]


def test_parses_and_classifies_mime_codecs() -> None:
    mime_type, codecs = parse_mime_type(
        'video/mp4; codecs="avc1.640028, mp4a.40.2"'
    )

    assert mime_type == "video/mp4"
    assert codecs == ("avc1.640028", "mp4a.40.2")
    assert classify_codecs(mime_type, codecs) == ("mp4a.40.2", "avc1.640028")


@pytest.mark.parametrize(
    "response",
    [{}, {"streamingData": {}}, {"streamingData": {"formats": [{}]}}],
)
def test_rejects_missing_or_unrecognizable_streaming_data(response: dict) -> None:
    with pytest.raises(FormatExtractionError):
        parse_streaming_formats(response)
