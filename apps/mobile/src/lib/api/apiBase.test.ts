import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  healthRequestUrl,
  isMissingApiBaseUrl,
  normalizeApiBaseUrl,
} from './apiBase.ts';

describe('API base URL', () => {
  it('keeps a URL with no trailing slash', () => {
    assert.equal(
      normalizeApiBaseUrl('https://sweet-stocks-tokyo-gilbert.trycloudflare.com'),
      'https://sweet-stocks-tokyo-gilbert.trycloudflare.com',
    );
  });

  it('strips one trailing slash', () => {
    assert.equal(
      normalizeApiBaseUrl('https://sweet-stocks-tokyo-gilbert.trycloudflare.com/'),
      'https://sweet-stocks-tokyo-gilbert.trycloudflare.com',
    );
  });

  it('strips multiple trailing slashes', () => {
    assert.equal(
      normalizeApiBaseUrl('https://sweet-stocks-tokyo-gilbert.trycloudflare.com///'),
      'https://sweet-stocks-tokyo-gilbert.trycloudflare.com',
    );
  });

  it('treats missing or blank values as absent', () => {
    assert.equal(normalizeApiBaseUrl(undefined), undefined);
    assert.equal(normalizeApiBaseUrl(null), undefined);
    assert.equal(normalizeApiBaseUrl(''), undefined);
    assert.equal(normalizeApiBaseUrl('   '), undefined);
    assert.equal(isMissingApiBaseUrl(undefined), true);
    assert.equal(isMissingApiBaseUrl('https://example.test'), false);
  });

  it('builds a health URL with exactly one slash before health', () => {
    const base = normalizeApiBaseUrl(
      'https://sweet-stocks-tokyo-gilbert.trycloudflare.com/',
    );
    assert.ok(base);
    assert.equal(
      healthRequestUrl(base),
      'https://sweet-stocks-tokyo-gilbert.trycloudflare.com/health',
    );
    assert.match(healthRequestUrl(base), /[^/]\/health$/);
    assert.doesNotMatch(healthRequestUrl(base), /\/\/health/);
  });
});
