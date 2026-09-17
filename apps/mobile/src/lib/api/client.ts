export function getApiBaseUrl(): string {
  const value = process.env.EXPO_PUBLIC_API_URL;
  if (!value) {
    throw new Error(
      'EXPO_PUBLIC_API_URL is missing. Copy apps/mobile/.env.example to apps/mobile/.env.local and set this computer LAN IP.',
    );
  }
  return value.replace(/\/$/, '');
}

export async function apiGet<T>(path: string): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`;
  let response: Response;
  try {
    response = await fetch(url);
  } catch {
    throw new Error(
      'Could not reach the Daily Win API. Confirm the API is running and this phone is on the same Wi-Fi.',
    );
  }

  if (!response.ok) {
    throw new Error(
      `The child profile could not be loaded from the server (${response.status}).`,
    );
  }

  return (await response.json()) as T;
}
