import { Platform, type TextStyle } from 'react-native';

import { colors } from './colors';

export const fontFamily = {
  display: 'Nunito_800ExtraBold',
  heading: 'Nunito_700Bold',
  body: Platform.select({ ios: 'System', android: 'sans-serif', default: undefined }),
} as const;

export const type = {
  display: {
    fontFamily: fontFamily.display,
    fontSize: 32,
    lineHeight: 40,
    color: colors.textPrimary,
  } satisfies TextStyle,
  screenTitle: {
    fontFamily: fontFamily.heading,
    fontSize: 26,
    lineHeight: 32,
    color: colors.textPrimary,
  } satisfies TextStyle,
  cardTitle: {
    fontFamily: fontFamily.heading,
    fontSize: 20,
    lineHeight: 26,
    color: colors.textPrimary,
  } satisfies TextStyle,
  body: {
    fontFamily: fontFamily.body,
    fontSize: 17,
    lineHeight: 24,
    fontWeight: '400',
    color: colors.textPrimary,
  } satisfies TextStyle,
  bodyEmphasized: {
    fontFamily: fontFamily.body,
    fontSize: 17,
    lineHeight: 24,
    fontWeight: '600',
    color: colors.textPrimary,
  } satisfies TextStyle,
  secondary: {
    fontFamily: fontFamily.body,
    fontSize: 15,
    lineHeight: 22,
    fontWeight: '400',
    color: colors.textSecondary,
  } satisfies TextStyle,
  caption: {
    fontFamily: fontFamily.body,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '500',
    color: colors.textSecondary,
  } satisfies TextStyle,
  sectionLabel: {
    fontFamily: fontFamily.body,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '600',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: colors.textSecondary,
  } satisfies TextStyle,
  metric: {
    fontFamily: fontFamily.heading,
    fontSize: 22,
    lineHeight: 28,
    color: colors.textPrimary,
  } satisfies TextStyle,
  button: {
    fontFamily: fontFamily.body,
    fontSize: 17,
    lineHeight: 22,
    fontWeight: '600',
  } satisfies TextStyle,
} as const;
