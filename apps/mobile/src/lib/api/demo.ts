import { ApiError, apiGet, apiPost } from '@/lib/api/client';
import type {
  DailyWinFeedbackCreate,
  DemoChildProfile,
  DemoDailyWin,
  DemoFeedbackRead,
} from '@/lib/api/types';

export function fetchDemoChildProfile(): Promise<DemoChildProfile> {
  return apiGet<DemoChildProfile>('/api/v1/demo/child-profile');
}

export async function generateDemoDailyWin(): Promise<DemoDailyWin> {
  try {
    return await apiPost<DemoDailyWin>('/api/v1/demo/daily-wins/generate');
  } catch (error) {
    if (error instanceof ApiError && error.errorCode === 'feedback_required') {
      throw new ApiError(
        'Reflect on the current Daily Win before creating another.',
        error.status,
        error.errorCode,
      );
    }
    throw new ApiError(
      'Daily Win could not be created. Please try again.',
      error instanceof ApiError ? error.status : undefined,
      error instanceof ApiError ? error.errorCode : undefined,
    );
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
      );
    }
    throw new ApiError(
      'Reflection could not be saved. Please try again.',
      error instanceof ApiError ? error.status : undefined,
      error instanceof ApiError ? error.errorCode : undefined,
    );
  }
}
