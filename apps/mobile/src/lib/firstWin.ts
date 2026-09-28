export function visibleWaitMs(
  rawModelMs: number | null | undefined,
  onboardingMs: number | null | undefined,
): number | null {
  if (rawModelMs == null) {
    return null;
  }
  const consumed = Math.max(0, onboardingMs ?? 0);
  return Math.max(0, rawModelMs - consumed);
}

export function readyBeforeGuide(
  rawModelMs: number | null | undefined,
  onboardingMs: number | null | undefined,
): boolean | null {
  if (rawModelMs == null || onboardingMs == null) {
    return null;
  }
  return visibleWaitMs(rawModelMs, onboardingMs) === 0;
}

export const GUIDE_SCREENS = [
  {
    title: '20 minutes. One challenge.',
    body: 'Daily Win gives you the plan and how to coach it. You and your child do it together, away from the screen.',
  },
  {
    title: "Don't rescue too fast",
    body: 'Ask before telling. Wait a beat. One skill at a time.',
  },
  {
    title: 'Hard is okay',
    body: 'A good challenge can feel tricky. Support is always available — you decide when to step in.',
  },
  {
    title: 'Report what actually happened',
    body: 'Tell Daily Win what you saw. That is how tomorrow’s challenge adapts.',
  },
] as const;
