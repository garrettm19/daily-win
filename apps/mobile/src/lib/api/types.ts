export type DemoChildSummary = {
  id: string;
  nickname: string;
};

export type DemoBaselineSummary = {
  age_years: number;
  grade: string;
  interests: string[];
  strengths: string[];
  current_difficulties: string[];
  motivators: string[];
  response_to_difficulty: string | null;
  preferred_activity_minutes: number;
  recorded_at: string;
};

export type DemoGoalSummary = {
  priority: number;
  skill_code: string;
  display_name: string;
  domain: string;
};

export type DemoChildProfile = {
  child: DemoChildSummary;
  baseline: DemoBaselineSummary;
  goals: DemoGoalSummary[];
  tester_fingerprint?: string | null;
};

export type ParentBriefing = {
  purpose: string;
  how_to_coach: string;
  watch_for: string;
  avoid: string;
};

export type DailyWinSegment = {
  type: 'LEARN' | 'DO' | 'GROW';
  title: string;
  minutes: number;
  steps: string[];
  parent_role: string;
};

export type DailyWinContent = {
  title: string;
  objective: string;
  duration_minutes: number;
  primary_skill_code: string;
  supporting_skill_codes: string[];
  personalization_summary: string;
  materials: string[];
  parent_briefing: ParentBriefing;
  segments: DailyWinSegment[];
  adaptations: {
    if_too_easy: string;
    if_too_hard: string;
  };
  success_checks: string[];
  observation_focus: string;
  safety_flags: string[];
  adaptation_summary?: string | null;
};

export type ParentAssessment = {
  what_to_check: string;
  success_looks_like: string;
  prompt_label: string;
  asks_for_counts: boolean;
  support_caption?: string | null;
};

export type LearningEngineDebug = {
  target: string;
  mode: string;
  difficulty: string;
  scaffold: string;
  why: string[];
  assessment: string;
  policy: string;
  selected_goal?: string | null;
  expected_entry?: string | null;
  evidence?: string | null;
  placement?: string | null;
  placement_why?: string | null;
};

export type CoachCue = {
  label: string;
  text: string;
};

export type BonusChallenge = {
  code: string;
  category: string;
  title: string;
  minutes: number;
  prompt: string;
  safety: string;
  personal_best: boolean;
  optional?: boolean;
  counts_as_mastery?: boolean;
};

export type DiscoveryWeek = {
  active: boolean;
  headline: string;
  body: string;
  domains: { domain: string; status: string; label: string }[];
};

export type SmartReflection = {
  questions: { id: string; prompt: string }[];
  notice_chips: string[];
  strategy_options: string[];
  self_correction_options: string[];
  effort_options: string[];
  bonus_engagement_options: string[];
};

export type DemoDailyWin = {
  id: string;
  child_nickname: string;
  title: string;
  objective: string;
  duration_minutes: number;
  primary_skill_code: string;
  primary_skill_display_name: string;
  content: DailyWinContent;
  has_feedback: boolean;
  created_at: string;
  assessment?: ParentAssessment | null;
  asks_about_setback?: boolean;
  what_changed_today?: string | null;
  learning_engine?: LearningEngineDebug | null;
  coach_card?: string[];
  coach_cues?: CoachCue[];
  wait_guidance?: string | null;
  bonus_challenge?: BonusChallenge | null;
  smart_reflection?: SmartReflection | null;
  discovery?: DiscoveryWeek | null;
  guide_onboarding?: string[] | null;
  teach_the_coach?: boolean;
  protocol_version?: string | null;
  one_thing_to_improve?: string | null;
  result_snapshot?: DemoResultSnapshot | null;
};

export type NextWinState = {
  daily_win: DemoDailyWin | null;
  preparation_status:
    | 'not_started'
    | 'generating'
    | 'ready'
    | 'failed'
    | 'invalidated'
    | string;
  trigger?: string | null;
  generation_stage?: string | null;
  focus_preview?: string | null;
  coach_preview?: string[];
  generated_after_reflection?: boolean;
  plan_valid?: boolean | null;
  error_code?: string | null;
  attempt_count?: number | null;
  model?: string | null;
  prompt_version?: string | null;
  latency_ms?: number | null;
  backend_elapsed_ms?: number;
  first_win_timing?: {
    profile_saved_ms?: number | null;
    preparation_started_ms?: number | null;
    terra_completed_ms?: number | null;
    win_ready_ms?: number | null;
    raw_model_ms?: number | null;
    onboarding_ms?: number | null;
    visible_wait_ms?: number | null;
    ready_before_guide?: boolean | null;
    trigger?: string | null;
    guide_started_at?: string | null;
    guide_finished_at?: string | null;
    guide_skipped?: boolean | null;
    guide_dwell_ms?: number | null;
  } | null;
};

