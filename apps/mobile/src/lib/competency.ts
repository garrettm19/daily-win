import type { AcademicResult, DemoAcademicProgress, DemoObservation } from './api/types.ts';
import { looksLikeRawEnum, normalizeDisplayText } from './displayNormalize.ts';
import { formatFriendlyDate } from './productCopy.ts';

export const COMPETENCY_STAGES = [
  'not_observed',
  'emerging',
  'developing',
  'demonstrated',
  'retained',
] as const;

export type CompetencyStage = (typeof COMPETENCY_STAGES)[number];

const STAGE_LABEL: Record<CompetencyStage, string> = {
  not_observed: 'Not observed',
  emerging: 'Emerging',
  developing: 'Developing',
  demonstrated: 'Demonstrated',
  retained: 'Retained',
};

const STATE_TO_STAGE: Record<string, CompetencyStage> = {
  'Not enough evidence yet': 'not_observed',
  Emerging: 'emerging',
  Developing: 'developing',
  Demonstrated: 'demonstrated',
  Retained: 'retained',
};

export function stageIndex(stage: CompetencyStage): number {
  return COMPETENCY_STAGES.indexOf(stage);
}

export function stageLabel(stage: CompetencyStage): string {
  return STAGE_LABEL[stage];
}

export function stageFromProgress(skill: DemoAcademicProgress): CompetencyStage {
  const raw = skill.band?.trim().toLowerCase();
  if (raw && (COMPETENCY_STAGES as readonly string[]).includes(raw)) {
    return raw as CompetencyStage;
  }
  return STATE_TO_STAGE[skill.state_label] ?? 'not_observed';
}

export type IndependenceLevel = 'independent' | 'light_help' | 'significant_help' | 'not_yet';

const RESULT_INDEPENDENCE: Record<string, IndependenceLevel> = {
  correct_independently: 'independent',
  correct_after_light_prompt: 'light_help',
  correct_after_significant_help: 'significant_help',
  incorrect: 'not_yet',
  not_attempted: 'not_yet',
};

const INDEPENDENCE_LABEL: Record<IndependenceLevel, string> = {
  independent: 'Independent',
  light_help: 'Light help',
  significant_help: 'Significant help',
  not_yet: 'Not yet',
};

const INDEPENDENCE_RANK: Record<IndependenceLevel, number> = {
  independent: 3,
  light_help: 2,
  significant_help: 1,
  not_yet: 0,
};

export function independenceFromResult(
  result: string | null | undefined,
): IndependenceLevel | null {
  if (!result) {
    return null;
  }
  return RESULT_INDEPENDENCE[result] ?? null;
}

export function independenceLabel(level: IndependenceLevel): string {
  return INDEPENDENCE_LABEL[level];
}

export function independencePoints(skill: DemoAcademicProgress): IndependenceLevel[] {
  const checks = skill.recent_checks ?? [];
  const points: IndependenceLevel[] = [];
  for (const check of [...checks].reverse()) {
    const level = independenceFromResult(check.result);
    if (level) {
      points.push(level);
    }
  }
  return points.slice(-6);
}

export function independenceTrendCopy(points: IndependenceLevel[]): string {
  if (points.length === 0) {
    return 'Still gathering evidence';
  }
  if (points.length === 1) {
    return 'Still gathering evidence';
  }
  const last = points[points.length - 1];
  const prior = points[points.length - 2];
  const lastTwo = points.slice(-2);
  if (lastTwo.every((item) => item === 'independent')) {
    return 'Independent in the last two checks';
  }
  if (INDEPENDENCE_RANK[last] > INDEPENDENCE_RANK[prior]) {
    return 'Needing less help recently';
  }
  if (INDEPENDENCE_RANK[last] < INDEPENDENCE_RANK[prior]) {
    return 'Needed more support last session';
  }
  const unique = new Set(points.slice(-3));
  if (unique.size > 1) {
    return 'Recent results are mixed';
  }
  return 'Still gathering evidence';
}

