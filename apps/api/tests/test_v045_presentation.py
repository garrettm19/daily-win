from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.daily_wins.enums import (
    Completion,
    Difficulty,
    Engagement,
    SetbackResponse,
)
from daily_win_api.domains.daily_wins.feedback import submit_demo_feedback
from daily_win_api.domains.daily_wins.queries import get_demo_daily_win
from daily_win_api.domains.daily_wins.schemas import DailyWinFeedbackCreate
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.enums import AcademicResult
from daily_win_api.domains.learning.progress import load_demo_progress


def test_progress_exposes_band_and_recent_checks(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(
        demo_db,
        generated.id,
        DailyWinFeedbackCreate(
            difficulty=Difficulty.ABOUT_RIGHT,
            engagement=Engagement.HIGH,
            completion=Completion.COMPLETED,
            setback_response=SetbackResponse.CONTINUED_AFTER_PROMPT,
            academic_result=AcademicResult.CORRECT_AFTER_LIGHT_PROMPT,
        ),
    )
    child = get_demo_child(demo_db)
    assert child is not None
    progress = load_demo_progress(demo_db, child)
    assert progress.academic_skills
    skill = progress.academic_skills[0]
    assert skill.band == "developing"
    assert skill.recent_checks
    assert skill.recent_checks[0].result == "correct_after_light_prompt"
    dumped = str(progress.model_dump())
    assert "%" not in dumped
    assert "mastery" not in dumped.lower()


def test_result_snapshot_and_mapped_observations(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(
        demo_db,
        generated.id,
        DailyWinFeedbackCreate(
            difficulty=Difficulty.ABOUT_RIGHT,
            engagement=Engagement.HIGH,
            completion=Completion.COMPLETED,
            setback_response=SetbackResponse.CONTINUED_AFTER_PROMPT,
            academic_result=AcademicResult.CORRECT_AFTER_LIGHT_PROMPT,
        ),
    )
    child = get_demo_child(demo_db)
    assert child is not None
    win = get_demo_daily_win(demo_db, generated.id, child)
    assert win is not None
    assert win.result_snapshot is not None
    assert win.result_snapshot.academic_result == "correct_after_light_prompt"
    assert win.result_snapshot.difficulty == "about_right"
    progress = load_demo_progress(demo_db, child)
    for item in progress.recent_observations:
        assert "correct_independently" not in item.summary
        assert "_" not in item.summary
        assert item.summary != "Parent observation"
        assert item.goal_name != "Goal"
        assert "[object Object]" not in item.summary
