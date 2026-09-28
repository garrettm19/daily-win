export type ApiErrorKind =
  | 'unavailable'
  | 'timeout'
  | 'http'
  | 'demo_session';

export type ParentErrorContext =
  | 'load'
  | 'saveProfile'
  | 'saveReflection'
  | 'generate'
  | 'unavailable'
  | 'setup'
  | 'progress'
  | 'weekly';

export const DEMO_SESSION_ERROR_CODE = 'demo_session_unavailable';

export const PARENT_ERRORS = {
  load: "Couldn't load Daily Win. Try again.",
  saveProfile: "Couldn't save your changes. Nothing was lost.",
  saveReflection: "Couldn't save the reflection. Your answers are still here.",
  generate: "Couldn't prepare today's Win. Try again.",
  unavailable: "Can't reach Daily Win right now. Check the connection and try again.",
  unavailableHint: 'Check the connection, then try again.',
  setup: "Couldn't save your changes. Nothing was lost.",
  demoSession: "Couldn't start this demo session. Try again.",
  progress: "Couldn't load Progress. Your Daily Wins are safe.",
  weekly: "Couldn't load the Weekly Coach Report. Your Daily Wins are safe.",
} as const;

export const EMPTY_COPY = {
  progress:
    'Complete a Daily Win and a short reflection to start a picture of what works.',
  history: 'No Daily Wins yet. Start today’s Win from Home.',
  weekly: 'No completed Wins this week yet.',
} as const;

export function diagnosticLabel(kind: ApiErrorKind | null | undefined): string | null {
  if (kind === 'timeout') {
    return 'API timeout';
  }
  if (kind === 'unavailable') {
    return 'API unavailable';
  }
  return null;
}

export function isConnectivityKind(
  kind: ApiErrorKind | null | undefined,
): boolean {
  return kind === 'unavailable' || kind === 'timeout';
}

export function shouldMarkBackendUnavailable(
  kind: ApiErrorKind | null | undefined,
): boolean {
  return isConnectivityKind(kind);
}

export function parentMessage(
  context: ParentErrorContext,
  kind?: ApiErrorKind | null,
): string {
  if (kind === 'demo_session') {
    return PARENT_ERRORS.demoSession;
  }
  if (isConnectivityKind(kind) || context === 'unavailable') {
    return PARENT_ERRORS.unavailable;
  }
  return PARENT_ERRORS[context];
}

export function classifyFetchFailure(aborted: boolean): ApiErrorKind {
  return aborted ? 'timeout' : 'unavailable';
}

export function describeCaughtError(
  caught: unknown,
  fallbackMessage: string,
): {
  message: string;
  kind: ApiErrorKind | null;
  code: string | null;
} {
  if (
    caught instanceof Error &&
    'kind' in caught &&
    typeof (caught as { kind?: unknown }).kind === 'string'
  ) {
    const kind = (caught as { kind: ApiErrorKind }).kind;
    const code =
      'errorCode' in caught &&
      typeof (caught as { errorCode?: unknown }).errorCode === 'string'
        ? (caught as { errorCode: string }).errorCode
        : null;
    if (kind === 'demo_session') {
      return {
        message: PARENT_ERRORS.demoSession,
        kind,
        code: code ?? DEMO_SESSION_ERROR_CODE,
      };
    }
    if (
      kind === 'unavailable' ||
      kind === 'timeout' ||
      kind === 'http'
    ) {
      return { message: fallbackMessage, kind, code };
    }
  }
  return {
    message: fallbackMessage,
    kind: null,
    code: null,
  };
}

export function progressHasNoEvidence(progress: {
  recent_observations: readonly unknown[];
  goals: readonly { evidence_count: number }[];
  academic_skills?: readonly { session_count?: number }[];
}): boolean {
  const academicEmpty = (progress.academic_skills ?? []).every(
    (item) => (item.session_count ?? 0) === 0,
  );
  return (
    progress.recent_observations.length === 0 &&
    progress.goals.every((goal) => goal.evidence_count === 0) &&
    academicEmpty
  );
}
