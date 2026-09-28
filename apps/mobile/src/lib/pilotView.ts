export const PILOT_VIEW_STORAGE_KEY = 'daily_win_parent_pilot_view_v1';

export type PilotViewStore = {
  getItem: (key: string) => Promise<string | null>;
  setItem: (key: string, value: string) => Promise<void>;
};

let cached = false;
let injectedStore: PilotViewStore | null = null;
const listeners = new Set<() => void>();

function isDev(): boolean {
  if (typeof __DEV__ !== 'undefined' && __DEV__) {
    return true;
  }
  return (globalThis as { __DEV__?: boolean }).__DEV__ === true;
}

function notify(): void {
  for (const listener of listeners) {
    listener();
  }
}

export function isParentPilotView(): boolean {
  return isDev() && cached;
}

export function subscribePilotView(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function setPilotViewStore(store: PilotViewStore | null): void {
  injectedStore = store;
}

export const setPilotViewStoreForTests = setPilotViewStore;

export function resetPilotViewForTests(): void {
  cached = false;
  injectedStore = null;
}

export function setParentPilotView(enabled: boolean): void {
  cached = Boolean(enabled) && isDev();
  notify();
  const store = injectedStore;
  if (!store) {
    return;
  }
  void store.setItem(PILOT_VIEW_STORAGE_KEY, cached ? 'on' : 'off');
}

export async function hydratePilotView(store?: PilotViewStore): Promise<void> {
  const resolved = store ?? injectedStore;
  if (!resolved || !isDev()) {
    return;
  }
  try {
    const value = await resolved.getItem(PILOT_VIEW_STORAGE_KEY);
    cached = value === 'on';
    notify();
  } catch {
    cached = false;
    notify();
  }
}
