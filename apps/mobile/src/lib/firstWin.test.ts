import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { GUIDE_SCREENS, readyBeforeGuide, visibleWaitMs } from './firstWin.ts';

describe('visibleWaitMs', () => {
  it('subtracts useful onboarding from Terra time', () => {
    assert.equal(visibleWaitMs(28300, 22100), 6200);
  });

  it('never goes negative', () => {
    assert.equal(visibleWaitMs(1000, 4000), 0);
  });

  it('stays unknown without model latency', () => {
    assert.equal(visibleWaitMs(null, 2000), null);
  });
});

describe('readyBeforeGuide', () => {
  it('is yes when Guide outlasts Terra', () => {
    assert.equal(readyBeforeGuide(10000, 20000), true);
  });

  it('is no when Terra outlasts Guide', () => {
    assert.equal(readyBeforeGuide(30000, 20000), false);
  });

  it('stays unknown without dwell time', () => {
    assert.equal(readyBeforeGuide(10000, null), null);
  });
});

describe('GUIDE_SCREENS', () => {
  it('is a short skippable intro, not padding', () => {
    assert.equal(GUIDE_SCREENS.length, 4);
    const blob = GUIDE_SCREENS.map((item) => `${item.title} ${item.body}`).join(' ');
    assert.match(blob, /plan/i);
    assert.match(blob, /rescue/i);
    assert.match(blob, /Ask before telling/i);
    assert.match(blob, /Hard is okay/i);
    assert.match(blob, /Support is always available/i);
    assert.match(blob, /actually happened/i);
  });
});
