export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly errorCode?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const ERROR_CODE_PATTERN = /^[a-z][a-z0-9_]{0,63}$/;

export function parseApiErrorCode(payload: unknown): string | undefined {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
    return undefined;
  }
  const code = (payload as { error_code?: unknown }).error_code;
  if (typeof code !== 'string' || !ERROR_CODE_PATTERN.test(code)) {
    return undefined;
  }
  return code;
}

export function getApiBaseUrl(): string {
  const value = process.env.EXPO_PUBLIC_API_URL;
  if (!value) {
    throw new Error(
      'EXPO_PUBLIC_API_URL is missing. Copy apps/mobile/.env.example to apps/mobile/.env.local and set this computer LAN IP.',
    );
  }
  return value.replace(/\/$/, '');
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers:
      body === undefined
        ? undefined
        : {
            'Content-Type': 'application/json',
          },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`;
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new Error(
      'Could not reach the Daily Win API. Confirm the API is running and this phone is on the same Wi-Fi.',
    );
  }

  if (!response.ok) {
    const payload = await readJsonUnknown(response);
    throw new ApiError(
      'The Daily Win API could not complete this request.',
      response.status,
      parseApiErrorCode(payload),
    );
  }

  const payload = await readJsonUnknown(response);
  if (payload === undefined) {
    throw new ApiError(
      'The Daily Win API could not complete this request.',
      response.status,
    );
  }
  return payload as T;
}

async function readJsonUnknown(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}
