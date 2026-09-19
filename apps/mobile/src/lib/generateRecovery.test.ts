import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  recoveredUnreflectedWin,
  shouldAttemptGenerate,
  shouldReuseLatestInsteadOfGenerate,
} from './generateRecovery.ts';
import { clampText } from './textLimits.ts';

describe('generation recovery', () => {
  it('reuses an unreflected latest Win instead of generating', () => {
    const latest = { id: 'win-1', has_feedback: false };
    assert.equal(shouldReuseLatestInsteadOfGenerate(latest), true);
    assert.equal(shouldAttemptGenerate(latest), false);
  });

  it('generates only when there is no unreflected latest Win', () => {
    assert.equal(shouldAttemptGenerate(null), true);
    assert.equal(
      shouldAttemptGenerate({ id: 'win-2', has_feedback: true }),
      true,
    );
  });

  it('recovers a Win created after a lost generate response', () => {
    const recovered = { id: 'win-3', has_feedback: false };
    assert.equal(recoveredUnreflectedWin(recovered), true);
    assert.equal(recoveredUnreflectedWin({ id: 'win-4', has_feedback: true }), false);
    assert.equal(recoveredUnreflectedWin(null), false);
  });
});

describe('form text limits', () => {
  it('clamps pasted text so form values cannot bypass max length', () => {
    assert.equal(clampText('short', 40), 'short');
    assert.equal(clampText('abcdefghij', 4), 'abcd');
  });
});
