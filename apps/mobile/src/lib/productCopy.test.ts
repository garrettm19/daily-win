import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  containsGenericCoachLanguage,
  cuesForSegment,
  formatFriendlyDate,
  formatHistoryDate,
  formatWeekRange,
  goalPriorityLabel,
  longWinNeedsCollapse,
  materialsForDisplay,
  optionLabel,
  selectableOptionLabel,
  showDiscoveryCard,
  unlistedDoMaterials,
  visibleLines,
  weeklySparseNote,
} from './productCopy.ts';

describe('optionLabel', () => {
  it('uses parent phrasing for known values', () => {
    assert.equal(optionLabel('looked_automatic'), 'Looked automatic');
    assert.equal(optionLabel('worked_with_help'), 'Worked for it with help');
  });

  it('does not leave snake_case visible', () => {
    assert.equal(optionLabel('kept_trying'), 'Kept trying');
  });

  it('never uses a generated paragraph as a chip label', () => {
    assert.equal(selectableOptionLabel('self_corrected'), 'Self-corrected');
    assert.equal(
      selectableOptionLabel(
        'Can he spell jumped without a hint Independent no instructional help',
      ),
      null,
    );
  });
});

describe('goalPriorityLabel', () => {
  it('stays quiet for a single goal', () => {
    assert.equal(goalPriorityLabel(1, 1), 'Focus');
  });

  it('names rotation without scheduler jargon', () => {
    assert.equal(goalPriorityLabel(1, 3), '#1 Main focus');
    assert.equal(goalPriorityLabel(2, 3), '#2 Secondary focus');
    assert.equal(goalPriorityLabel(3, 3), '#3 Also in rotation');
  });
});

describe('dates', () => {
  const now = new Date(2026, 8, 21);

  it('uses Today and Yesterday', () => {
    assert.equal(formatFriendlyDate('2026-09-21T15:00:00', now), 'Today');
    assert.equal(formatFriendlyDate('2026-09-20T08:00:00', now), 'Yesterday');
    assert.match(formatFriendlyDate('2026-09-15', now), /Sep 15/);
  });

  it('formats historical dates without Today', () => {
    assert.match(formatHistoryDate('2026-09-21T15:00:00'), /Sep 21/);
    assert.doesNotMatch(formatHistoryDate('2026-09-21T15:00:00'), /Today/);
  });

  it('formats a covered week without ISO timestamps', () => {
    const range = formatWeekRange('2026-09-15', '2026-09-21');
    assert.match(range, /Sep 15/);
    assert.match(range, /Sep 21/);
    assert.doesNotMatch(range, /T/);
  });
});

describe('weekly sparse copy', () => {
  it('does not overclaim on 0–2 Wins', () => {
    assert.equal(
      weeklySparseNote(0),
      'Still gathering a picture this week.',
    );
    assert.match(weeklySparseNote(1) ?? '', /Only one Win/);
    assert.equal(weeklySparseNote(5), null);
  });
});

describe('presentation guardrails', () => {
  it('hides empty headings and caps lists', () => {
    assert.deepEqual(visibleLines(['  ', 'Let them try first', ''], 3), [
      'Let them try first',
    ]);
    assert.equal(visibleLines(['a', 'b', 'c', 'd'], 3).length, 3);
  });

  it('omits NONE materials and unused headers', () => {
    assert.deepEqual(
      materialsForDisplay(['NONE', 'PAPER', 'PENCIL'], {
        PAPER: 'Paper',
        PENCIL: 'Pencil',
      }),
      ['Paper', 'Pencil'],
    );
  });

  it('keeps coach cues sparse', () => {
    const cues = [
      { label: 'WAIT', text: 'Count to five.' },
      { label: 'WAIT', text: 'Count to five.' },
      { label: 'HINT', text: 'Ask what they notice.' },
    ];
    assert.equal(cuesForSegment(cues, 'LEARN').length, 1);
    assert.equal(cuesForSegment(cues, 'GROW').length, 0);
  });
});

describe('generic coach language', () => {
  it('flags abstract coach cards', () => {
    assert.equal(
      containsGenericCoachLanguage('Provide appropriate support.'),
      true,
    );
    assert.equal(
      containsGenericCoachLanguage('Let him try the first check alone.'),
      false,
    );
  });
});

describe('materials vs DO', () => {
  it('flags a DO object missing from materials', () => {
    assert.deepEqual(
      unlistedDoMaterials(['Get a timer and count to ten.'], ['PAPER']),
      ['TIMER'],
    );
    assert.deepEqual(
      unlistedDoMaterials(['Build a short block tower.'], ['BLOCKS']),
      [],
    );
  });
});

describe('long Win presentation', () => {
  it('marks very long step lists for collapse', () => {
    assert.equal(longWinNeedsCollapse(4), false);
    assert.equal(longWinNeedsCollapse(12), true);
  });
});

describe('discovery presentation', () => {
  it('hides discovery when there is nothing to rotate', () => {
    assert.equal(showDiscoveryCard({ active: true, domains: [{}] }), false);
    assert.equal(
      showDiscoveryCard({ active: true, domains: [{}, {}] }),
      true,
    );
    assert.equal(showDiscoveryCard({ active: false, domains: [{}, {}] }), false);
  });
});
