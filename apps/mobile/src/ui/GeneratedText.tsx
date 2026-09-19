import { StyleSheet, Text, type TextProps } from 'react-native';

import { colors, type } from '@/theme';

export function GeneratedText({
  children,
  variant = 'body',
  style,
  ...rest
}: TextProps & {
  variant?: 'title' | 'body' | 'meta' | 'emphasized';
}) {
  const variantStyle =
    variant === 'title'
      ? type.screenTitle
      : variant === 'meta'
        ? type.secondary
        : variant === 'emphasized'
          ? type.bodyEmphasized
          : type.body;

  return (
    <Text {...rest} style={[styles.base, variantStyle, style]}>
      {children}
    </Text>
  );
}

const styles = StyleSheet.create({
  base: {
    width: '100%',
    flexShrink: 1,
    color: colors.textPrimary,
  },
});
