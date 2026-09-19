from types import SimpleNamespace

import pytest

from daily_win_api.ai.moderation import (
    ModerationRejectedError,
    ModerationResult,
    NoOpContentModerator,
    OpenAIContentModerator,
    build_content_moderator,
    review_generated_daily_win,
)
from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.core.config import Settings
from daily_win_api.domains.daily_wins.safety import activity_text_blob


def test_noop_moderator_never_flags() -> None:
    result = NoOpContentModerator().check("Use scissors to cut cardboard")
    assert result.flagged is False


def test_build_content_moderator_defaults_to_noop() -> None:
    moderator = build_content_moderator(Settings(content_moderation_enabled=False))
    assert isinstance(moderator, NoOpContentModerator)


def test_review_generated_daily_win_is_noop_when_disabled() -> None:
    review_generated_daily_win(
        valid_daily_win_draft(),
        settings=Settings(content_moderation_enabled=False),
    )


def test_openai_moderator_uses_flagged_result() -> None:
    client = _FakeModerationClient(flagged=True)
    moderator = OpenAIContentModerator(client)
    result = moderator.check("placeholder")
    assert result.flagged is True
    assert client.kwargs is not None
    assert client.kwargs["model"] == "omni-moderation-latest"


def test_openai_moderator_passes_when_not_flagged() -> None:
    moderator = OpenAIContentModerator(_FakeModerationClient(flagged=False))
    assert moderator.check("hello").flagged is False


def test_review_raises_when_enabled_and_flagged(monkeypatch) -> None:
    draft = valid_daily_win_draft()

    class _Flagging:
        def check(self, text: str) -> ModerationResult:
            assert activity_text_blob(draft) == text
            return ModerationResult(flagged=True)

    monkeypatch.setattr(
        "daily_win_api.ai.moderation.build_content_moderator",
        lambda _settings=None: _Flagging(),
    )
    with pytest.raises(ModerationRejectedError) as caught:
        review_generated_daily_win(draft)
    assert caught.value.code == "harmful_content"


class _FakeModerationClient:
    def __init__(self, *, flagged: bool) -> None:
        self.kwargs: dict | None = None
        self.moderations = self
        self._flagged = flagged

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(results=[SimpleNamespace(flagged=self._flagged)])
