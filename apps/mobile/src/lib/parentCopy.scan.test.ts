import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');

const PRODUCTION_SCREENS = [
  'src/app/index.tsx',
  'src/app/daily-win.tsx',
  'src/app/reflect.tsx',
  'src/app/insight.tsx',
  'src/app/progress.tsx',
  'src/app/weekly-report.tsx',
  'src/app/history.tsx',
  'src/app/guide.tsx',
  'src/app/profile.tsx',
];

const BANNED = [
  'diagnostic',
  'remediation',
  'canonical',
  'projector',
  'scheduler',
  'instruction_policy',
  'ai_run',
  'service_tier',
  'reasoning',
];

describe('production parent copy scan', () => {
  it('keeps engine words out of parent screens', () => {
    for (const relative of PRODUCTION_SCREENS) {
      const text = readFileSync(join(ROOT, relative), 'utf8').toLowerCase();
      for (const word of BANNED) {
        assert.equal(
          text.includes(word),
          false,
          `${relative} contains ${word}`,
        );
      }
    }
  });

  it('historical detail source never uses Today’s Win / Today’s Focus', () => {
    const source = readFileSync(join(ROOT, 'src/app/daily-win.tsx'), 'utf8');
    const historyFn = source.slice(source.indexOf('function HistoryDetail'));
    const body = historyFn.slice(0, historyFn.indexOf('function DailyWinSession'));
    assert.doesNotMatch(body, /Today['’]s Win/);
    assert.doesNotMatch(body, /Today['’]s Focus/);
    assert.doesNotMatch(body, /Today's Win/);
  });
});
