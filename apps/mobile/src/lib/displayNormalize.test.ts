import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  SELECTABLE_LABEL_MAX,
  isSelectableLabel,
  joinDisplayFragments,
  looksLikeParagraph,
  looksLikeRawEnum,
  normalizeDisplayText,
} from './displayNormalize.ts';

describe('normalizeDisplayText', () => {
  it('collapses whitespace and line breaks', () => {
    assert.equal(normalizeDisplayText('  Can he  spell\njumped  '), 'Can he spell jumped');
  });

  it('removes duplicate punctuation and space before marks', () => {
    assert.equal(normalizeDisplayText('Ready now .  Go!!'), 'Ready now. Go!');
  });

  it('does not invent copy', () => {
    assert.equal(normalizeDisplayText(''), '');
    assert.equal(normalizeDisplayText(null), '');
  });
});

describe('joinDisplayFragments', () => {
  it('joins structured fragments with punctuation cleanup', () => {
    assert.equal(
      joinDisplayFragments(['Spell jumped', 'Watch the ending.']),
      'Spell jumped Watch the ending.',
    );
  });
});

describe('isSelectableLabel', () => {
  it('accepts canonical check labels', () => {
    for (const label of [
      'Did it independently',
      'Did it with a little help',
      'Needed a lot of help',
      "Didn't get it yet",
      "Didn't try this part",
    ]) {
      assert.equal(isSelectableLabel(label), true, label);
    }
  });

  it('rejects newlines, run-ons, and long generated paragraphs', () => {
    assert.equal(isSelectableLabel('Did it\nindependently'), false);
    assert.equal(
      isSelectableLabel(
        'Can he spell jumped without a hint Independent: no instructional help on this part.',
      ),
      false,
    );
    assert.equal(isSelectableLabel('A'.repeat(SELECTABLE_LABEL_MAX + 1)), false);
  });
});

describe('looksLikeParagraph / raw enum', () => {
  it('detects concatenated sentences and snake_case', () => {
    assert.equal(looksLikeParagraph('One sentence. Two sentences.'), true);
    assert.equal(looksLikeRawEnum('correct_independently'), true);
    assert.equal(looksLikeRawEnum('[object Object]'), true);
    assert.equal(looksLikeRawEnum('undefined'), true);
    assert.equal(looksLikeRawEnum('Independent once'), false);
  });
});
