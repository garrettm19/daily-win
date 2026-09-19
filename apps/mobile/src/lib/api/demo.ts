import { ApiError, apiGet, apiPatch, apiPost } from '@/lib/api/client';
import { parentMessage } from '@/lib/api/parentErrors';
import { API_TIMEOUT_MS } from '@/lib/api/timeouts';
import {
  recoveredUnreflectedWin,
  shouldReuseLatestInsteadOfGenerate,
} from '@/lib/generateRecovery';
import type {
  DailyWinFeedbackCreate,
  DemoChildProfile,
  DemoDailyWin,
  DemoDailyWinSummary,
  DemoFeedbackRead,
  DemoOnboardingCatalog,
  DemoProfileUpdate,
  DemoProfileWrite,
  DemoProgress,
  DemoResetRead,
  DemoSession,
} from '@/lib/api/types';

export function fetchDemoSession(): Promise<DemoSession> {
  return apiGet<DemoSession>('/api/v1/demo/session');
}

export function fetchOnboardingCatalog(): Promise<DemoOnboardingCatalog> {
  return apiGet<DemoOnboardingCatalog>('/api/v1/demo/onboarding-catalog');
}

export function setupHayesProfile(): Promise<DemoChildProfile> {
  return apiPost<DemoChildProfile>('/api/v1/demo/setup/hayes');
}

export function setupCustomProfile(
  payload: DemoProfileWrite,
): Promise<DemoChildProfile> {
  return apiPost<DemoChildProfile>('/api/v1/demo/setup/profile', payload);
}

export function updateDemoProfile(
  payload: DemoProfileUpdate,
): Promise<DemoChildProfile> {
  return apiPatch<DemoChildProfile>('/api/v1/demo/profile', payload);
}

export function fetchDemoChildProfile(): Promise<DemoChildProfile> {
  return apiGet<DemoChildProfile>('/api/v1/demo/child-profile');
}

export function fetchDemoProgress(): Promise<DemoProgress> {
  return apiGet<DemoProgress>('/api/v1/demo/progress');
}

export function fetchDemoDailyWins(): Promise<DemoDailyWinSummary[]> {
  return apiGet<DemoDailyWinSummary[]>('/api/v1/demo/daily-wins');
}

export async function fetchDemoDailyWin(id: string): Promise<DemoDailyWin | null> {
  try {
    return await apiGet<DemoDailyWin>(`/api/v1/demo/daily-wins/${id}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function fetchLatestDemoDailyWin(): Promise<DemoDailyWin | null> {
  try {
    return await apiGet<DemoDailyWin>('/api/v1/demo/daily-wins/latest');
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function generateDemoDailyWin(): Promise<DemoDailyWin> {
  try {
    return await apiPost<DemoDailyWin>(
      '/api/v1/demo/daily-wins/generate',
      undefined,
      { timeoutMs: API_TIMEOUT_MS.generate },
    );
  } catch (error) {
    if (error instanceof ApiError && error.errorCode === 'feedback_required') {
      throw new ApiError(
        'Reflect on the current Daily Win before creating another.',
        error.status,
        error.errorCode,
        error.kind,
      );
    }
    if (error instanceof ApiError) {
      throw new ApiError(
        parentMessage('generate', error.kind),
        error.status,
        error.errorCode,
        error.kind,
      );
    }
    throw new ApiError(parentMessage('generate'), undefined, undefined, 'unavailable');
  }
}

export async function generateDemoDailyWinSafely(): Promise<DemoDailyWin> {
  const latest = await fetchLatestDemoDailyWin();
  if (shouldReuseLatestInsteadOfGenerate(latest)) {
    return latest;
  }
  try {
    return await generateDemoDailyWin();
  } catch (error) {
    const recovered = await recoverGeneratedWin(error);
    if (recovered) {
      return recovered;
    }
    throw error;
  }
}

async function recoverGeneratedWin(error: unknown): Promise<DemoDailyWin | null> {
  try {
    const latest = await fetchLatestDemoDailyWin();
    if (error instanceof ApiError && error.errorCode === 'feedback_required') {
      return latest;
    }
    if (recoveredUnreflectedWin(latest)) {
      return latest;
    }
  } catch {
    return null;
  }
  return null;
}

export async function submitDemoDailyWinFeedback(
  dailyWinId: string,
  payload: DailyWinFeedbackCreate,
): Promise<DemoFeedbackRead> {
  try {
    return await apiPost<DemoFeedbackRead>(
      `/api/v1/demo/daily-wins/${dailyWinId}/feedback`,
      payload,
    );
  } catch (error) {
    if (error instanceof ApiError && error.errorCode === 'already_submitted') {
      throw new ApiError(
        'This Daily Win already has a reflection.',
        error.status,
        error.errorCode,
        error.kind,
      );
    }
    if (error instanceof ApiError) {
      throw new ApiError(
        parentMessage('saveReflection', error.kind),
        error.status,
        error.errorCode,
        error.kind,
      );
    }
    throw new ApiError(
      parentMessage('saveReflection'),
      undefined,
      undefined,
      'unavailable',
    );
  }
}

export async function resetDemoActivityHistory(): Promise<DemoResetRead> {
  try {
    return await apiPost<DemoResetRead>('/api/v1/demo/reset/activity');
  } catch (error) {
    if (error instanceof ApiError && error.kind === 'demo_session') {
      throw error;
    }
    throw new ApiError(
      "Couldn't reset activity history. Try again.",
      error instanceof ApiError ? error.status : undefined,
      error instanceof ApiError ? error.errorCode : undefined,
      error instanceof ApiError ? error.kind : 'http',
    );
  }
}

export async function restartDemoSession(): Promise<DemoResetRead> {
  try {
    return await apiPost<DemoResetRead>('/api/v1/demo/reset/session');
  } catch (error) {
    if (error instanceof ApiError && error.kind === 'demo_session') {
      throw error;
    }
    throw new ApiError(
      "Couldn't restart the demo. Try again.",
      error instanceof ApiError ? error.status : undefined,
      error instanceof ApiError ? error.errorCode : undefined,
      error instanceof ApiError ? error.kind : 'http',
    );
  }
}

export async function resetDemoState(): Promise<DemoResetRead> {
  return resetDemoActivityHistory();
}
