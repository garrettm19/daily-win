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
};

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
};

