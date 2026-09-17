export type HomeWinPhase = 'none' | 'reflection_pending' | 'reflected';

export function homeWinPhase(
  dailyWin: { has_feedback: boolean } | null,
): HomeWinPhase {
  if (dailyWin === null) {
    return 'none';
  }
  if (!dailyWin.has_feedback) {
    return 'reflection_pending';
  }
  return 'reflected';
}
