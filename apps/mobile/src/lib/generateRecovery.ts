export type RecoverableWin = {
  id: string;
  has_feedback: boolean;
} | null;

export function shouldReuseLatestInsteadOfGenerate<
  T extends { has_feedback: boolean },
>(latest: T | null): latest is T {
  return latest !== null && !latest.has_feedback;
}

export function recoveredUnreflectedWin<T extends { has_feedback: boolean }>(
  latest: T | null,
): latest is T {
  return latest !== null && !latest.has_feedback;
}

export function shouldAttemptGenerate(
  latest: { has_feedback: boolean } | null,
): boolean {
  return latest === null || latest.has_feedback;
}
