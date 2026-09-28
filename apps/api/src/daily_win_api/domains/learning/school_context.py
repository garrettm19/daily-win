"""Future-safe parent-reported school context. Not measured Daily Win evidence."""

from __future__ import annotations

from dataclasses import dataclass

SCHOOL_CONTEXT_V1 = "school_context_v1"


@dataclass(frozen=True)
class ParentReportedSchoolContext:
    """Parent-entered classroom context. May influence diagnostic priority later."""

    teacher_focus: str | None = None
    classroom_topic: str | None = None
    recent_assignment_topic: str | None = None
    reporting_kind: str = "parent_reported"
    epistemic_kind: str = "PROFILE_REPORT"
    schema_version: str = SCHOOL_CONTEXT_V1

    def as_dict(self) -> dict[str, object]:
        return {
            "teacher_focus": self.teacher_focus,
            "classroom_topic": self.classroom_topic,
            "recent_assignment_topic": self.recent_assignment_topic,
            "reporting_kind": self.reporting_kind,
            "epistemic_kind": self.epistemic_kind,
            "schema_version": self.schema_version,
            "counts_as_measurement": False,
        }


def may_influence_diagnostic_priority(payload: ParentReportedSchoolContext) -> bool:
    return any(
        (
            payload.teacher_focus,
            payload.classroom_topic,
            payload.recent_assignment_topic,
        )
    )
