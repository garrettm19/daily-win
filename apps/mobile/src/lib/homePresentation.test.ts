import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  firstRunPrepFailed,
  homePresentationPhase,
  onePrimaryCtaLabel,
  shouldHoldPresentedWin,
} from './homePresentation.ts';

describe('shouldHoldPresentedWin', () => {
  it('holds a new READY Win while Home remains focused on another Win', () => {
    assert.equal(
      shouldHoldPresentedWin({
        presentedWinId: 'win-a',
        incomingWinId: 'win-b',
        screenHeld: true,
      }),
      true,
    );
  });

  it('does not hold on first presentation or after intentional re-entry', () => {
    assert.equal(
      shouldHoldPresentedWin({
        presentedWinId: null,
        incomingWinId: 'win-b',
        screenHeld: true,
      }),
      false,
    );
    assert.equal(
      shouldHoldPresentedWin({
        presentedWinId: 'win-a',
        incomingWinId: 'win-b',
        screenHeld: false,
      }),
      false,
    );
    assert.equal(
      shouldHoldPresentedWin({
        presentedWinId: 'win-b',
        incomingWinId: 'win-b',
        screenHeld: true,
      }),
      false,
    );
  });
});

describe('homePresentationPhase', () => {
  it('keeps current vs next vs historical distinct', () => {
    assert.equal(
      homePresentationPhase({
        presentedWin: { id: 'a', has_feedback: false },
        latestWin: { id: 'a', has_feedback: false },
        preparationStatus: 'ready',
        pendingReady: false,
      }),
      'current_unreflected',
    );
    assert.equal(
      homePresentationPhase({
        presentedWin: { id: 'a', has_feedback: true },
        latestWin: { id: 'b', has_feedback: false },
        preparationStatus: 'ready',
        pendingReady: true,
      }),
      'next_ready_pending_presentation',
    );
    assert.equal(
      homePresentationPhase({
        presentedWin: { id: 'a', has_feedback: true },
        latestWin: { id: 'a', has_feedback: true },
        preparationStatus: 'generating',
        pendingReady: false,
      }),
      'reflected_preparing_next',
    );
    assert.equal(
      homePresentationPhase({
        presentedWin: null,
        latestWin: null,
        preparationStatus: 'generating',
        pendingReady: false,
      }),
      'preparing_first',
    );
    assert.equal(
      homePresentationPhase({
        presentedWin: null,
        latestWin: null,
        preparationStatus: 'not_started',
        pendingReady: false,
      }),
      'first_run',
    );
  });

  it('exposes one primary CTA for actionable states', () => {
    assert.equal(onePrimaryCtaLabel('current_unreflected'), 'Start Daily Win');
    assert.equal(onePrimaryCtaLabel('next_ready_pending_presentation'), null);
    assert.equal(onePrimaryCtaLabel('reflected_preparing_next'), null);
    assert.equal(onePrimaryCtaLabel('prep_failed'), 'Try again');
  });
});

describe('firstRunPrepFailed', () => {
  it('uses first-Win failure only when nothing has been presented', () => {
    assert.equal(
      firstRunPrepFailed(
        { daily_win: null, preparation_status: 'failed', trigger: 'first_profile_setup' },
        null,
      ),
      true,
    );
  });
});
