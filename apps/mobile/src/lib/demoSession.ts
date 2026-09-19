export const DEMO_SESSION_STORAGE_KEY = 'daily_win_demo_session_v1';
export const DEMO_SESSION_MIN_LENGTH = 32;
export const DEMO_SESSION_ERROR_CODE = 'demo_session_unavailable';

export type DemoSessionStore = {
  getItem: (key: string) => Promise<string | null>;
  setItem: (key: string, value: string) => Promise<void>;
};

export class DemoSessionError extends Error {
  readonly errorCode = DEMO_SESSION_ERROR_CODE;

  constructor(message = "Couldn't start this demo session. Try again.") {
    super(message);
    this.name = 'DemoSessionError';
  }
}

type ResolvedDemoSession = {
  secret: string;
  testerFingerprint: string;
};

let cachedSession: ResolvedDemoSession | null = null;
let inflight: Promise<string> | null = null;
let injectedStore: DemoSessionStore | null = null;
const fingerprintListeners = new Set<() => void>();

function isDev(): boolean {
  if (typeof __DEV__ !== 'undefined' && __DEV__) {
    return true;
  }
  return (globalThis as { __DEV__?: boolean }).__DEV__ === true;
}

function isReactNativeRuntime(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    (navigator as { product?: string }).product === 'ReactNative'
  );
}

