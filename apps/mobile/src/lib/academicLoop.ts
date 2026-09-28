import type { AcademicResult, DemoDailyWin, DemoProgress } from '@/lib/api/types';

export const SUPPORT_CAPTION =
  'Independent means no help on the check. A little help is one short cue that does not give the answer.';

export const ACADEMIC_RESULT_OPTIONS: {
  value: AcademicResult;
  label: string;
}[] = [
  { value: 'correct_independently', label: 'Did it independently' },
  { value: 'correct_after_light_prompt', label: 'Did it with a little help' },
  { value: 'correct_after_significant_help', label: 'Needed a lot of help' },
  { value: 'incorrect', label: "Didn't get it yet" },
  { value: 'not_attempted', label: "Didn't try this part" },
];

/** Canonical check caption. Never use generated prompt_label or API support_caption. */
export function checkCaption(
  _assessment?: { prompt_label?: string; support_caption?: string | null } | null,
): string {
  return SUPPORT_CAPTION;
}

export function isCanonicalCheckLabel(label: string): boolean {
  return ACADEMIC_RESULT_OPTIONS.some((item) => item.label === label);
}

export function hasAcademicProbe(win: DemoDailyWin | null): boolean {
  return Boolean(win?.assessment?.what_to_check);
}

export function asksForCounts(win: DemoDailyWin | null): boolean {
  return Boolean(win?.assessment?.asks_for_counts);
}

export function asksAboutSetback(win: DemoDailyWin | null): boolean {
  if (win == null) {
    return true;
  }
  return win.asks_about_setback !== false;
}

export function asksEngagementQuestion(
  difficulty: 'too_easy' | 'about_right' | 'too_hard' | null,
  hasBonus: boolean,
): boolean {
  return difficulty === 'too_easy' || difficulty === 'too_hard' || hasBonus;
}

export function countsAreValid(
  correct: number | null,
  attempted: number | null,
): boolean {
  if (correct === null && attempted === null) {
    return true;
  }
  if (correct === null || attempted === null) {
    return false;
  }
  return correct >= 0 && attempted >= 0 && correct <= attempted;
}

export function changedTodayCopy(win: DemoDailyWin): string | null {
  const planned = win.what_changed_today?.trim();
  if (planned) {
    return planned;
  }
  const generated = win.content.adaptation_summary?.trim();
  return generated || null;
}

export function progressHasAcademicEvidence(progress: DemoProgress): boolean {
  return (progress.academic_skills ?? []).some((item) => item.session_count > 0);
}
