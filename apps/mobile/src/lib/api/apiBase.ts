export function normalizeApiBaseUrl(
  raw: string | undefined | null,
): string | undefined {
  if (typeof raw !== 'string') {
    return undefined;
  }
  const trimmed = raw.trim();
  if (!trimmed) {
    return undefined;
  }
  return trimmed.replace(/\/+$/, '');
}

export function healthRequestUrl(baseUrl: string): string {
  return `${baseUrl}/health`;
}

export function isMissingApiBaseUrl(
  raw: string | undefined | null,
): boolean {
  return normalizeApiBaseUrl(raw) === undefined;
}

const rawApiBaseUrl = process.env.EXPO_PUBLIC_API_URL;

export const API_BASE_URL = normalizeApiBaseUrl(rawApiBaseUrl);
