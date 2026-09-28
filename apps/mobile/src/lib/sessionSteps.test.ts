import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { buildSessionSteps, historicalLabels, stepperIndex } from './sessionSteps.ts';
import type { DemoDailyWin } from './api/types.ts';

function win(overrides: Partial<DemoDailyWin> = {}): DemoDailyWin {
  return {
    id: 'win-1',
    child_nickname: 'Hayes',
    title: 'Jumping endings',
    objective: 'Practice ed endings',
    duration_minutes: 20,
    primary_skill_code: 'writing.spelling.inflected_endings',
    primary_skill_display_name: 'Spelling endings',
    has_feedback: false,
    created_at: '2026-09-21T12:00:00Z',
    content: {
      title: 'Jumping endings',
      objective: 'Practice ed endings',
      duration_minutes: 20,
      primary_skill_code: 'writing.spelling.inflected_endings',
      supporting_skill_codes: [],
      personalization_summary: 'Theme',
      materials: ['PAPER'],
      parent_briefing: {
        purpose: 'p',
        how_to_coach: 'c',
        watch_for: 'w',
        avoid: 'a',
      },
      segments: [
        { type: 'LEARN', title: 'Notice the ending', minutes: 5, steps: ['Look at jumped.'], parent_role: '' },
        { type: 'DO', title: 'Try one', minutes: 8, steps: ['Spell jumped.'], parent_role: '' },
        { type: 'GROW', title: 'Celebrate', minutes: 3, steps: ['Name what worked.'], parent_role: '' },
      ],
      adaptations: { if_too_easy: 'e', if_too_hard: 'h' },
      success_checks: ['ok'],
      observation_focus: 'watch',
      safety_flags: [],
    },
    assessment: {
      what_to_check: 'Can he spell jumped without a hint?',
      success_looks_like: 'The ending is -ed.',
      prompt_label: 'Spell jumped',
      asks_for_counts: false,
    },
    ...overrides,
  };
}

describe('session stepper', () => {
  it('builds Mission → Learn → Do → Grow → Result and tracks the active step', () => {
    const steps = buildSessionSteps(win());
    assert.deepEqual(
      steps.map((item) => item.kind),
      ['mission', 'learn', 'do', 'grow', 'reflect'],
    );
    assert.equal(stepperIndex(steps, 'learn'), 0);
    assert.equal(stepperIndex(steps, 'do'), 1);
    assert.equal(stepperIndex(steps, 'grow'), 2);
  });

  it('omits empty GROW, bonus when missing, and Result when already reflected', () => {
    const historical = buildSessionSteps(
      win({
        has_feedback: true,
        bonus_challenge: undefined,
        content: {
          ...win().content,
          segments: [
            { type: 'LEARN', title: 'Notice', minutes: 5, steps: ['Look.'], parent_role: '' },
            { type: 'DO', title: 'Try', minutes: 8, steps: ['Spell.'], parent_role: '' },
            { type: 'GROW', title: '', minutes: 3, steps: [], parent_role: '' },
          ],
        },
      }),
    );
    assert.deepEqual(
      historical.map((item) => item.kind),
      ['mission', 'learn', 'do'],
    );
  });

  it('includes bonus only when a prompt exists', () => {
    const withBonus = buildSessionSteps(
      win({
        bonus_challenge: {
          code: 'b',
          category: 'fun',
          title: 'One more',
          minutes: 3,
          prompt: 'Try a harder word.',
          safety: '',
          personal_best: false,
        },
      }),
    );
    assert.equal(withBonus.some((item) => item.kind === 'bonus'), true);
  });
});

describe('historical labels', () => {
  it('flags Today’s Win / Today’s Focus so detail views can forbid them', () => {
    assert.equal(historicalLabels("Today's Win"), true);
    assert.equal(historicalLabels('Today’s Focus'), true);
    assert.equal(historicalLabels('Jumping endings'), false);
  });
});