function isWebRuntime(): boolean {
  return typeof window !== 'undefined' && !isReactNativeRuntime();
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function isValidSecret(value: string | null | undefined): value is string {
  return typeof value === 'string' && value.length >= DEMO_SESSION_MIN_LENGTH;
}

function safeFailureText(error: unknown): string {
  const name = error instanceof Error ? error.name : 'Error';
  let message = error instanceof Error ? error.message : String(error);
  const secret = cachedSession?.secret;
  if (secret && message.includes(secret)) {
    message = message.split(secret).join('[redacted]');
  }
  return `${name}: ${message}`;
}

function logDev(message: string): void {
  if (!isDev()) {
    return;
  }
  console.log(`[DailyWin Dev] ${message}`);
}

function logSessionFailure(error: unknown): void {
  logDev(`demo session failure: ${safeFailureText(error)}`);
}

function notifyFingerprintListeners(): void {
  for (const listener of fingerprintListeners) {
    listener();
  }
}

function webDevStorage(): Storage | null {
  if (!isWebRuntime()) {
    return null;
  }
  try {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    return localStorage;
  } catch {
    return null;
  }
}

async function secureRandomBytes(byteCount: number): Promise<Uint8Array> {
  try {
    const Crypto = await import('expo-crypto');
    return await Crypto.getRandomBytesAsync(byteCount);
  } catch (error) {
    if (isReactNativeRuntime()) {
      logSessionFailure(error);
      throw new DemoSessionError('Secure random generator is unavailable');
    }
    const cryptoApi = globalThis.crypto;
    if (cryptoApi && typeof cryptoApi.getRandomValues === 'function') {
      const bytes = new Uint8Array(byteCount);
      cryptoApi.getRandomValues(bytes);
      return bytes;
    }
    throw new DemoSessionError('Secure random generator is unavailable');
  }
}

async function randomSecret(): Promise<string> {
  const bytes = await secureRandomBytes(32);
  return bytesToHex(bytes);
}

async function sha256Hex(value: string): Promise<string> {
  try {
    const Crypto = await import('expo-crypto');
    return await Crypto.digestStringAsync(
      Crypto.CryptoDigestAlgorithm.SHA256,
      value,
    );
  } catch (error) {
    if (isReactNativeRuntime()) {
      logSessionFailure(error);
      throw new DemoSessionError('SHA-256 is unavailable');
    }
    const cryptoApi = globalThis.crypto;
    if (cryptoApi?.subtle?.digest) {
      const digest = await cryptoApi.subtle.digest(
        'SHA-256',
        new TextEncoder().encode(value),
      );
      return bytesToHex(new Uint8Array(digest));
    }
    throw new DemoSessionError('SHA-256 is unavailable');
  }
}

export function testerFingerprintFromHash(sessionHash: string): string {
  return sessionHash.slice(0, 6).toUpperCase();
}

export async function testerFingerprintFromSecret(secret: string): Promise<string> {
  const sessionHash = await sha256Hex(secret);
  return testerFingerprintFromHash(sessionHash);
}

export function formatTesterLabel(
  fingerprint: string | null | undefined,
): string | null {
  if (!fingerprint) {
    return null;
  }
  return `Tester: ${fingerprint}`;
}

export function getCachedTesterFingerprint(): string | null {
  return cachedSession?.testerFingerprint ?? null;
}

export function subscribeTesterFingerprint(listener: () => void): () => void {
  fingerprintListeners.add(listener);
  return () => {
    fingerprintListeners.delete(listener);
  };
}

export function setDemoSessionStoreForTests(store: DemoSessionStore | null): void {
  injectedStore = store;
}

export function resetDemoSessionForTests(): void {
  cachedSession = null;
  inflight = null;
  injectedStore = null;
}

export function peekDemoSessionInflightForTests(): Promise<string> | null {
  return inflight;
}

function toDemoSessionError(error: unknown): DemoSessionError {
  if (error instanceof DemoSessionError) {
    return error;
  }
  return new DemoSessionError();
}

async function loadSecureStore(): Promise<typeof import('expo-secure-store')> {
  return import('expo-secure-store');
}

async function readPersistedSecret(): Promise<string | null> {
  if (injectedStore) {
    return injectedStore.getItem(DEMO_SESSION_STORAGE_KEY);
  }
  const web = webDevStorage();
  if (web) {
    return web.getItem(DEMO_SESSION_STORAGE_KEY);
  }
  const SecureStore = await loadSecureStore();
  return SecureStore.getItemAsync(DEMO_SESSION_STORAGE_KEY);
}

async function writePersistedSecret(secret: string): Promise<void> {
  if (injectedStore) {
    await injectedStore.setItem(DEMO_SESSION_STORAGE_KEY, secret);
    return;
  }
  const web = webDevStorage();
  if (web) {
    web.setItem(DEMO_SESSION_STORAGE_KEY, secret);
    return;
  }
  const SecureStore = await loadSecureStore();
  await SecureStore.setItemAsync(DEMO_SESSION_STORAGE_KEY, secret);
}

async function rememberSession(
  secret: string,
  origin: 'existing' | 'created',
): Promise<string> {
  const testerFingerprint = await testerFingerprintFromSecret(secret);
  cachedSession = { secret, testerFingerprint };
  notifyFingerprintListeners();
  logDev(`demo session: ${origin}`);
  logDev(`tester fingerprint: ${testerFingerprint}`);
  return secret;
}

async function initializeDemoSession(): Promise<string> {
  logDev('demo session: initializing');
  try {
    const stored = await readPersistedSecret();
    if (isValidSecret(stored)) {
      return rememberSession(stored, 'existing');
    }
    const secret = await randomSecret();
    await writePersistedSecret(secret);
    return rememberSession(secret, 'created');
  } catch (error) {
    logSessionFailure(error);
    cachedSession = null;
    notifyFingerprintListeners();
    throw toDemoSessionError(error);
  }
}

export function getDemoSession(): Promise<string> {
  if (cachedSession && isValidSecret(cachedSession.secret)) {
    return Promise.resolve(cachedSession.secret);
  }
  if (!inflight) {
    inflight = initializeDemoSession().finally(() => {
      inflight = null;
    });
  }
  return inflight;
}

export async function requireDemoSession(): Promise<string> {
  const session = await getDemoSession();
  if (!isValidSecret(session)) {
    throw new DemoSessionError('Demo session is empty');
  }
  return session;
}

export async function attachDemoSessionHeader(
  headers: Record<string, string>,
): Promise<Record<string, string>> {
  headers['X-Demo-Session'] = await requireDemoSession();
  return headers;
}
