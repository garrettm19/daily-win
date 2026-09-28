import type { DailyWinSegment, DemoDailyWin } from './api/types.ts';
import { hasVisibleText, visibleLines } from './productCopy.ts';

export type SessionStepKind = 'mission' | 'learn' | 'do' | 'grow' | 'bonus' | 'reflect';

export type SessionStep = {
  id: string;
  kind: SessionStepKind;
  label: string;
  segment?: DailyWinSegment;
};

const KIND_LABEL: Record<SessionStepKind, string> = {
  mission: 'Mission',
  learn: 'Learn',
  do: 'Do',
  grow: 'Grow',
  bonus: 'Bonus',
  reflect: 'Result',
};

export function sessionStepLabel(kind: SessionStepKind): string {
  return KIND_LABEL[kind];
}

function segmentIsVisible(segment: DailyWinSegment | undefined): boolean {
  if (!segment) {
    return false;
  }
  return visibleLines(segment.steps).length > 0 || hasVisibleText(segment.title);
}

export function buildSessionSteps(win: DemoDailyWin): SessionStep[] {
  const steps: SessionStep[] = [{ id: 'mission', kind: 'mission', label: KIND_LABEL.mission }];
  const byType = new Map(win.content.segments.map((segment) => [segment.type, segment]));
  const learn = byType.get('LEARN');
  const doing = byType.get('DO');
  const grow = byType.get('GROW');
  if (segmentIsVisible(learn)) {
    steps.push({ id: 'learn', kind: 'learn', label: KIND_LABEL.learn, segment: learn });
  }
  if (segmentIsVisible(doing) || hasVisibleText(win.assessment?.what_to_check)) {
    steps.push({
      id: 'do',
      kind: 'do',
      label: KIND_LABEL.do,
      segment: segmentIsVisible(doing) ? doing : undefined,
    });
  }
  if (segmentIsVisible(grow)) {
    steps.push({ id: 'grow', kind: 'grow', label: KIND_LABEL.grow, segment: grow });
  }
  if (win.bonus_challenge && hasVisibleText(win.bonus_challenge.prompt)) {
    steps.push({ id: 'bonus', kind: 'bonus', label: KIND_LABEL.bonus });
  }
  if (!win.has_feedback) {
    steps.push({ id: 'reflect', kind: 'reflect', label: KIND_LABEL.reflect });
  }
  return steps;
}

export function actionSteps(steps: readonly SessionStep[]): SessionStep[] {
  return steps.filter((step) => step.kind !== 'mission' && step.kind !== 'reflect');
}

export function stepperIndex(steps: readonly SessionStep[], currentId: string): number {
  const actionable = actionSteps(steps);
  const index = actionable.findIndex((step) => step.id === currentId);
  return index;
}

export function historicalLabels(text: string): boolean {
  const lowered = text.toLowerCase();
  return (
    lowered.includes("today's win") ||
    lowered.includes('today’s win') ||
    lowered.includes("today's focus") ||
    lowered.includes('today’s focus')
  );
}
