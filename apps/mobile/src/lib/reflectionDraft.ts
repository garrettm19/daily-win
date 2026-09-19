import type { AcademicResult, DailyWinFeedbackCreate } from '@/lib/api/types';

export type ReflectionDraft = {
  dailyWinId: string;
  difficulty: DailyWinFeedbackCreate['difficulty'] | null;
  engagement: DailyWinFeedbackCreate['engagement'] | null;
  completion: DailyWinFeedbackCreate['completion'] | null;
  setbackResponse: DailyWinFeedbackCreate['setback_response'] | null;
  academicResult: AcademicResult | null;
  correctCount: number | null;
  attemptedCount: number | null;
  whatHelped: string;
  additionalNote: string;
};

let draft: ReflectionDraft | null = null;

export function loadReflectionDraft(dailyWinId: string): ReflectionDraft | null {
  if (draft?.dailyWinId === dailyWinId) {
    return draft;
  }
  return null;
}

export function saveReflectionDraft(next: ReflectionDraft): void {
  draft = next;
}

export function clearReflectionDraft(dailyWinId?: string): void {
  if (dailyWinId === undefined || draft?.dailyWinId === dailyWinId) {
    draft = null;
  }
}
