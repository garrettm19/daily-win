import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  formatObservation,
  independenceTrendCopy,
  independencePoints,
  stageFromProgress,
  stageIndex,
  uniqueFormattedObservations,
} from './competency.ts';
import type { DemoAcademicProgress, DemoObservation } from './api/types.ts';

function skill(overrides: Partial<DemoAcademicProgress> = {}): DemoAcademicProgress {
  return {
    domain_label: 'Writing',
    skill_name: 'Spelling endings',
    state_label: 'Developing',
    recent_evidence: 'Completed with a little help.',
    evidence_label: '3 sessions',
    session_count: 3,
    supporting_copy: 'Daily Win is still gathering evidence.',
    band: 'developing',
    recent_checks: [
      { occurred_at: '2026-09-21T12:00:00Z', result: 'correct_independently' },
      { occurred_at: '2026-09-19T12:00:00Z', result: 'correct_after_light_prompt' },
      { occurred_at: '2026-09-17T12:00:00Z', result: 'correct_after_significant_help' },
    ],
    ...overrides,
  };
}

describe('competency stages', () => {
  it('maps not_observed through retained without showing a numeric score', () => {
    assert.equal(stageIndex('not_observed'), 0);
    assert.equal(stageIndex('retained'), 4);
    assert.equal(stageFromProgress(skill({ band: 'emerging', state_label: 'Emerging' })), 'emerging');
    assert.equal(
      stageFromProgress(skill({ band: undefined, state_label: 'Not enough evidence yet' })),
      'not_observed',
    );
  });
});

describe('independence trend', () => {
  it('plots discrete sessions oldest-first and uses allowed copy', () => {
    const points = independencePoints(skill());
    assert.deepEqual(points, ['significant_help', 'light_help', 'independent']);
    assert.equal(independenceTrendCopy(points), 'Needing less help recently');
    assert.equal(independenceTrendCopy(['independent', 'independent']), 'Independent in the last two checks');
    assert.equal(
      independenceTrendCopy(['independent', 'significant_help']),
      'Needed more support last session',
    );
    assert.equal(independenceTrendCopy(['light_help']), 'Still gathering evidence');
    assert.equal(independenceTrendCopy([]), 'Still gathering evidence');
  });

  it('handles sparse evidence without interpolating a curve', () => {
    const sparse = independencePoints(
      skill({
        recent_checks: [{ occurred_at: '2026-09-21T12:00:00Z', result: 'correct_independently' }],
      }),
    );
    assert.deepEqual(sparse, ['independent']);
    assert.equal(independenceTrendCopy(sparse), 'Still gathering evidence');
  });
});

describe('recent observation formatting', () => {
  it('formats supported values and hides junk', () => {
    const ok: DemoObservation = {
      goal_name: 'Persistence',
      summary: 'Returned after one prompt',
      source: 'From your reflection',
    };
    assert.deepEqual(formatObservation(ok), {
      goalName: 'Persistence',
      summary: 'Returned after one prompt',
    });
    assert.equal(
      formatObservation({ goal_name: 'Persistence', summary: 'correct_independently', source: 'x' }),
      null,
    );
    assert.equal(
      formatObservation({ goal_name: 'Goal', summary: 'Returned after one prompt', source: 'x' }),
      null,
    );
    assert.equal(
      formatObservation({ goal_name: 'Persistence', summary: '[object Object]', source: 'x' }),
      null,
    );
    assert.equal(formatObservation(null), null);
  });

  it('drops duplicates and keeps newest-first order of the input', () => {
    const items: DemoObservation[] = [
      { goal_name: 'Persistence', summary: 'Returned after one prompt', source: 'a' },
      { goal_name: 'Persistence', summary: 'Returned after one prompt', source: 'b' },
      { goal_name: 'Writing organization', summary: 'Returned to the challenge independently', source: 'c' },
    ];
    const unique = uniqueFormattedObservations(items);
    assert.equal(unique.length, 2);
    assert.equal(unique[0].goalName, 'Persistence');
    assert.equal(unique[1].goalName, 'Writing organization');
  });
});
