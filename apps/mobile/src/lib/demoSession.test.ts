import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { afterEach, describe, it } from 'node:test';

import {
  DEMO_SESSION_ERROR_CODE,
  PARENT_ERRORS,
  describeCaughtError,
  diagnosticLabel,
} from './api/parentErrors.ts';
import {
  DemoSessionError,
  attachDemoSessionHeader,
  formatTesterLabel,
  getCachedTesterFingerprint,
  getDemoSession,
  peekDemoSessionInflightForTests,
  requireDemoSession,
  resetDemoSessionForTests,
  setDemoSessionStoreForTests,
  testerFingerprintFromSecret,
  type DemoSessionStore,
} from './demoSession.ts';

afterEach(() => {
  resetDemoSessionForTests();
  delete (globalThis as { __DEV__?: boolean }).__DEV__;
});

function memoryStore(initial: string | null = null): DemoSessionStore & {
  writes: string[];
  reads: number;
} {
  let value = initial;
  const writes: string[] = [];
  return {
    writes,
    get reads() {
      return this._reads;
    },
    _reads: 0,
    async getItem() {
      this._reads += 1;
      return value;
    },
    async setItem(_key: string, next: string) {
      writes.push(next);
      value = next;
    },
  } as DemoSessionStore & { writes: string[]; reads: number; _reads: number };
}

function expectedFingerprint(secret: string): string {
  return createHash('sha256').update(secret).digest('hex').slice(0, 6).toUpperCase();
}

describe('demo session initialization', () => {
  it('creates one session when none is stored', async () => {
    const store = memoryStore(null);
    setDemoSessionStoreForTests(store);
    const secret = await getDemoSession();
    assert.match(secret, /^[0-9a-f]{64}$/);
    assert.equal(store.writes.length, 1);
    assert.equal(store.writes[0], secret);
    assert.equal(await getDemoSession(), secret);
    assert.equal(store.writes.length, 1);
  });

  it('reuses a stored session', async () => {
    const stored = 'a'.repeat(64);
    const store = memoryStore(stored);
    setDemoSessionStoreForTests(store);
    assert.equal(await getDemoSession(), stored);
    assert.equal(await getDemoSession(), stored);
    assert.equal(store.writes.length, 0);
  });

  it('shares one initialization promise across concurrent startup calls', async () => {
    let resolveRead: ((value: string | null) => void) | undefined;
    let reads = 0;
    const writes: string[] = [];
    setDemoSessionStoreForTests({
      getItem: async () => {
        reads += 1;
        return new Promise((resolve) => {
          resolveRead = resolve;
        });
      },
      setItem: async (_key, value) => {
        writes.push(value);
      },
    });

    const first = getDemoSession();
    const second = getDemoSession();
    const home = requireDemoSession();
    const reset = requireDemoSession();
    assert.equal(first, second);
    assert.equal(peekDemoSessionInflightForTests(), first);
    assert.ok(resolveRead);
    resolveRead!(null);

    const [created, again, homeSession, resetSession] = await Promise.all([
      first,
      second,
      home,
      reset,
    ]);
    assert.equal(created, again);
    assert.equal(homeSession, created);
    assert.equal(resetSession, created);
    assert.equal(reads, 1);
    assert.equal(writes.length, 1);
    assert.equal(writes[0], created);
  });

  it('waits for the session before attaching a demo request header', async () => {
    const stored = 'b'.repeat(64);
    let resolveRead: ((value: string | null) => void) | undefined;
    setDemoSessionStoreForTests({
      getItem: async () =>
        new Promise((resolve) => {
          resolveRead = resolve;
        }),
      setItem: async () => {
        throw new Error('should reuse stored session');
      },
    });

    const headers: Record<string, string> = {};
    const pending = attachDemoSessionHeader(headers);
    let settled = false;
    void pending.then(() => {
      settled = true;
    });
    await Promise.resolve();
    assert.equal(settled, false);
    assert.equal(headers['X-Demo-Session'], undefined);
    resolveRead!(stored);
    await pending;
    assert.equal(headers['X-Demo-Session'], stored);
    assert.notEqual(headers['X-Demo-Session'], '');
  });

  it('always attaches a non-empty X-Demo-Session header', async () => {
    setDemoSessionStoreForTests(memoryStore(null));
    const headers = await attachDemoSessionHeader({});
    assert.ok(headers['X-Demo-Session']);
    assert.ok(headers['X-Demo-Session'].length >= 32);
  });

  it('classifies SecureStore failure as demo_session_unavailable', async () => {
    setDemoSessionStoreForTests({
      getItem: async () => {
        throw new Error('Keychain is locked');
      },
      setItem: async () => undefined,
    });
    await assert.rejects(
      () => getDemoSession(),
      (error: unknown) => {
        assert.ok(error instanceof DemoSessionError);
        assert.equal(error.errorCode, DEMO_SESSION_ERROR_CODE);
        assert.equal(error.message, PARENT_ERRORS.demoSession);
        const described = describeCaughtError(
          Object.assign(new Error(error.message), {
            kind: 'demo_session',
            errorCode: error.errorCode,
          }),
          PARENT_ERRORS.load,
        );
        assert.equal(described.message, PARENT_ERRORS.demoSession);
        assert.notEqual(diagnosticLabel(described.kind), 'API unavailable');
        return true;
      },
    );
  });

  it('shows a tester fingerprint once a session exists', async () => {
    const stored = 'c'.repeat(64);
    setDemoSessionStoreForTests(memoryStore(stored));
    const secret = await getDemoSession();
    const fingerprint = await testerFingerprintFromSecret(secret);
    assert.equal(fingerprint, expectedFingerprint(secret));
    assert.equal(getCachedTesterFingerprint(), fingerprint);
    assert.equal(formatTesterLabel(fingerprint), `Tester: ${fingerprint}`);
    assert.match(fingerprint, /^[A-F0-9]{6}$/);
  });

  it('never logs the session secret', async () => {
    (globalThis as { __DEV__?: boolean }).__DEV__ = true;
    const stored = `secret-value-${'d'.repeat(48)}`;
    setDemoSessionStoreForTests(memoryStore(stored));
    const lines: string[] = [];
    const originalLog = console.log;
    console.log = (...args: unknown[]) => {
      lines.push(args.map(String).join(' '));
    };
    try {
      const secret = await getDemoSession();
      const fingerprint = getCachedTesterFingerprint();
      await attachDemoSessionHeader({});
      const joined = lines.join('\n');
      assert.match(joined, /demo session: existing/);
      assert.match(joined, /tester fingerprint: /);
      assert.ok(fingerprint);
      assert.match(joined, new RegExp(`tester fingerprint: ${fingerprint}`));
      assert.equal(joined.includes(secret), false);
      assert.equal(joined.includes(stored), false);
    } finally {
      console.log = originalLog;
    }
  });
});