export function recentSupportSummary(points: IndependenceLevel[]): string | null {
  if (points.length === 0) {
    return null;
  }
  const counts = { independent: 0, light_help: 0, significant_help: 0, not_yet: 0 };
  for (const point of points.slice(-3)) {
    counts[point] += 1;
  }
  const parts: string[] = [];
  if (counts.independent) {
    parts.push(
      counts.independent === 1 ? 'Independent once' : `Independent ${counts.independent} times`,
    );
  }
  if (counts.light_help) {
    parts.push(
      counts.light_help === 1 ? 'Light help once' : `Light help ${counts.light_help} times`,
    );
  }
  if (counts.significant_help) {
    parts.push(
      counts.significant_help === 1
        ? 'A lot of help once'
        : `A lot of help ${counts.significant_help} times`,
    );
  }
  return parts.slice(0, 2).join(' · ') || null;
}

export function formatCheckDate(value: string): string {
  return formatFriendlyDate(value);
}

export function academicResultLabel(result: AcademicResult | string | null | undefined): string {
  switch (result) {
    case 'correct_independently':
      return 'Independent';
    case 'correct_after_light_prompt':
      return 'Light help';
    case 'correct_after_significant_help':
      return 'Significant help';
    case 'incorrect':
      return "Didn't get it yet";
    case 'not_attempted':
      return "Didn't try this part";
    default:
      return '';
  }
}

export function difficultyLabel(value: string | null | undefined): string {
  switch (value) {
    case 'too_easy':
      return 'Too easy';
    case 'about_right':
      return 'About right';
    case 'too_hard':
      return 'Too hard';
    default:
      return '';
  }
}

export function persistenceLabel(value: string | null | undefined): string {
  switch (value) {
    case 'kept_going_independently':
      return 'Kept going';
    case 'continued_after_prompt':
      return 'Kept going after a prompt';
    case 'needed_significant_help':
      return 'Needed significant help';
    case 'stopped_or_avoided':
      return 'Stopped';
    case 'no_setback_occurred':
      return '';
    default:
      return '';
  }
}

export function selfCorrectionLabel(value: string | null | undefined): string {
  switch (value) {
    case 'self_corrected':
      return 'Yes';
    case 'corrected_after_prompt':
      return 'After a prompt';
    case 'did_not_correct':
      return 'Not this time';
    default:
      return '';
  }
}

export type FormattedObservation = {
  goalName: string;
  summary: string;
};

export function formatObservation(
  item: DemoObservation | null | undefined,
): FormattedObservation | null {
  if (item == null || typeof item !== 'object') {
    return null;
  }
  const goalName = normalizeDisplayText(item.goal_name);
  const summary = normalizeDisplayText(item.summary);
  if (!goalName || looksLikeRawEnum(goalName) || goalName === 'Goal') {
    return null;
  }
  if (!summary || looksLikeRawEnum(summary) || summary === 'Parent observation') {
    return null;
  }
  if (summary === '[object Object]') {
    return null;
  }
  return { goalName, summary };
}

export function uniqueFormattedObservations(
  items: readonly DemoObservation[] | null | undefined,
): FormattedObservation[] {
  const seen = new Set<string>();
  const out: FormattedObservation[] = [];
  for (const item of items ?? []) {
    const formatted = formatObservation(item);
    if (!formatted) {
      continue;
    }
    const key = `${formatted.goalName}:${formatted.summary}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    out.push(formatted);
  }
  return out;
}

export function nextMoveCopy(args: {
  oneThing?: string | null;
  changedToday?: string | null;
  currentAdjustment?: string | null;
}): string | null {
  const candidates = [args.oneThing, args.changedToday, args.currentAdjustment];
  for (const item of candidates) {
    const text = normalizeDisplayText(item);
    if (text) {
      return text;
    }
  }
  return null;
}
