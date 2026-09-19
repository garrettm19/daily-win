"""V0.3.3 educational-quality eval: planner, learner, probes, renderer, integrity."""

from daily_win_api.ai.decision.fake import FakeDecisionGateway
from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.domains.learning.enums import AcademicBand, InstructionMode
from daily_win_api.domains.learning.integrity import curriculum_integrity_errors
from daily_win_api.domains.learning.planner import plan_instruction
from daily_win_api.eval.builders import planner_input
from daily_win_api.eval.curriculum_audit import audit_curriculum
from daily_win_api.eval.decision_fixtures import (
    labelled_verification_cases,
    score_verification,
)
from daily_win_api.eval.expert_report import (
    EXPERT_SCORE_KEYS,
    curriculum_review_markdown,
    curriculum_review_sections,
    empty_expert_record,
)
from daily_win_api.eval.learner_cases import evaluate_learner_case, learner_state_cases
from daily_win_api.eval.planner_cases import evaluate_planner_case, planner_golden_cases
from daily_win_api.eval.probe_quality import labelled_probe_cases, probe_is_valid
from daily_win_api.eval.progress_claims import overclaim_hits
from daily_win_api.eval.renderer_quality import (
    anti_pattern_flags,
    labelled_anti_pattern_drafts,
    parent_burden,
    theme_variants_keep_instruction,
)
from daily_win_api.eval.runner import build_parser
from daily_win_api.eval.suites import run_offline_suites
from daily_win_api.eval.support import SUPPORT_LEVELS


def test_planner_golden_case_count_and_pass() -> None:
    cases = planner_golden_cases()
    assert 40 <= len(cases) <= 80
    errors = [item for case in cases for item in evaluate_planner_case(case)]
    assert errors == []


def test_planner_why_not_blocks_later_skills() -> None:
    blocked = {
        "math_g1_within20_missing_prereq": "math.addition.within_20",
        "reading_cvc_blocked": "reading.phonics.blend_cvc",
        "writing_org_missing_sentence": "writing.organization.sequence_events",
        "reading_inference_blocked": "reading.comprehension.simple_inference",
        "fluency_blocked_without_cvc": "reading.fluency.smooth_oral",
        "spelling_blocked_without_cvc": "writing.spelling.high_frequency",
        "equal_groups_blocked_without_addition": "math.multiplication.equal_groups",
        "supporting_later_addition_blocked": "math.addition.within_10",
    }
    by_id = {case.id: case for case in planner_golden_cases()}
    for case_id, forbidden in blocked.items():
        case = by_id[case_id]
        assert forbidden in case.forbid
        assert evaluate_planner_case(case) == []


def test_planner_interest_change_does_not_change_skill() -> None:
    by_id = {case.id: case for case in planner_golden_cases()}
    soccer = by_id["theme_soccer_same_skill"]
    dinosaurs = by_id["theme_dinosaurs_same_skill"]
    assert soccer.expected_skill == dinosaurs.expected_skill
    assert soccer.data.interests != dinosaurs.data.interests
    assert evaluate_planner_case(soccer) == []
    assert evaluate_planner_case(dinosaurs) == []


def test_learner_state_golden_cases() -> None:
    cases = learner_state_cases()
    ids = {case.id for case in cases}
    assert {
        "case_a_step_incorrect",
        "case_a_spaced_independent",
        "case_b_two_independent_same_day_same_session",
        "case_b_two_independent_same_day_two_sessions",
        "case_c_retained_then_weak",
        "case_d_lucky_independent_among_incorrect",
    } <= ids
    errors = [item for case in cases for item in evaluate_learner_case(case)]
    assert errors == []


def test_two_independent_same_day_are_not_retained() -> None:
    by_id = {case.id: case for case in learner_state_cases()}
    same_session = by_id["case_b_two_independent_same_day_same_session"]
    two_sessions = by_id["case_b_two_independent_same_day_two_sessions"]
    assert AcademicBand.RETAINED in same_session.forbid_bands
    assert AcademicBand.RETAINED in two_sessions.forbid_bands
    assert two_sessions.expected_band is AcademicBand.DEMONSTRATED


def test_probe_quality_rejects_affect_and_generic_fallback() -> None:
    by_id = {case.id: case for case in labelled_probe_cases()}
    assert by_id["bad_enjoy_story"].expected_valid is False
    assert by_id["bad_neat_writing"].expected_valid is False
    assert by_id["bad_generic_fallback"].expected_valid is False
    assert probe_is_valid(
        by_id["bad_enjoy_story"].skill_code, by_id["bad_enjoy_story"].probe
    ) is False
    catalog = [
        case
        for case in labelled_probe_cases()
        if case.id.startswith("catalog_")
    ]
    assert len(catalog) == 20
    assert all(case.expected_valid for case in catalog)
    assert all(probe_is_valid(case.skill_code, case.probe) for case in catalog)