export type AcademicResult =
  | 'correct_independently'
  | 'correct_after_light_prompt'
  | 'correct_after_significant_help'
  | 'incorrect'
  | 'not_attempted';

export type DailyWinFeedbackCreate = {
  difficulty: 'too_easy' | 'about_right' | 'too_hard';
  engagement: 'low' | 'medium' | 'high';
  completion: 'completed' | 'partially_completed' | 'stopped_early';
  setback_response:
    | 'no_setback_occurred'
    | 'kept_going_independently'
    | 'continued_after_prompt'
    | 'needed_significant_help'
    | 'stopped_or_avoided';
  what_helped?: string;
  additional_note?: string;
  academic_result?: AcademicResult;
  correct_count?: number;
  attempted_count?: number;
  self_correction?: string;
  strategy_observed?: string;
  performance_effort?: string;
  notice_chips?: string[];
  bonus_engagement?: string;
  non_target_error?: string;
};

export type DemoFeedbackRead = {
  feedback_id: string;
  insight: {
    observation: string;
    next_adjustment: string;
  };
  learner_state: {
    skill_code: string;
    latest_signal: string;
    direction: string;
    evidence_count: number;
  };
  academic_observation?: string | null;
  growth_observation?: string | null;
  what_we_learned?: { area: string; summary: string }[];
  what_changes_next?: string | null;
};

export type DemoResetRead = {
  status: string;
  mode?: string;
};

export type DemoSession = {
  status: 'new' | 'ready' | string;
  profile_source?: string | null;
  tester_fingerprint: string;
  profile: DemoChildProfile | null;
};

export type DemoOnboardingCatalog = {
  grades: { code: string; label: string }[];
  interest_suggestions: string[];
  strength_suggestions: string[];
  difficulty_suggestions: string[];
  response_options: string[];
  motivator_suggestions: string[];
  durations: number[];
  goals: { code: string; domain_label: string; label: string }[];
  min_goals: number;
  max_goals: number;
  max_interests: number;
  max_strengths: number;
  max_difficulties: number;
  max_motivators: number;
};

export type DemoProfileWrite = {
  nickname: string;
  age_years: number;
  grade: string;
  interests: string[];
  strengths: string[];
  current_difficulties: string[];
  response_to_difficulty: string;
  goal_codes: string[];
  primary_goal_code: string;
  motivators: string[];
  preferred_activity_minutes: number;
};

export type DemoProfileUpdate = Omit<DemoProfileWrite, 'nickname' | 'age_years' | 'grade'>;

export type DemoGoalProgress = {
  display_name: string;
  latest_observation: string | null;
  current_adjustment: string | null;
  evidence_count: number;
  evidence_label: string;
  still_learning: boolean;
  still_learning_message?: string | null;
  recent_pattern?: string | null;
};

export type DemoAcademicCheck = {
  occurred_at: string;
  result: string;
};

export type DemoAcademicProgress = {
  domain_label: string;
  skill_name: string;
  state_label: string;
  recent_evidence: string | null;
  evidence_label: string;
  session_count: number;
  supporting_copy: string;
  needs_review?: boolean;
  band?: string;
  recent_checks?: DemoAcademicCheck[];
};

export type DemoResultSnapshot = {
  difficulty?: string | null;
  academic_result?: string | null;
  setback_response?: string | null;
  completion?: string | null;
  engagement?: string | null;
};

export type DemoStateGuideItem = {
  label: string;
  explanation: string;
};

export type DemoObservation = {
  goal_name: string;
  summary: string;
  source: string;
};

export type DemoDailyWinSummary = {
  id: string;
  title: string;
  created_at: string;
  primary_focus: string;
  has_feedback: boolean;
  is_adaptive: boolean;
};

