from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from daily_win_api.ai.decision.fake import FakeDecisionGateway
from daily_win_api.domains.daily_wins.renderer_contract import (
    renderer_contract_hard_failures,
    renderer_contract_soft_flags,
)
from daily_win_api.domains.learning.integrity import curriculum_integrity_errors
from daily_win_api.domains.learning.planner import INSTRUCTION_POLICY_CURRENT
from daily_win_api.domains.learning.probes import PROBE_CATALOG_VERSION
from daily_win_api.eval.curriculum_audit import audit_curriculum
from daily_win_api.eval.decision_fixtures import (
    labelled_verification_cases,
    score_verification,
)
from daily_win_api.eval.expert_report import (
    curriculum_review_markdown,
    curriculum_review_sections,
)
from daily_win_api.eval.learner_cases import evaluate_learner_case, learner_state_cases
from daily_win_api.eval.planner_cases import evaluate_planner_case, planner_golden_cases
from daily_win_api.eval.probe_quality import evaluate_probe_case, labelled_probe_cases
from daily_win_api.eval.progress_claims import overclaim_hits
from daily_win_api.eval.renderer_contract_cases import labelled_renderer_contract_cases
from daily_win_api.eval.renderer_quality import (
    anti_pattern_flags,
    difficulty_examples,
    fake_render_structural_errors,
    labelled_anti_pattern_drafts,
    planner_difficulty_label,
    theme_variants_keep_instruction,
)
from daily_win_api.eval.scoring import write_results


@dataclass(frozen=True)
class SuiteResult:
    name: str
    total: int
    failed: int
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.failed == 0


def run_planner_suite() -> SuiteResult:
    errors: list[str] = []
    cases = planner_golden_cases()
    for case in cases:
        for item in evaluate_planner_case(case):
            errors.append(f"{case.id}: {item}")
    return SuiteResult("planner", len(cases), len(errors), tuple(errors))


def run_learner_suite() -> SuiteResult:
    errors: list[str] = []
    cases = learner_state_cases()
    for case in cases:
        for item in evaluate_learner_case(case):
            errors.append(f"{case.id}: {item}")
    return SuiteResult("learner", len(cases), len(errors), tuple(errors))


def run_probe_suite() -> SuiteResult:
    errors: list[str] = []
    cases = labelled_probe_cases()
    for case in cases:
        errors.extend(evaluate_probe_case(case))
    return SuiteResult("probes", len(cases), len(errors), tuple(errors))


def run_quality_suite() -> SuiteResult:
    errors: list[str] = []
    errors.extend(theme_variants_keep_instruction())
    errors.extend(fake_render_structural_errors())
    for example in difficulty_examples():
        label = planner_difficulty_label(example.band, example.mode, example.scaffold)
        if label != example.label:
            errors.append(f"{example.id}: {label} != {example.label}")
    for name, draft, expected in labelled_anti_pattern_drafts():
        flags = anti_pattern_flags(draft)
        if expected is not None and expected not in flags:
            errors.append(f"{name} missing {expected}")
        if expected is None and flags:
            errors.append(f"{name} unexpected {flags}")
    for case in labelled_renderer_contract_cases():
        hard = renderer_contract_hard_failures(case.draft, case.plan)
        soft = renderer_contract_soft_flags(case.draft, case.plan)
        if case.expect_hard is not None and case.expect_hard not in hard:
            errors.append(f"{case.id} missing {case.expect_hard}")
        if case.expect_hard is None and hard:
            errors.append(f"{case.id} unexpected hard {hard}")
        if case.expect_soft is not None and case.expect_soft not in soft:
            errors.append(f"{case.id} missing soft {case.expect_soft}")
        if case.expect_soft is None and soft:
            errors.append(f"{case.id} unexpected soft {soft}")
    claims = overclaim_hits()
    if claims:
        errors.extend(claims)
    total = (
        2
        + len(difficulty_examples())
        + len(labelled_anti_pattern_drafts())
        + len(labelled_renderer_contract_cases())
        + 1
    )
    return SuiteResult("quality", total, len(errors), tuple(errors))


def run_decision_suite() -> SuiteResult:
    report = score_verification(labelled_verification_cases(), FakeDecisionGateway())
    errors: list[str] = []
    if report["safety_false_negatives"]:
        errors.append("safety false negatives")
    if report["classification_accuracy"] != 1.0:
        errors.append(f"accuracy {report['classification_accuracy']}")
    return SuiteResult(
        "decision",
        len(labelled_verification_cases()),
        len(errors),
        tuple(errors),
    )


def run_integrity_suite() -> SuiteResult:
    errors = curriculum_integrity_errors()
    return SuiteResult("integrity", 1, len(errors), tuple(errors))


SUITE_RUNNERS = {
    "planner": run_planner_suite,
    "learner": run_learner_suite,
    "probes": run_probe_suite,
    "quality": run_quality_suite,
    "decision": run_decision_suite,
    "integrity": run_integrity_suite,
}


def run_offline_suites() -> dict[str, Any]:
    suites = tuple(runner() for runner in SUITE_RUNNERS.values())
    audit = audit_curriculum()
    review = curriculum_review_sections()
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "curriculum_version": audit.version,
        "instruction_policy_version": INSTRUCTION_POLICY_CURRENT,
        "projector_version": "academic_projector_v1",
        "probe_catalog_version": PROBE_CATALOG_VERSION,
        "planner_case_count": len(planner_golden_cases()),
        "curriculum": {
            "academic_skill_count": len(audit.skills),
            "missing_prerequisite_edges": [
                f"{src}->{dest}" for src, dest in audit.missing_prerequisite_edges
            ],
            "rejected_prerequisite_edges": [
                f"{src}->{dest}" for src, dest in audit.rejected_prerequisite_edges
            ],
            "overly_broad": list(audit.overly_broad),
            "hard_to_observe": list(audit.hard_to_observe),
            "questionable_grade_bands": list(audit.questionable_grade_bands),
            "skills_without_specific_probe": list(audit.skills_without_specific_probe),
            "missing_standard_refs": list(audit.missing_standard_refs),
            "duplicates": list(audit.duplicates),
            "remaining_uncertainty": list(audit.remaining_uncertainty),
        },
        "curriculum_review": review,
        "suites": [asdict(item) for item in suites],
        "all_passed": all(item.passed for item in suites),
        "note": "Offline educational-quality eval. Not learner memory.",
    }


def write_offline_report(path) -> None:
    payload = run_offline_suites()
    write_results(path, payload)
    markdown_path = path.with_suffix(".curriculum-review.md")
    markdown_path.write_text(curriculum_review_markdown(), encoding="utf-8")
