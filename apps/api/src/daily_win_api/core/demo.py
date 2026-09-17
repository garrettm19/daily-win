"""Development/demo tenant identifiers.

This is not production authorization. Authenticated household membership
will replace this mechanism later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from daily_win_api.domains.children.models import Child
    from daily_win_api.domains.households.models import Household

DEMO_NAMESPACE = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
DEMO_HOUSEHOLD_ID = uuid5(DEMO_NAMESPACE, "demo-household")
DEMO_CHILD_ID = uuid5(DEMO_NAMESPACE, "demo-child-hayes")
DEMO_CHILD_NICKNAME = "Hayes"
SKILL_ID_NAMESPACE = UUID("bbbbbbbb-cccc-4ddd-8eee-ffffffffffff")


def skill_id_for_code(code: str) -> UUID:
    return uuid5(SKILL_ID_NAMESPACE, code)


def demo_baseline_id() -> UUID:
    return uuid5(DEMO_NAMESPACE, "demo-child-hayes-baseline-v1")


def demo_goal_id(skill_code: str) -> UUID:
    return uuid5(DEMO_NAMESPACE, f"demo-child-hayes-goal:{skill_code}")


def get_demo_household_id() -> UUID:
    return DEMO_HOUSEHOLD_ID


def get_demo_child_id() -> UUID:
    return DEMO_CHILD_ID


def get_demo_household(session: Session) -> Household | None:
    from daily_win_api.domains.households.models import Household

    return session.get(Household, DEMO_HOUSEHOLD_ID)


def get_demo_child(session: Session) -> Child | None:
    from daily_win_api.domains.children.models import Child

    return session.get(Child, DEMO_CHILD_ID)
