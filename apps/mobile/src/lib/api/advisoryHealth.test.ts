import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  applyHealthToSession,
  appWaitsForHealth,
  advisoryStatusFromHealth,
  healthCanReplaceApp,
  homeLoadRetryMessage,
  homeSuccessRendersRegardlessOfHealth,
  initialAppShell,
} from './advisoryHealth.ts';
import { PARENT_ERRORS } from './parentErrors.ts';

describe('advisory health does not gate the app', () => {
  it('app renders normally before health completes', () => {
    assert.equal(initialAppShell(), 'router');
    assert.equal(appWaitsForHealth(), false);
    const before = applyHealthToSession(initialAppShell(), { pending: true });
    assert.equal(before.shell, 'router');
    assert.equal(before.indicator, 'Checking…');
  });

  it('health 200 -> dev indicator Connected', () => {
    assert.equal(advisoryStatusFromHealth({ ok: true }), 'connected');
    assert.equal(
      applyHealthToSession('router', { ok: true }).indicator,
      'Connected',
    );
  });

  it('health failure -> dev indicator Unavailable', () => {
    assert.equal(advisoryStatusFromHealth({ ok: false }), 'unavailable');
    assert.equal(
      applyHealthToSession('router', { ok: false }).indicator,
      'Unavailable',
    );
  });

  it('health timeout -> app still renders normally', () => {
    const timedOut = applyHealthToSession('router', { ok: false });
    assert.equal(timedOut.shell, 'router');
    assert.equal(healthCanReplaceApp(), false);
  });

  it('Home data success works regardless of health status', () => {
    assert.equal(homeSuccessRendersRegardlessOfHealth('checking'), true);
    assert.equal(homeSuccessRendersRegardlessOfHealth('connected'), true);
    assert.equal(homeSuccessRendersRegardlessOfHealth('unavailable'), true);
  });

  it('Home API failure uses the Home Retry UI', () => {
    assert.equal(homeLoadRetryMessage(), PARENT_ERRORS.load);
    assert.notEqual(homeLoadRetryMessage(), PARENT_ERRORS.unavailable);
  });

  it('later health failure cannot eject user from the app', () => {
    const afterSuccess = applyHealthToSession('router', { ok: true });
    const afterLaterFailure = applyHealthToSession(afterSuccess.shell, {
      ok: false,
    });
    assert.equal(afterLaterFailure.shell, 'router');
    assert.equal(afterLaterFailure.indicator, 'Unavailable');
    assert.equal(healthCanReplaceApp(), false);
  });

  it('health recovery updates indicator without navigation changes', () => {
    const unavailable = applyHealthToSession('router', { ok: false });
    const recovered = applyHealthToSession(unavailable.shell, { ok: true });
    assert.equal(unavailable.shell, recovered.shell);
    assert.equal(recovered.shell, 'router');
    assert.equal(recovered.indicator, 'Connected');
  });
});
