import type { DemoDailyWin, NextWinState } from './api/types.ts';
import { firstWinFailed, homeWinPhase } from './homeState.ts';

export type HomePresentationPhase =
  | 'first_run'
  | 'preparing_first'
  | 'current_unreflected'
  | 'reflected_preparing_next'
  | 'next_ready_pending_presentation'
  | 'next_ready'
  | 'prep_failed';

/**
 * Hold a newly READY Win when Home is still showing a different Win.
 * First-run preparing → READY may appear (spinner completing). Replacing
 * an already-visible Win card must wait for the next intentional focus.
 */
export function shouldHoldPresentedWin(args: {
  presentedWinId: string | null;
  incomingWinId: string | null;
  screenHeld: boolean;
}): boolean {
  if (!args.screenHeld) {
    return false;
  }
  if (!args.presentedWinId || !args.incomingWinId) {
    return false;
  }
  return args.presentedWinId !== args.incomingWinId;
}

export function homePresentationPhase(args: {
  presentedWin: { id: string; has_feedback: boolean } | null;
  latestWin: { id: string; has_feedback: boolean } | null;
  preparationStatus?: string | null;
  pendingReady: boolean;
}): HomePresentationPhase {
  const status = args.preparationStatus ?? null;
  if (status === 'failed' || status === 'invalidated') {
    return 'prep_failed';
  }
  if (args.pendingReady) {
    return 'next_ready_pending_presentation';
  }
  const presented = args.presentedWin;
  if (presented !== null && !presented.has_feedback) {
    return 'current_unreflected';
  }
  if (status === 'generating') {
    return presented?.has_feedback ? 'reflected_preparing_next' : 'preparing_first';
  }
  if (presented === null) {
    return 'first_run';
  }
  if (
    args.latestWin !== null &&
    args.latestWin.id !== presented.id &&
    !args.latestWin.has_feedback
  ) {
    return 'next_ready_pending_presentation';
  }
  if (status === 'ready' && presented.has_feedback === false) {
    return 'next_ready';
  }
  if (presented.has_feedback && status === 'ready' && args.latestWin?.id === presented.id) {
    return 'next_ready';
  }
  if (presented.has_feedback) {
    return status === 'ready' ? 'next_ready' : 'reflected_preparing_next';
  }
  return 'next_ready';
}

export function presentedWinFromState(
  nextWin: NextWinState | null,
  held: DemoDailyWin | null,
  pendingReady: boolean,
): DemoDailyWin | null {
  if (pendingReady && held) {
    return held;
  }
  return nextWin?.daily_win ?? held;
}

export function homeCardPhase(
  presentedWin: { has_feedback: boolean } | null,
  preparationStatus?: string | null,
  pendingReady = false,
) {
  if (pendingReady) {
    return homeWinPhase(presentedWin, presentedWin ? 'ready' : preparationStatus);
  }
  return homeWinPhase(presentedWin, preparationStatus);
}

export function firstRunPrepFailed(
  nextWin: NextWinState | null,
  presentedWin: DemoDailyWin | null,
): boolean {
  return firstWinFailed(nextWin, presentedWin !== null);
}

export function onePrimaryCtaLabel(phase: HomePresentationPhase): string | null {
  switch (phase) {
    case 'first_run':
      return "Create today's Win";
    case 'preparing_first':
    case 'reflected_preparing_next':
    case 'next_ready_pending_presentation':
      return null;
    case 'current_unreflected':
    case 'next_ready':
      return 'Start Daily Win';
    case 'prep_failed':
      return 'Try again';
    default:
      return null;
  }
}
