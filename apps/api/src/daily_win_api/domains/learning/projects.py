"""Lightweight project/theme continuity. Engagement context, not learner truth."""

from __future__ import annotations

from dataclasses import dataclass

PROJECT_CATALOG = (
    {
        "code": "project.dream_hotel",
        "title": "Dream Hotel",
        "beats": ("describe", "allocate", "budget", "pitch"),
    },
)


@dataclass(frozen=True)
class ProjectMemory:
    project_code: str
    beat: str
    choices: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "project_code": self.project_code,
            "beat": self.beat,
            "choices": list(self.choices),
            "epistemic_kind": "engagement_context",
        }


def next_project_beat(
    recent_code: str | None, recent_beat: str | None
) -> ProjectMemory | None:
    if recent_code is None:
        return ProjectMemory(project_code="project.dream_hotel", beat="describe")
    item = next((row for row in PROJECT_CATALOG if row["code"] == recent_code), None)
    if item is None:
        return None
    beats = item["beats"]
    if recent_beat in beats:
        index = beats.index(recent_beat)
        if index + 1 < len(beats):
            return ProjectMemory(project_code=recent_code, beat=beats[index + 1])
    return None
