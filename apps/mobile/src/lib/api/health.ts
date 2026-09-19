import { setBackendStatus } from '@/lib/api/backendStatus';
import { ApiError, apiGet } from '@/lib/api/client';
import { API_TIMEOUT_MS } from '@/lib/api/timeouts';

export type HealthRead = {
  status: string;
};

export async function checkApiHealth(): Promise<HealthRead> {
  return apiGet<HealthRead>('/health', {
    timeoutMs: API_TIMEOUT_MS.health,
    includeSession: false,
  });
}

export async function probeBackend(): Promise<{
  ok: boolean;
  kind: 'connected' | 'unavailable' | 'timeout';
}> {
  try {
    await checkApiHealth();
    return { ok: true, kind: 'connected' };
  } catch (error) {
    if (error instanceof ApiError && error.kind === 'timeout') {
      return { ok: false, kind: 'timeout' };
    }
    return { ok: false, kind: 'unavailable' };
  }
}

export function startAdvisoryHealthProbe(): void {
  setBackendStatus('checking');
  void probeBackend().then((result) => {
    setBackendStatus(result.ok ? 'connected' : 'unavailable');
  });
}
