/**
 * Daily Win color tokens (V0.2.2 light theme).
 *
 * Semantic names only. Do not use gold (`highlight`) as small text on white.
 * Dark text on cream/gold surfaces. White text only on `actionPrimary`.
 *
 * V0.2.2 ships a light-only palette. Tokens are named so a dark theme can be
 * added later without renaming application code.
 */
export const colors = {
  background: '#FAF8F3',
  surface: '#FFFFFF',
  surfaceMuted: '#F3F0E8',
  textPrimary: '#1F2B28',
  textSecondary: '#5E6B66',
  textOnAction: '#FFFFFF',
  borderSubtle: '#D9E1DD',
  actionPrimary: '#2E6F62',
  actionPrimaryPressed: '#24584E',
  actionPrimarySoft: '#EAF3EF',
  highlight: '#F4C76E',
  highlightSoft: '#FFF5D8',
  danger: '#B54845',
  dangerSoft: '#F6E6E5',
  phaseLearn: '#5C7388',
  phaseDo: '#C4922A',
  phaseGrow: '#2E6F62',
} as const;

export type ColorToken = keyof typeof colors;
