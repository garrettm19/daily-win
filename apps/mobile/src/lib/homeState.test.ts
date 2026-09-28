import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  firstWinFailed,
  generationStageCopy,
  homeWinPhase,
  readyWinFromState,
  shouldPollPreparation,
} from './homeState.ts';
import type { NextWinState } from './api/types.ts';

describe('homeWinPhase', () => {
  it('prefers the unreflected READY Win', () => {
    assert.equal(
      homeWinPhase({ has_feedback: false }, 'generating'),
      'reflection_pending',
    );
  });

  it('shows preparing while next Win is generating', () => {
    assert.equal(homeWinPhase({ has_feedback: true }, 'generating'), 'preparing');
    assert.equal(homeWinPhase(null, 'generating'), 'preparing');
  });

  it('does not show an invalidated Win as ready', () => {
    assert.equal(homeWinPhase({ has_feedback: false }, 'invalidated'), 'failed');
    assert.equal(homeWinPhase(null, 'failed'), 'failed');
  });

  it('is first-ever when nothing is prepared', () => {
    assert.equal(homeWinPhase(null, 'not_started'), 'none');
  });
});

describe('generationStageCopy', () => {
  it('uses one calm parent line, not technical stages', () => {
    assert.equal(
      generationStageCopy('choosing_focus'),
      "Preparing today's challenge...",
    );
    assert.equal(
      generationStageCopy('building_challenge'),
      "Preparing today's challenge...",
    );
    assert.equal(generationStageCopy('mystery'), "Preparing today's challenge...");
  });
});

describe('readyWinFromState', () => {
  it('requires READY plus payload', () => {
    const ready: NextWinState = {
      daily_win: { has_feedback: false } as NextWinState['daily_win'],
      preparation_status: 'ready',
    };
    const generating: NextWinState = {
      daily_win: null,
      preparation_status: 'generating',
    };
    assert.equal(readyWinFromState(ready), true);
    assert.equal(readyWinFromState(generating), false);
  });
});

describe('shouldPollPreparation', () => {
  it('polls only while generating and stops otherwise', () => {
    assert.equal(shouldPollPreparation('generating'), true);
    assert.equal(shouldPollPreparation('ready'), false);
    assert.equal(shouldPollPreparation('failed'), false);
    assert.equal(shouldPollPreparation(null), false);
  });
});

describe('firstWinFailed', () => {
  it('uses first-Win failure copy, not returning-parent copy', () => {
    assert.equal(
      firstWinFailed(
        {
          daily_win: null,
          preparation_status: 'failed',
          trigger: 'first_profile_setup',
        },
        false,
      ),
      true,
    );
    assert.equal(
      firstWinFailed({ daily_win: null, preparation_status: 'failed', trigger: 'reflection' }, false),
      false,
    );
  });
});
