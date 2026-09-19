export const TEXT_LIMITS = {
  nickname: 30,
  customLabel: 40,
  reflectionNote: 400,
  testerFeedback: 1000,
} as const;

export function clampText(value: string, max: number): string {
  if (value.length <= max) {
    return value;
  }
  return value.slice(0, max);
}
