export const API_TIMEOUT_MS = {
  health: 8_000,
  read: 12_000,
  mutate: 18_000,
  generate: 75_000,
} as const;

export type ApiTimeoutKind = keyof typeof API_TIMEOUT_MS;

export function timeoutForRequest(
  method: string,
  path: string,
): number {
  const upper = method.toUpperCase();
  if (path === '/health' || path.startsWith('/health?')) {
    return API_TIMEOUT_MS.health;
  }
  if (path.includes('/daily-wins/generate')) {
    return API_TIMEOUT_MS.generate;
  }
  if (upper === 'GET') {
    return API_TIMEOUT_MS.read;
  }
  return API_TIMEOUT_MS.mutate;
}
