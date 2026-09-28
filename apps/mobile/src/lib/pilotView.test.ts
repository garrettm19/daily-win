import assert from 'node:assert/strict';
import { afterEach, describe, it } from 'node:test';

import {
  hydratePilotView,
  isParentPilotView,
  resetPilotViewForTests,
  setParentPilotView,
  setPilotViewStoreForTests,
  type PilotViewStore,
} from './pilotView.ts';

afterEach(() => {
  resetPilotViewForTests();
  delete (globalThis as { __DEV__?: boolean }).__DEV__;
});

function memoryStore(initial: string | null = null): PilotViewStore & { writes: string[] } {
  let value = initial;
  const writes: string[] = [];
  return {
    writes,
    async getItem() {
      return value;
    },
    async setItem(_key: string, next: string) {
      writes.push(next);
      value = next;
    },
  };
}

describe('parent pilot view', () => {
  it('hides developer surfaces only in development when enabled', () => {
    (globalThis as { __DEV__?: boolean }).__DEV__ = true;
    assert.equal(isParentPilotView(), false);
    setParentPilotView(true);
    assert.equal(isParentPilotView(), true);
    setParentPilotView(false);
    assert.equal(isParentPilotView(), false);
  });

  it('hydrates from storage without restarting', async () => {
    (globalThis as { __DEV__?: boolean }).__DEV__ = true;
    const store = memoryStore('on');
    setPilotViewStoreForTests(store);
    await hydratePilotView();
    assert.equal(isParentPilotView(), true);
    setParentPilotView(false);
    assert.equal(store.writes.at(-1), 'off');
    assert.equal(isParentPilotView(), false);
  });

  it('never enables outside development', () => {
    (globalThis as { __DEV__?: boolean }).__DEV__ = false;
    setParentPilotView(true);
    assert.equal(isParentPilotView(), false);
  });
});
