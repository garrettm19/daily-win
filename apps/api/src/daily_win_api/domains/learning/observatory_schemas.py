"""Development-only Learning Trace and learner-snapshot DTOs.

These are inspectability artifacts. They are not learner truth and must not
include secrets, DB UUIDs, raw prompts, or private notes.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileContextTrace(BaseModel):
    nickname: str
    age_years: int
    grade: str
    selected_goals: list[str]
    relevant_interests: list[str]
    preferred_duration_minutes: int


class SchedulerTrace(BaseModel):
    selected_goal: str
    selected_strand: str
    reason_codes: list[str]
    urgency_class: str
    recent_goal_history: list[str]
    deferred_goals: list[str]
    review_due: bool
    starvation_guard_triggered: bool
    scheduler_version: str
    why_selected: str
    why_deferred: list[str]


class PlacementTrace(BaseModel):
    placement_policy_version: str
    selected_strand: str
    expected_grade_band_entry_skill: str
    expected_entry_label: str
    placement_mode: str
    evidence_sparse: bool
    reason_codes: list[str]


class PriorEvidenceTrace(BaseModel):
    skill_code: str
    parent_friendly_name: str
    band: str
    needs_remediation: bool
    usable_evidence_count: int
    distinct_session_count: int
    most_recent_result: str | None = None
    most_recent_independent_result: str | None = None
    last_practiced_date: str | None = None
    last_independent_success: str | None = None
    prerequisite_state_sufficient: bool


class CurriculumDecisionTrace(BaseModel):
    target_skill: str
    parent_friendly_skill_name: str
    prerequisite_chain: list[str]
    prerequisite_status: list[str]
    grade_band: str | None = None
    standard_reference: str | None = None


class InstructionPlanTrace(BaseModel):
    primary_skill: str
    supporting_skill: str | None = None
    mode: str
    difficulty: str
    scaffold: str
    growth_overlay: str | None = None
    duration_minutes: int
    reason_codes: list[str]
    policy_version: str
    recent_themes_excluded: list[str]
    assessment_objective: str


class AssessmentPlanTrace(BaseModel):
    canonical_probe: str
    expected_outcome: str
    success_criterion: str
    allowed_support: str
    counts_apply: bool
    fresh_item_rule_applies: bool
    probe_kind: str


class RendererTrace(BaseModel):
    prompt_version: str
    model: str
    schema_version: str
    required_renderer_contracts: list[str]
    generation_attempt_count: int
    validation_result: str
    contract_failures: list[str] = Field(default_factory=list)
    safety_result: str
    safety_rule: str | None = None


class GenerationFailureTrace(BaseModel):
    reason_code: str
    failed_contract_ids: list[str] = Field(default_factory=list)
    safety_rule: str | None = None
    parent_safe_summary: str


class ReflectionTrace(BaseModel):
    academic_result: str | None = None
    correct_count: int | None = None
    attempted_count: int | None = None
    persistence_observation: str | None = None
    difficulty: str | None = None
    engagement: str | None = None
    completion: str | None = None


class SkillStateDelta(BaseModel):
    skill_code: str
    parent_friendly_name: str
    before_band: str
    after_band: str
    before_sessions: int
    after_sessions: int
    before_needs_remediation: bool
    after_needs_remediation: bool
    evidence_result: str | None = None


class WhyNotTrace(BaseModel):
    why_not_next_skill: str
    why_not_previous_skill: str
    why_not_second_goal: str
    why_not_review: str | None = None
    why_not_terminal: str | None = None
    why_this_coaching: str | None = None
    why_wait: str | None = None
    why_model_allowed: str | None = None
    why_reduce: str | None = None
    why_ask_for_explanation: str | None = None


class CoachProtocolTrace(BaseModel):
    protocol_version: str
    expected_challenge: str
    initial_parent_behavior: str
    prompt_ceiling: str
    frustration_response: str
    assessment_boundary: str
    coach_card: list[str] = Field(default_factory=list)
    teach_the_coach: bool = False


class WeeklyContextTrace(BaseModel):
    summary_version: str | None = None
    wins_this_week: int = 0
    academic_areas: list[str] = Field(default_factory=list)
    next_week_focus: str | None = None


class FirstWinTimingTrace(BaseModel):
    profile_saved_ms: int | None = None
    preparation_started_ms: int | None = None
    terra_completed_ms: int | None = None
    win_ready_ms: int | None = None
    raw_model_ms: int | None = None
    onboarding_ms: int | None = None
    visible_wait_ms: int | None = None
    ready_before_guide: bool | None = None
    trigger: str | None = None


class NextWinPreparationTrace(BaseModel):
    status: str
    trigger: str | None = None
    generated_after_reflection: bool = False
    attempt_count: int | None = None
    error_code: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None
    plan_valid: bool | None = None


class GenerationPerformanceTrace(BaseModel):
    latest_total_ms: int | None = None
    latest_provider_ms: int | None = None
    latest_validation_ms: int | None = None
    latest_attempts: int | None = None
    latest_input_tokens: int | None = None
    latest_output_tokens: int | None = None
    generation_intent: str | None = None
    generation_intent_label: str | None = None
    reasoning_effort: str | None = None
    requested_service_tier: str | None = None
    returned_service_tier: str | None = None
    recent_count: int = 0
    median_total_ms: int | None = None
    median_provider_ms: int | None = None
    min_total_ms: int | None = None
    max_total_ms: int | None = None


class LearningTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generation_status: str
    profile: ProfileContextTrace
    placement: PlacementTrace
    scheduler: SchedulerTrace | None = None
    relevant_prior_evidence: list[PriorEvidenceTrace]
    curriculum: CurriculumDecisionTrace
    instruction_plan: InstructionPlanTrace
    assessment: AssessmentPlanTrace
    renderer: RendererTrace
    reflection: ReflectionTrace | None = None
    state_update: list[SkillStateDelta] = Field(default_factory=list)
    next_win_implication: str
    why_not: WhyNotTrace
    generation_failure: GenerationFailureTrace | None = None
    win_created_at: datetime | None = None
    win_title: str | None = None
    coach_protocol: CoachProtocolTrace | None = None
    weekly_context: WeeklyContextTrace | None = None
    next_win_preparation: NextWinPreparationTrace | None = None


class AcademicSnapshotItem(BaseModel):
    domain_label: str
    skill_name: str
    skill_code: str
    band: str
    band_label: str
    session_count: int
    latest_result: str | None = None
    last_independent: str | None = None


class GrowthSnapshotItem(BaseModel):
    skill_name: str
    skill_code: str
    latest_signal: str | None = None
    summary: str


class LearnerSnapshot(BaseModel):
    nickname: str
    academic: list[AcademicSnapshotItem]
    growth: list[GrowthSnapshotItem]


class CurriculumGraphNode(BaseModel):
    skill_code: str
    parent_friendly_name: str
    band: str
    is_target: bool
    is_blocked: bool
    is_retained: bool


class CurriculumGraphTrace(BaseModel):
    strand: str
    target_skill: str | None = None
    nodes: list[CurriculumGraphNode]


class NextWinPreview(BaseModel):
    likely_target: str
    likely_parent_friendly_name: str
    likely_mode: str
    likely_scaffold: str
    likely_difficulty: str
    reason: str
    scheduled_goal: str | None = None
    scheduler_reason: str | None = None
    note: str = "Preview only. Does not create a Daily Win."


class EngineVersionReport(BaseModel):
    curriculum_version: str
    placement_policy: str
    instruction_policy: str
    instruction_scheduler: str
    academic_projector: str
    growth_projector: str
    prompt_version: str
    renderer_model: str
    renderer_schema_version: str
    safety_validator_version: str
    probe_catalog_version: str
    coach_protocol: str


class ContextBudgetComponent(BaseModel):
    name: str
    characters: int
    estimated_tokens: int


class RedactedContextReport(BaseModel):
    events_included: int
    prior_wins_included: int
    profile_fields_included: list[str]
    planner_fields_included: list[str]
    serialized_characters: int
    estimated_tokens: int
    components: list[ContextBudgetComponent]
    redacted_context: dict[str, object]


class LearningQaBundle(BaseModel):
    """One-screen developer bundle. Development/demo only."""

    engine: EngineVersionReport
    snapshot: LearnerSnapshot
    graph: CurriculumGraphTrace
    latest_trace: LearningTrace | None = None
    next_preview: NextWinPreview | None = None
    latest_win_title: str | None = None
    latest_has_feedback: bool = False
    setup_required: bool = False
    next_win_preparation: NextWinPreparationTrace | None = None
    generation_performance: GenerationPerformanceTrace | None = None
    first_win_timing: FirstWinTimingTrace | None = None
