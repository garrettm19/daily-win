"""Optional general harmful-content moderation (Layer 5).

Domain-specific activity safety remains application-owned in
`domains.daily_wins.safety`. This module is disabled by default and must not
add a second generative model call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.core.config import Settings, get_settings
from daily_win_api.domains.daily_wins.safety import activity_text_blob


class ModerationRejectedError(Exception):
    """Provider moderation flagged generated activity text."""

    def __init__(self) -> None:
        super().__init__("harmful_content")
        self.code = "harmful_content"


@dataclass(frozen=True)
class ModerationResult:
    flagged: bool


class ContentModerator(Protocol):
    def check(self, text: str) -> ModerationResult: ...


class NoOpContentModerator:
    def check(self, text: str) -> ModerationResult:
        return ModerationResult(flagged=False)


class OpenAIContentModerator:
    """OpenAI Moderations API. Not a generative Daily Win call."""

    def __init__(self, client, model: str = "omni-moderation-latest") -> None:
        self._client = client
        self._model = model

    def check(self, text: str) -> ModerationResult:
        response = self._client.moderations.create(model=self._model, input=text)
        results = getattr(response, "results", None) or []
        flagged = any(bool(getattr(item, "flagged", False)) for item in results)
        return ModerationResult(flagged=flagged)


def build_content_moderator(settings: Settings | None = None) -> ContentModerator:
    resolved = settings or get_settings()
    if not resolved.content_moderation_enabled:
        return NoOpContentModerator()
    from openai import OpenAI

    return OpenAIContentModerator(OpenAI(api_key=resolved.openai_api_key or ""))


def review_generated_daily_win(
    draft: DailyWinDraft, *, settings: Settings | None = None
) -> None:
    """No-op unless content_moderation_enabled. Does not override Layer 4."""
    moderator = build_content_moderator(settings)
    result = moderator.check(activity_text_blob(draft))
    if result.flagged:
        raise ModerationRejectedError
