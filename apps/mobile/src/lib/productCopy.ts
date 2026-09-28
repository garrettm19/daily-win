/** Parent-facing vocabulary and display helpers. Not learner truth. */

import { isSelectableLabel, normalizeDisplayText } from './displayNormalize.ts';

export const DISPLAY_LIMITS = {
  jobBullets: 3,
  noticeChips: 5,
  weeklyBullets: 2,
} as const;

const OPTION_LABELS: Record<string, string> = {
  looked_automatic: 'Looked automatic',
  worked_independently: 'Worked for it independently',
  worked_with_help: 'Worked for it with help',
  noticed_and_fixed: 'Noticed and fixed it',
  needed_a_prompt: 'Needed a prompt',
  did_not_notice: 'Did not notice',
  skipped: 'Skipped',
  loved_it: 'Loved it',
  liked_it: 'Liked it',
  not_into_it: 'Not into it',
  did_not_try: 'Did not try it',
  self_corrected: 'Self-corrected',
  corrected_after_prompt: 'Corrected after a prompt',
  did_not_correct: 'Did not correct',
  not_observed: 'Not observed',
  automatic: 'Automatic',
  effortful_but_independent: 'Effortful, independent',
  effortful_with_support: 'Effortful, with support',
  mental_automatic: 'Knew it',
  counted: 'Counted',
  drew_modelled: 'Drew or modeled',
  decomposed_numbers: 'Broke numbers apart',
  needed_help: 'Needed help',
  guessed_unclear: 'Guessed / unclear',
  sounded_out: 'Sounded it out',
  reread: 'Reread',
  used_context: 'Used context',
  recalled_directly: 'Recalled it',
  needed_prompt: 'Needed a prompt',
  used_known_pattern: 'Used a known pattern',
  reread_own_work: 'Reread their work',
  needed_a_model: 'Needed a model',
  neutral: 'Neutral',
};

export function optionLabel(value: string): string {
  const known = OPTION_LABELS[value];
  if (known) {
    return known;
  }
  const words = normalizeDisplayText(value.split('_').join(' '));
  if (!words) {
    return value;
  }
  const labeled = words.charAt(0).toUpperCase() + words.slice(1);
  return labeled;
}

export function selectableOptionLabel(value: string): string | null {
  const label = optionLabel(value);
  if (!isSelectableLabel(label)) {
    return null;
  }
  return label;
}

export function goalPriorityLabel(priority: number, total: number): string {
  if (total <= 1) {
    return 'Focus';
  }
  if (priority === 1) {
    return '#1 Main focus';
  }
  if (priority === 2) {
    return '#2 Secondary focus';
  }
  return `#${priority} Also in rotation`;
}

export function formatFriendlyDate(
  value: string,
  now: Date = new Date(),
): string {
  const date = parseDate(value);
  if (date === null) {
    return value;
  }
  const today = startOfLocalDay(now);
  const then = startOfLocalDay(date);
  const diffDays = Math.round((today.getTime() - then.getTime()) / 86_400_000);
  if (diffDays === 0) {
    return 'Today';
  }
  if (diffDays === 1) {
    return 'Yesterday';
  }
  return then.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function formatHistoryDate(value: string): string {
  const date = parseDate(value);
  if (date === null) {
    return value;
  }
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function formatWeekRange(start: string, end: string): string {
  const from = formatFriendlyDate(start);
  const to = formatFriendlyDate(end);
  if (from === to) {
    return from;
  }
  return `${stripRelative(start)} – ${stripRelative(end)}`;
}

export function weeklySparseNote(winsCompleted: number): string | null {
  if (winsCompleted <= 0) {
    return 'Still gathering a picture this week.';
  }
  if (winsCompleted === 1) {
    return 'Only one Win was completed, so this is an early signal.';
  }
  if (winsCompleted === 2) {
    return 'Two Wins this week — an early picture, not a full one.';
  }
  return null;
}

export function hasVisibleText(value: string | null | undefined): boolean {
  return Boolean(value && value.trim());
}

export function visibleLines(
  values: readonly string[] | null | undefined,
  max?: number,
): string[] {
  const lines = (values ?? [])
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
  if (max == null) {
    return lines;
  }
  return lines.slice(0, max);
}

export function materialsForDisplay(
  codes: readonly string[] | undefined,
  labels: Record<string, string>,
): string[] {
  return (codes ?? [])
    .filter((code) => code !== 'NONE')
    .map((code) => labels[code] ?? code.split('_').join(' ').toLowerCase())
    .filter((item) => item.trim().length > 0);
}

export function cuesForSegment<T extends { label: string; text: string }>(
  cues: readonly T[] | null | undefined,
  segmentType: 'LEARN' | 'DO' | 'GROW',
): T[] {
  if (segmentType === 'GROW') {
    return [];
  }
  const seen = new Set<string>();
  const unique: T[] = [];
  for (const cue of cues ?? []) {
    if (!hasVisibleText(cue.label) || !hasVisibleText(cue.text)) {
      continue;
    }
    const key = `${cue.label}:${cue.text}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    unique.push(cue);
    if (unique.length >= 1) {
      break;
    }
  }
  return unique;
}

const GENERIC_COACH = [
  'provide appropriate support',
  'encourage productive struggle',
  'observe learner behavior',
];

export function containsGenericCoachLanguage(text: string): boolean {
  const lowered = text.toLowerCase();
  return GENERIC_COACH.some((item) => lowered.includes(item));
}

const MATERIAL_HINTS: Record<string, string> = {
  paper: 'PAPER',
  pencil: 'PENCIL',
  crayon: 'CRAYONS_OR_MARKERS',
  marker: 'CRAYONS_OR_MARKERS',
  tape: 'TAPE',
  card: 'INDEX_CARDS',
  cup: 'PLASTIC_CUPS',
  block: 'BLOCKS',
  book: 'BOOK',
  coin: 'COINS',
  ball: 'SOFT_BALL',
  timer: 'TIMER',
};

export function unlistedDoMaterials(
  doSteps: readonly string[],
  materials: readonly string[],
): string[] {
  const listed = new Set(materials.map((item) => item.toUpperCase()));
  const blob = doSteps.join(' ').toLowerCase();
  const missing: string[] = [];
  for (const [hint, code] of Object.entries(MATERIAL_HINTS)) {
    if (blob.includes(hint) && !listed.has(code) && !listed.has('NONE')) {
      missing.push(code);
    }
  }
  return missing;
}

export function longWinNeedsCollapse(stepCount: number): boolean {
  return stepCount >= 12;
}

export function showDiscoveryCard(discovery: {
  active: boolean;
  domains: readonly unknown[];
} | null | undefined): boolean {
  return Boolean(discovery?.active && (discovery?.domains.length ?? 0) >= 2);
}

function stripRelative(value: string): string {
  const date = parseDate(value);
  if (date === null) {
    return value;
  }
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function parseDate(value: string): Date | null {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const day = new Date(`${value}T12:00:00`);
    if (Number.isNaN(day.getTime())) {
      return null;
    }
    return day;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed;
}

function startOfLocalDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}
