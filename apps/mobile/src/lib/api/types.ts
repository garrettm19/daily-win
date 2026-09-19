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

export type DemoAcademicProgress = {
  domain_label: string;
  skill_name: string;
  state_label: string;
  recent_evidence: string | null;
  evidence_label: string;
  session_count: number;
  supporting_copy: string;
  needs_review?: boolean;
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


