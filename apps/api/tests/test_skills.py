from sqlalchemy import func, select

from daily_win_api.dev.seed import seed_development_data
from daily_win_api.domains.learning.models import Skill
from daily_win_api.domains.learning.taxonomy import SKILL_DEFINITIONS


def test_seeded_skill_codes_are_unique(db_session) -> None:
    seed_development_data(db_session)

    expected = {definition["code"] for definition in SKILL_DEFINITIONS}
    codes = set(db_session.scalars(select(Skill.code).where(Skill.code.in_(expected))))
    assert codes == expected
    assert len(codes) == len(SKILL_DEFINITIONS)

    count = db_session.scalar(select(func.count()).select_from(Skill))
    distinct = db_session.scalar(select(func.count(func.distinct(Skill.code))))
    assert count == distinct


def test_seeded_skills_have_curriculum_metadata(db_session) -> None:
    seed_development_data(db_session)
    skill = db_session.scalar(
        select(Skill).where(Skill.code == "math.addition.within_10")
    )
    assert skill is not None
    assert skill.skill_kind == "skill"
    assert skill.strand == "addition"
    assert skill.parent_code == "math.addition"
    assert skill.measurable_outcome
    strand = db_session.scalar(select(Skill).where(Skill.code == "math.addition"))
    assert strand is not None
    assert strand.skill_kind == "strand"
