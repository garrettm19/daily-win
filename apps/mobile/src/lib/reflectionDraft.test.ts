import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  clearReflectionDraft,
  loadReflectionDraft,
  saveReflectionDraft,
  type ReflectionDraft,
} from './reflectionDraft.ts';

describe('reflection draft', () => {
  it('keeps answers after a failed submit', () => {
    const draft: ReflectionDraft = {
      dailyWinId: 'win-1',
      difficulty: 'about_right',
      engagement: 'high',
      completion: 'completed',
      setbackResponse: 'continued_after_prompt',
      academicResult: 'correct_independently',
      correctCount: null,
      attemptedCount: null,
      whatHelped: 'Waited.',
      additionalNote: '',
    };
    saveReflectionDraft(draft);
    assert.deepEqual(loadReflectionDraft('win-1'), draft);
    assert.equal(loadReflectionDraft('win-2'), null);
    clearReflectionDraft('win-1');
    assert.equal(loadReflectionDraft('win-1'), null);
  });
});
