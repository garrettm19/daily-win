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
