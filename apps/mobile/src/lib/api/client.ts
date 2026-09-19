import { API_BASE_URL, healthRequestUrl } from '@/lib/api/apiBase';
import { setBackendStatus } from '@/lib/api/backendStatus';
import {
  DEMO_SESSION_ERROR_CODE,
  PARENT_ERRORS,
  type ApiErrorKind,
  classifyFetchFailure,
  shouldMarkBackendUnavailable,
} from '@/lib/api/parentErrors';
import { timeoutForRequest } from '@/lib/api/timeouts';
import {
  DemoSessionError,
  getCachedTesterFingerprint,
  requireDemoSession,
} from '@/lib/demoSession';

let loggedApiBase = false;

function isDev(): boolean {
  if (typeof __DEV__ !== 'undefined' && __DEV__) {
    return true;
  }
  return (globalThis as { __DEV__?: boolean }).__DEV__ === true;
}

function logApiBaseOnce(): void {
  if (!isDev() || loggedApiBase) {
    return;
  }
  loggedApiBase = true;
  console.log('[DailyWin Dev] API base:', API_BASE_URL ?? '(missing)');
}

function isHealthPath(path: string): boolean {
  return path === '/health' || path.startsWith('/health?');
}

function describeHealthFailure(error: unknown): string {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  return String(error);
}

function requestHeaders(init?: RequestInit): Record<string, string> {
  const headers: Record<string, string> = {};
  const source = init?.headers;
  if (!source) {
    return headers;
  }
  if (Array.isArray(source)) {
    for (const [key, value] of source) {
      headers[key] = value;
    }
    return headers;
  }
  if (typeof Headers !== 'undefined' && source instanceof Headers) {
    source.forEach((value, key) => {
      headers[key] = value;
    });
    return headers;
  }
  return { ...(source as Record<string, string>) };
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly errorCode?: string,
    readonly kind: ApiErrorKind = 'http',
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
  if (!API_BASE_URL) {
    throw new Error('EXPO_PUBLIC_API_URL is missing.');
  }
  return API_BASE_URL;
}

export type RequestOptions = {
  timeoutMs?: number;
  includeSession?: boolean;
};

export function apiGet<T>(path: string, options?: RequestOptions): Promise<T> {
  return request<T>(path, { method: 'GET' }, options);
}

export function apiPost<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<T> {
  return request<T>(
    path,
    {
      method: 'POST',
      headers:
        body === undefined
          ? undefined
          : {
              'Content-Type': 'application/json',
            },
      body: body === undefined ? undefined : JSON.stringify(body),
    },
    options,
  );
}

export function apiPatch<T>(
  path: string,
  body: unknown,
  options?: RequestOptions,
): Promise<T> {
  return request<T>(
    path,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    options,
  );
}

function isAbortError(error: unknown): boolean {
  if (error instanceof Error && error.name === 'AbortError') {
    return true;
  }
  return (
    typeof error === 'object' &&
    error !== null &&
    'name' in error &&
    (error as { name: unknown }).name === 'AbortError'
  );
}

function demoSessionUnavailableError(): ApiError {
  return new ApiError(
    PARENT_ERRORS.demoSession,
    undefined,
    DEMO_SESSION_ERROR_CODE,
    'demo_session',
  );
}

async function attachDemoSession(
  headers: Record<string, string>,
): Promise<{ testerFingerprint: string | null }> {
  try {
    const session = await requireDemoSession();
    headers['X-Demo-Session'] = session;
    return { testerFingerprint: getCachedTesterFingerprint() };
  } catch (error) {
    if (isDev()) {
      const name = error instanceof Error ? error.name : 'Error';
      const message = error instanceof Error ? error.message : String(error);
      console.log(`[DailyWin Dev] demo session failure: ${name}: ${message}`);
    }
    if (error instanceof DemoSessionError || error instanceof ApiError) {
      throw error instanceof ApiError ? error : demoSessionUnavailableError();
    }
    throw demoSessionUnavailableError();
  }
}

async function request<T>(
  path: string,
  init?: RequestInit,
  options?: RequestOptions,
): Promise<T> {
  logApiBaseOnce();
  const health = isHealthPath(path);
  const method = init?.method ?? 'GET';
  const includeSession = health ? false : (options?.includeSession ?? true);

  if (!API_BASE_URL) {
    setBackendStatus('unavailable');
    if (isDev() && health) {
      console.log('[DailyWin Dev] health failure:', 'API URL missing');
    }
    throw new ApiError(
      "Daily Win isn't connected right now.",
      undefined,
      'api_url_missing',
      'unavailable',
    );
  }

  const url = health ? healthRequestUrl(API_BASE_URL) : `${API_BASE_URL}${path}`;
  const headers = requestHeaders(init);

  if (includeSession) {
    const attached = await attachDemoSession(headers);
    const headerValue = headers['X-Demo-Session'];
    if (!headerValue) {
      throw demoSessionUnavailableError();
    }
    if (isDev()) {
      console.log(`[DailyWin Dev] demo request: ${method} ${path}`);
      console.log('[DailyWin Dev] demo session attached: true');
      if (attached.testerFingerprint) {
        console.log(`[DailyWin Dev] tester: ${attached.testerFingerprint}`);
      }
    }
  }

  const timeoutMs = options?.timeoutMs ?? timeoutForRequest(method, path);
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  let response: Response;
  try {
    if (isDev() && health) {
      console.log('[DailyWin Dev] health request:', url);
    }
    response = await fetch(url, {
      ...init,
      headers,
      signal: controller.signal,
    });
    if (isDev() && health) {
      console.log('[DailyWin Dev] health status:', response.status);
    }
    if (isDev() && includeSession) {
      console.log(`[DailyWin Dev] demo response: ${response.status}`);
    }
  } catch (error) {
    const kind = classifyFetchFailure(isAbortError(error));
    if (shouldMarkBackendUnavailable(kind)) {
      setBackendStatus('unavailable');
    }
    if (isDev() && health) {
      console.log('[DailyWin Dev] health failure:', describeHealthFailure(error));
    }
    throw new ApiError(
      "Daily Win isn't connected right now.",
      undefined,
      undefined,
      kind,
    );
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const payload = await readJsonUnknown(response);
    throw new ApiError(
      'The Daily Win API could not complete this request.',
      response.status,
      parseApiErrorCode(payload),
      'http',
    );
  }

  setBackendStatus('connected');

  const payload = await readJsonUnknown(response);
  if (health) {
    return (payload ?? { status: 'ok' }) as T;
  }
  if (payload === undefined) {
    throw new ApiError(
      'The Daily Win API could not complete this request.',
      response.status,
      undefined,
      'http',
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
