import type { AcademicResult, DemoDailyWin, DemoProgress } from '@/lib/api/types';

export const SUPPORT_CAPTION =
  'Independent: no instructional help on this part. Light prompt: one short cue that does not give the answer. A lot of help: multiple prompts, modelling, or a partial answer.';

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
