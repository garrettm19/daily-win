import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  ACADEMIC_RESULT_OPTIONS,
  SUPPORT_CAPTION,
  asksAboutSetback,
  asksEngagementQuestion,
  asksForCounts,
  changedTodayCopy,
  checkCaption,
  countsAreValid,
  hasAcademicProbe,
  isCanonicalCheckLabel,
} from './academicLoop.ts';
import type { DemoDailyWin } from './api/types.ts';

function win(overrides: Partial<DemoDailyWin> = {}): DemoDailyWin {
  return {
    id: 'win-1',
    child_nickname: 'Hayes',
    title: 'A Daily Win',
    objective: 'Practice',
    duration_minutes: 20,
    primary_skill_code: 'writing.sentences.complete_sentence',
    primary_skill_display_name: 'Complete sentence',
    has_feedback: false,
    created_at: '2026-09-19T00:00:00Z',
    content: {
      title: 'A Daily Win',
      objective: 'Practice',
      duration_minutes: 20,
      primary_skill_code: 'writing.sentences.complete_sentence',
      supporting_skill_codes: [],
      personalization_summary: 'Theme',
      materials: ['PAPER'],
      parent_briefing: {
        purpose: 'p',
        how_to_coach: 'c',
        watch_for: 'w',
        avoid: 'a',
      },
      segments: [],
      adaptations: { if_too_easy: 'e', if_too_hard: 'h' },
      success_checks: ['ok'],
      observation_focus: 'watch',
      safety_flags: [],
    },
    ...overrides,
  };
}

describe('academic reflection mapping', () => {
  it('maps parent labels to backend academic_result values exactly', () => {
    assert.deepEqual(
      ACADEMIC_RESULT_OPTIONS.map((item) => item.value),
      [
        'correct_independently',
        'correct_after_light_prompt',
        'correct_after_significant_help',
        'incorrect',
        'not_attempted',
      ],
    );
    assert.equal(
      ACADEMIC_RESULT_OPTIONS.find((item) => item.value === 'correct_independently')
        ?.label,
      'Did it independently',
    );
    assert.match(SUPPORT_CAPTION, /no help on the check/);
    assert.match(SUPPORT_CAPTION, /one short cue/);
    for (const option of ACADEMIC_RESULT_OPTIONS) {
      assert.equal(isCanonicalCheckLabel(option.label), true);
      assert.doesNotMatch(option.label, /\n/);
      assert.ok(option.label.length < 42);
    }
    assert.equal(
      checkCaption({
        prompt_label: 'Can he spell jumped without a hint Independent no help',
        support_caption:
          'Independent: no instructional help on this part. Light prompt: one short cue.',
        what_to_check: 'Can he spell jumped without a hint?',
        success_looks_like: 'The ending is -ed.',
        asks_for_counts: false,
      }),
      SUPPORT_CAPTION,
    );
    assert.doesNotMatch(
      checkCaption({
        prompt_label: 'Can he spell jumped without a hint Independent no help',
        support_caption: 'Independent: no instructional help.',
        what_to_check: 'x',
        success_looks_like: 'y',
        asks_for_counts: false,
      }),
      /Independent: no instructional help/,
    );
  });

  it('shows the academic section only when a probe exists', () => {
    assert.equal(hasAcademicProbe(win()), false);
    assert.equal(
      hasAcademicProbe(
        win({
          assessment: {
            what_to_check: 'Can Hayes say one complete sentence?',
            success_looks_like: 'The sentence has a who/what and an action.',
            prompt_label: 'Say or write one complete sentence',
            asks_for_counts: false,
          },
        }),
      ),
      true,
    );
  });

  it('asks for counts only when the probe says so', () => {
    assert.equal(asksForCounts(win()), false);
    assert.equal(
      asksForCounts(
        win({
          assessment: {
            what_to_check: 'Can Hayes add within 10?',
            success_looks_like: 'Correct sum.',
            prompt_label: 'Solve one addition fact',
            asks_for_counts: true,
          },
        }),
      ),
      true,
    );
  });

  it('validates count pairs', () => {
    assert.equal(countsAreValid(null, null), true);
    assert.equal(countsAreValid(3, 4), true);
    assert.equal(countsAreValid(0, 0), true);
    assert.equal(countsAreValid(4, 3), false);
    assert.equal(countsAreValid(2, null), false);
  });

  it('asks engagement only when difficulty is off or a bonus exists', () => {
    assert.equal(asksEngagementQuestion('about_right', false), false);
    assert.equal(asksEngagementQuestion('too_hard', false), true);
    assert.equal(asksEngagementQuestion('about_right', true), true);
  });

  it('omits setback unless the win asks for it, and prefers planner change copy', () => {
    assert.equal(asksAboutSetback(win()), true);
    assert.equal(asksAboutSetback(win({ asks_about_setback: false })), false);
    const planned = win({
      what_changed_today: "We're practicing sequencing again, but with less help.",
      content: {
        ...win().content,
        adaptation_summary: 'Generic LLM summary',
      },
    });
    assert.equal(
      changedTodayCopy(planned),
      "We're practicing sequencing again, but with less help.",
    );
  });
});
