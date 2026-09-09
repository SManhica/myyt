from __future__ import annotations

from myyt.config import MEDIA_URL_REFRESH_MARGIN
from myyt.models import MediaFormat, PlayerInfo
from myyt.youtube.extractor import YouTubeExtractor
from myyt.youtube.selector import select_best_audio


def extract_selection(
    extractor: YouTubeExtractor,
    url: str,
) -> tuple[PlayerInfo, MediaFormat]:
    player_info = extractor.extract_player(url)
    return player_info, select_best_audio(player_info.formats)


def expires_soon(media_format: MediaFormat, now: float) -> bool:
    return bool(
        media_format.expires_at is not None
        and media_format.expires_at <= int(now) + MEDIA_URL_REFRESH_MARGIN
    )


def matching_usable_format(player_info: PlayerInfo, itag: int) -> MediaFormat | None:
    for media_format in player_info.formats:
        if (
            media_format.itag == itag
            and media_format.has_audio
            and media_format.media_url
            and not media_format.requires_n_transform
            and media_format.protocol in {"http", "https"}
        ):
            return media_format
    return None


def is_exact_resume_match(original: MediaFormat, refreshed: MediaFormat) -> bool:
    if original.content_length is None or refreshed.content_length is None:
        return False
    return (
        original.itag,
        original.mime_type,
        original.container,
        original.codecs,
        original.audio_codec,
        original.video_codec,
        original.sample_rate,
        original.channels,
        original.content_length,
        original.has_audio,
        original.has_video,
    ) == (
        refreshed.itag,
        refreshed.mime_type,
        refreshed.container,
        refreshed.codecs,
        refreshed.audio_codec,
        refreshed.video_codec,
        refreshed.sample_rate,
        refreshed.channels,
        refreshed.content_length,
        refreshed.has_audio,
        refreshed.has_video,
    )
