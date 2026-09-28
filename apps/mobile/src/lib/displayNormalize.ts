/** Display-only copy cleanup. Never rewrites educational meaning. */

const MULTI_SPACE = /\s+/g;
const SPACE_BEFORE_PUNCT = /\s+([,.;:!?])/g;
const DUP_TERMINAL = /([.!?]){2,}/g;
const DUP_COMMA = /([,;:]){2,}/g;
const SPACE_AFTER_OPEN = /([([{])\s+/g;

export function normalizeDisplayText(value: string | null | undefined): string {
  if (value == null) {
    return '';
  }
  return value
    .replace(/\r\n|\r|\n/g, ' ')
    .replace(MULTI_SPACE, ' ')
    .replace(SPACE_BEFORE_PUNCT, '$1')
    .replace(DUP_TERMINAL, '$1')
    .replace(DUP_COMMA, '$1')
    .replace(SPACE_AFTER_OPEN, '$1')
    .trim();
}

export function joinDisplayFragments(
  parts: readonly (string | null | undefined)[],
  separator = ' ',
): string {
  const cleaned = parts
    .map((item) => normalizeDisplayText(item))
    .filter((item) => item.length > 0);
  return normalizeDisplayText(cleaned.join(separator));
}

export const SELECTABLE_LABEL_MAX = 42;

export function isSelectableLabel(value: string | null | undefined): boolean {
  if (value == null) {
    return false;
  }
  if (value.includes('\n') || value.includes('\r')) {
    return false;
  }
  const text = normalizeDisplayText(value);
  if (!text) {
    return false;
  }
  if (text.length > SELECTABLE_LABEL_MAX) {
    return false;
  }
  if (looksLikeParagraph(text)) {
    return false;
  }
  return true;
}

export function looksLikeParagraph(value: string): boolean {
  const text = value.trim();
  if (text.length > SELECTABLE_LABEL_MAX) {
    return true;
  }
  const sentences = text.split(/(?<=[.!?])\s+/).filter((item) => item.length > 0);
  return sentences.length >= 2;
}

export function looksLikeRawEnum(value: string | null | undefined): boolean {
  if (value == null) {
    return true;
  }
  const text = value.trim();
  if (!text) {
    return true;
  }
  if (text === 'undefined' || text === 'null' || text === '[object Object]') {
    return true;
  }
  if (text.includes('_') && !text.includes(' ')) {
    return true;
  }
  return false;
}