export type LearningQaBundle = {
  engine: {
    curriculum_version: string;
    placement_policy: string;
    instruction_policy: string;
    instruction_scheduler: string;
    academic_projector: string;
    growth_projector: string;
    prompt_version: string;
    renderer_model: string;
    renderer_schema_version: string;
    safety_validator_version: string;
    probe_catalog_version: string;
    coach_protocol?: string;
  };
  snapshot: {
    nickname: string;
    academic: {
      domain_label: string;
      skill_name: string;
      skill_code: string;
      band: string;
      band_label: string;
      session_count: number;
      latest_result: string | null;
      last_independent: string | null;
    }[];
    growth: {
      skill_name: string;
      skill_code: string;
      latest_signal: string | null;
      summary: string;
    }[];
  };
  graph: {
    strand: string;
    target_skill: string | null;
    nodes: {
      skill_code: string;
      parent_friendly_name: string;
      band: string;
      is_target: boolean;
      is_blocked: boolean;
      is_retained: boolean;
    }[];
  };
  latest_trace: Record<string, unknown> | null;
  next_preview: {
    likely_target: string;
    likely_parent_friendly_name: string;
    likely_mode: string;
    likely_scaffold: string;
    likely_difficulty: string;
    reason: string;
    scheduled_goal?: string | null;
    scheduler_reason?: string | null;
    note: string;
  } | null;
  latest_win_title: string | null;
  latest_has_feedback: boolean;
  setup_required: boolean;
  next_win_preparation?: {
    status: string;
    trigger?: string | null;
    generated_after_reflection?: boolean;
    attempt_count?: number | null;
    error_code?: string | null;
    model?: string | null;
    prompt_version?: string | null;
    latency_ms?: number | null;
    plan_valid?: boolean | null;
  } | null;
  generation_performance?: {
    latest_total_ms?: number | null;
    latest_provider_ms?: number | null;
    latest_validation_ms?: number | null;
    latest_attempts?: number | null;
    latest_input_tokens?: number | null;
    latest_output_tokens?: number | null;
    generation_intent?: string | null;
    generation_intent_label?: string | null;
    reasoning_effort?: string | null;
    requested_service_tier?: string | null;
    returned_service_tier?: string | null;
    recent_count?: number;
    median_total_ms?: number | null;
    median_provider_ms?: number | null;
    min_total_ms?: number | null;
    max_total_ms?: number | null;
  } | null;
  first_win_timing?: {
    profile_saved_ms?: number | null;
    preparation_started_ms?: number | null;
    terra_completed_ms?: number | null;
    win_ready_ms?: number | null;
    raw_model_ms?: number | null;
    onboarding_ms?: number | null;
    visible_wait_ms?: number | null;
    ready_before_guide?: boolean | null;
    trigger?: string | null;
    guide_started_at?: string | null;
    guide_finished_at?: string | null;
    guide_skipped?: boolean | null;
    guide_dwell_ms?: number | null;
  } | null;
};

export type WeeklyCoachReport = {
  week_start: string;
  week_end: string;
  summary_version: string;
  source_session_count: number;
  this_week: { wins_completed?: number; academic_areas?: string[] };
  what_looked_strong: string[];
  what_still_took_work: string[];
  how_they_handled_challenge: string[];
  what_they_enjoyed: string[];
  what_changes_next_week: string[];
  one_thing_for_the_parent: string;
  win_of_the_week_candidates: string[];
  emerging_needs: { hint: string; recommendation: string; claim: string }[];
  engagement_memory: {
    recently_enjoyed: string[];
    recently_low: string[];
    low_engagement_categories: string[];
  };
  next_week: {
    primary_academic_focus: string;
    secondary_academic_focus: string | null;
    growth_focus: string | null;
    why: string;
  } | null;
  discovery_progress: string[];
};

export type DemoProgress = {
  nickname: string;
  goals: DemoGoalProgress[];
  academic_skills?: DemoAcademicProgress[];
  growth_skills?: DemoGoalProgress[];
  recent_observations: DemoObservation[];
  recent_daily_wins: DemoDailyWinSummary[];
  state_guide?: DemoStateGuideItem[];
  evidence_disclaimer?: string | null;
};