def test_theme_variants_keep_instruction() -> None:
    assert theme_variants_keep_instruction() == []


def test_anti_pattern_fixtures() -> None:
    for _name, draft, expected in labelled_anti_pattern_drafts():
        flags = anti_pattern_flags(draft)
        if expected is None:
            assert flags == ()
        else:
            assert expected in flags


def test_parent_burden_fake_draft_is_within_promise() -> None:
    burden = parent_burden(valid_daily_win_draft())
    assert burden.flags == ()
    assert burden.material_count <= 4
    assert burden.duration_minutes <= 20


def test_support_semantics_are_shared() -> None:
    assert "without instructional help" in SUPPORT_LEVELS["correct_independently"]
    assert "does not contain the answer" in SUPPORT_LEVELS["correct_after_light_prompt"]
    assert "partial answer" in SUPPORT_LEVELS["correct_after_significant_help"]


def test_progress_copy_does_not_overclaim() -> None:
    assert overclaim_hits() == ()


def test_curriculum_audit_records_gaps_without_expanding_taxonomy() -> None:
    audit = audit_curriculum()
    assert audit.version == "curriculum_v1"
    assert len(audit.skills) == 20
    assert audit.missing_prerequisite_edges == ()
    assert audit.skills_without_specific_probe == ()
    assert audit.missing_standard_refs == ()
    assert audit.overly_broad == ()
    assert (
        "math.number_sense.compare",
        "math.fractions.halves_fourths",
    ) in audit.rejected_prerequisite_edges
    assert all(skill.has_specific_probe for skill in audit.skills)


def test_decision_gateway_labelled_eval_stays_offline() -> None:
    cases = labelled_verification_cases()
    names = {item["id"] for item in cases}
    assert "probe_target_mismatch" in names
    assert "repeats_recent_title" in names
    report = score_verification(cases, FakeDecisionGateway())
    assert report["classification_accuracy"] == 1.0
    assert report["safety_false_negatives"] == 0
    assert report["confidence_calibration"] is None


def test_expert_review_scores_are_empty_and_not_learner_data() -> None:
    plan = plan_instruction(planner_input(goals=(("math.addition", 1),)))
    record = empty_expert_record(
        profile_summary="Synthetic Nova, age 8, grade 3.",
        learner_state={"math.addition.within_10": "not_observed"},
        plan=plan,
    )
    assert set(record.human_scores) == set(EXPERT_SCORE_KEYS)
    assert all(value is None for value in record.human_scores.values())
    assert record.verdict is None
    assert "not learner data" in record.note


def test_eval_cli_exposes_suite_and_model_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(["--suite", "planner"])
    assert args.suite == "planner"
    models = parser.parse_args(["--model", "gpt-5.6-luna", "--sample", "5"])
    assert models.model == "gpt-5.6-luna"
    assert models.sample == 5
    terra = parser.parse_args(["--model", "gpt-5.6-terra", "--sample", "5"])
    assert terra.model == "gpt-5.6-terra"
    sol = parser.parse_args(["--model", "gpt-5.6-sol", "--sample", "5"])
    assert sol.model == "gpt-5.6-sol"
    bakeoff = parser.parse_args(["--compare", "terra-luna"])
    assert bakeoff.compare == "terra-luna"
    rescore = parser.parse_args(["--rescore-bakeoff"])
    assert rescore.rescore_bakeoff == "DEFAULT"


def test_offline_suites_pass_and_record_versions() -> None:
    report = run_offline_suites()
    assert report["all_passed"] is True
    assert report["curriculum_version"] == "curriculum_v1"
    assert report["instruction_policy_version"] == "instruction_policy_v2"
    assert report["projector_version"] == "academic_projector_v1"
    assert report["probe_catalog_version"] == "assessment_probe_v2"
    assert 40 <= report["planner_case_count"] <= 80
    assert report["curriculum"]["skills_without_specific_probe"] == []
    assert report["curriculum_review"]
    assert len(report["curriculum_review"]) == 20
    assert "Not learner memory" in report["note"]


def test_emerging_plus_remediation_flag_is_remediation() -> None:
    case = next(
        item
        for item in planner_golden_cases()
        if item.id == "emerging_plus_flag_is_remediation"
    )
    assert case.expected_mode is InstructionMode.REMEDIATION
    assert evaluate_planner_case(case) == []


def test_curriculum_integrity_invariants() -> None:
    assert curriculum_integrity_errors() == []


def test_curriculum_review_export_covers_each_academic_skill() -> None:
    sections = curriculum_review_sections()
    assert len(sections) == 20
    codes = {item["skill"] for item in sections}
    assert "math.addition.within_10" in codes
    assert "reading.comprehension.main_idea" in codes
    markdown = curriculum_review_markdown()
    assert "## Main idea" in markdown
    assert "Probe:" in markdown
    assert "Success criterion:" in markdown
