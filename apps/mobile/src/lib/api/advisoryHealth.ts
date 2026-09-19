export type AppShell = 'router';

export type AdvisoryBackendStatus = 'checking' | 'connected' | 'unavailable';

export function initialAppShell(): AppShell {
  return 'router';
}

export function appWaitsForHealth(): boolean {
  return false;
}

export function healthCanReplaceApp(): boolean {
  return false;
}

export function advisoryStatusFromHealth(result: {
  pending?: boolean;
  ok?: boolean;
}): AdvisoryBackendStatus {
  if (result.pending) {
    return 'checking';
  }
  return result.ok ? 'connected' : 'unavailable';
}

export function advisoryIndicatorLabel(status: AdvisoryBackendStatus): string {
  if (status === 'checking') {
    return 'Checking…';
  }
  if (status === 'connected') {
    return 'Connected';
  }
  return 'Unavailable';
}

export function applyHealthToSession(
  shell: AppShell,
  health: { pending?: boolean; ok?: boolean },
): { shell: AppShell; indicator: string } {
  return {
    shell,
    indicator: advisoryIndicatorLabel(advisoryStatusFromHealth(health)),
  };
}

export function homeLoadRetryMessage(): string {
  return "Couldn't load Daily Win. Try again.";
}

export function homeSuccessRendersRegardlessOfHealth(
  _health: AdvisoryBackendStatus,
): boolean {
  return true;
}
