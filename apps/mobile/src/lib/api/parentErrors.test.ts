import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  DEMO_SESSION_ERROR_CODE,
  EMPTY_COPY,
  PARENT_ERRORS,
  classifyFetchFailure,
  describeCaughtError,
  diagnosticLabel,
  isConnectivityKind,
  parentMessage,
  progressHasNoEvidence,
  shouldMarkBackendUnavailable,
} from './parentErrors.ts';
import { API_TIMEOUT_MS, timeoutForRequest } from './timeouts.ts';
import { backendStatusLabel } from './backendStatus.ts';

describe('parent-facing errors', () => {
  it('uses connectivity copy for timeouts and unavailable APIs', () => {
    assert.equal(parentMessage('load', 'timeout'), PARENT_ERRORS.unavailable);
    assert.equal(parentMessage('generate', 'unavailable'), PARENT_ERRORS.unavailable);
    assert.equal(parentMessage('saveReflection', 'http'), PARENT_ERRORS.saveReflection);
    assert.equal(parentMessage('saveProfile', 'http'), PARENT_ERRORS.saveProfile);
    assert.equal(parentMessage('load', 'http'), PARENT_ERRORS.load);
    assert.equal(parentMessage('load', 'demo_session'), PARENT_ERRORS.demoSession);
  });

  it('keeps diagnostics sanitized', () => {
    assert.equal(diagnosticLabel('timeout'), 'API timeout');
    assert.equal(diagnosticLabel('unavailable'), 'API unavailable');
    assert.equal(diagnosticLabel('http'), null);
    assert.equal(diagnosticLabel('demo_session'), null);
    assert.equal(isConnectivityKind('timeout'), true);
    assert.equal(classifyFetchFailure(true), 'timeout');
    assert.equal(classifyFetchFailure(false), 'unavailable');
  });

  it('detects empty progress evidence', () => {
    assert.equal(
      progressHasNoEvidence({ recent_observations: [], goals: [{ evidence_count: 0 }] }),
      true,
    );
    assert.equal(
      progressHasNoEvidence({
        recent_observations: [{ summary: 'tried again' }],
        goals: [{ evidence_count: 0 }],
      }),
      false,
    );
    assert.equal(
      progressHasNoEvidence({
        recent_observations: [],
        goals: [{ evidence_count: 0 }],
        academic_skills: [{ session_count: 1 }],
      }),
      false,
    );
    assert.equal(parentMessage('progress', 'http'), PARENT_ERRORS.progress);
    assert.equal(parentMessage('weekly', 'http'), PARENT_ERRORS.weekly);
    assert.equal(EMPTY_COPY.history, 'No Daily Wins yet. Start today’s Win from Home.');
  });
});

describe('timeouts', () => {
  it('uses shorter reads and a longer generation window', () => {
    assert.equal(timeoutForRequest('GET', '/health'), API_TIMEOUT_MS.health);
    assert.equal(timeoutForRequest('GET', '/api/v1/demo/session'), API_TIMEOUT_MS.read);
    assert.equal(timeoutForRequest('POST', '/api/v1/demo/profile'), API_TIMEOUT_MS.mutate);
    assert.equal(
      timeoutForRequest('POST', '/api/v1/demo/daily-wins/generate'),
      API_TIMEOUT_MS.generate,
    );
    assert.ok(API_TIMEOUT_MS.read <= 15_000);
    assert.ok(API_TIMEOUT_MS.mutate <= 20_000);
    assert.ok(API_TIMEOUT_MS.generate >= 60_000);
    assert.ok(API_TIMEOUT_MS.generate <= 90_000);
  });
});

describe('backend status label', () => {
  it('never exposes connection details', () => {
    assert.equal(backendStatusLabel('connected'), 'Connected');
    assert.equal(backendStatusLabel('unavailable'), 'Unavailable');
    assert.equal(backendStatusLabel('checking'), 'Checking…');
  });
});

describe('demo session error classification', () => {
  it('does not label a session failure as API unavailable', () => {
    class SessionApiError extends Error {
      kind = 'demo_session' as const;
      errorCode = DEMO_SESSION_ERROR_CODE;
    }
    const described = describeCaughtError(
      new SessionApiError(),
      PARENT_ERRORS.load,
    );
    assert.equal(described.message, PARENT_ERRORS.demoSession);
    assert.equal(described.kind, 'demo_session');
    assert.equal(described.code, DEMO_SESSION_ERROR_CODE);
    assert.equal(diagnosticLabel(described.kind), null);
    assert.notEqual(described.message, PARENT_ERRORS.unavailable);
  });

  it('keeps health connected when session initialization fails', () => {
    assert.equal(shouldMarkBackendUnavailable('demo_session'), false);
    assert.equal(shouldMarkBackendUnavailable('http'), false);
    assert.equal(shouldMarkBackendUnavailable('unavailable'), true);
    assert.equal(shouldMarkBackendUnavailable('timeout'), true);
  });

  it('does not treat unknown errors as a network outage', () => {
    const described = describeCaughtError(
      new Error('keychain'),
      PARENT_ERRORS.load,
    );
    assert.equal(described.kind, null);
    assert.equal(diagnosticLabel(described.kind), null);
  });
});

describe('production copy audit', () => {
  const RAW_CODES = [
    'configuration_error',
    'provider_error',
    'unsafe_content',
    'renderer_contract_failed',
    'instruction_plan_mismatch',
    'feedback_required',
    'generation_in_progress',
  ];
  const SKIP = new Set(['learning-qa.tsx', 'test-feedback.tsx']);

  it('does not leak raw error codes on parent screens', () => {
    const appDir = join(dirname(fileURLToPath(import.meta.url)), '../../app');
    const files = readdirSync(appDir).filter(
      (name) => name.endsWith('.tsx') && !SKIP.has(name),
    );
    for (const name of files) {
      const text = readFileSync(join(appDir, name), 'utf8');
      for (const code of RAW_CODES) {
        if (name === 'index.tsx' && code === 'generation_in_progress') {
          continue;
        }
        if (name === 'index.tsx' && code === 'feedback_required') {
          continue;
        }
        assert.equal(
          text.includes(`'${code}'`) || text.includes(`"${code}"`),
          false,
          `${name} displayed ${code}`,
        );
      }
    }
    const parentCopy = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), 'parentErrors.ts'),
      'utf8',
    );
    for (const code of RAW_CODES) {
      assert.equal(parentCopy.includes(code), false, `parentErrors leaked ${code}`);
    }
  });
});
