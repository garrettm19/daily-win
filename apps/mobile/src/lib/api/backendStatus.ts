export type BackendStatus = 'checking' | 'connected' | 'unavailable';

type Listener = (status: BackendStatus) => void;

let current: BackendStatus = 'checking';
const listeners = new Set<Listener>();

export function getBackendStatus(): BackendStatus {
  return current;
}

export function setBackendStatus(next: BackendStatus): void {
  if (current === next) {
    return;
  }
  current = next;
  for (const listener of listeners) {
    listener(current);
  }
}

export function subscribeBackendStatus(listener: Listener): () => void {
  listeners.add(listener);
  listener(current);
  return () => {
    listeners.delete(listener);
  };
}

export function backendStatusLabel(status: BackendStatus): string {
  if (status === 'checking') {
    return 'Checking…';
  }
  if (status === 'connected') {
    return 'Connected';
  }
  return 'Unavailable';
}
