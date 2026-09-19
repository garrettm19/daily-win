"""Development demo session isolation.

Not authentication. Production must not register this mechanism.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.core.demo import DEMO_NAMESPACE
from daily_win_api.dev.models import DemoSession
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.households.models import Household

MIN_DEMO_SESSION_SECRET_LENGTH = 32
SESSION_STATUS_NEW = "new"
SESSION_STATUS_READY = "ready"


class DemoSessionRejectedError(Exception):
    """Missing or too-short X-Demo-Session header."""


@dataclass
class DemoTenant:
    household_id: UUID
    child: Child | None
    tester_fingerprint: str
    session_hash: str
    profile_source: str | None


def hash_demo_session_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def tester_fingerprint(session_hash: str) -> str:
    return session_hash[:6].upper()


def session_household_id(session_hash: str) -> UUID:
    return uuid5(DEMO_NAMESPACE, f"session:{session_hash}:household")


def session_child_id(session_hash: str) -> UUID:
    return uuid5(DEMO_NAMESPACE, f"session:{session_hash}:child")


def session_baseline_id(session_hash: str) -> UUID:
    return uuid5(DEMO_NAMESPACE, f"session:{session_hash}:baseline-v1")


def session_goal_id(session_hash: str, skill_code: str) -> UUID:
    return uuid5(DEMO_NAMESPACE, f"session:{session_hash}:goal:{skill_code}")


def resolve_demo_tenant(session: Session, secret: str | None) -> DemoTenant:
    """Resolve or create an isolated demo session. Does not seed a child."""
    if secret is None or len(secret.strip()) < MIN_DEMO_SESSION_SECRET_LENGTH:
        raise DemoSessionRejectedError
    digest = hash_demo_session_secret(secret.strip())
    row = session.scalar(select(DemoSession).where(DemoSession.session_hash == digest))
    if row is None:
        household_id = session_household_id(digest)
        household = session.get(Household, household_id)
        if household is None:
            household = Household(id=household_id, display_name="Demo Household")
            session.add(household)
            session.flush()
        row = DemoSession(
            id=uuid4(),
            session_hash=digest,
            household_id=household_id,
            child_id=None,
            profile_source=None,
            last_seen_at=datetime.now(UTC),
        )
        session.add(row)
        session.flush()
    else:
        row.last_seen_at = datetime.now(UTC)

    child = None
    if row.child_id is not None:
        child = session.get(Child, row.child_id)
        if child is None or child.household_id != row.household_id:
            raise DemoSessionRejectedError
    return DemoTenant(
        household_id=row.household_id,
        child=child,
        tester_fingerprint=tester_fingerprint(digest),
        session_hash=digest,
        profile_source=row.profile_source,
    )


def load_demo_session_row(session: Session, session_hash: str) -> DemoSession | None:
    return session.scalar(
        select(DemoSession).where(DemoSession.session_hash == session_hash)
    )


def session_status(tenant: DemoTenant) -> str:
    if tenant.child is None:
        return SESSION_STATUS_NEW
    return SESSION_STATUS_READY
