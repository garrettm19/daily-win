import type { NextWinState } from '@/lib/api/types';

export type HomeWinPhase =
  | 'none'
  | 'reflection_pending'
  | 'preparing'
  | 'failed'
  | 'reflected';

export function homeWinPhase(
  dailyWin: { has_feedback: boolean } | null,
  preparationStatus?: string | null,
): HomeWinPhase {
  if (preparationStatus === 'invalidated') {
    return 'failed';
  }
  if (dailyWin !== null && !dailyWin.has_feedback) {
    return 'reflection_pending';
  }
  if (preparationStatus === 'generating') {
    return 'preparing';
  }
  if (preparationStatus === 'failed') {
    return 'failed';
  }
  if (dailyWin === null) {
    return 'none';
  }
  return 'reflected';
}

export function shouldPollPreparation(status?: string | null): boolean {
  return status === 'generating';
}

export function generationStageCopy(_stage?: string | null): string {
  return "Preparing today's challenge...";
}

export function readyWinFromState(state: NextWinState): boolean {
  return state.preparation_status === 'ready' && state.daily_win !== null;
}

export function firstWinFailed(nextWin: NextWinState | null, hasWin: boolean): boolean {
  if (hasWin || nextWin == null) {
    return false;
  }
  if (nextWin.preparation_status !== 'failed') {
    return false;
  }
  return (
    nextWin.trigger === 'first_profile_setup' ||
    nextWin.trigger === 'first_run' ||
    nextWin.trigger == null
  );
}
