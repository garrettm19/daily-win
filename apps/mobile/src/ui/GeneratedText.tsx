import { StyleSheet, Text, type TextProps } from 'react-native';

import { normalizeDisplayText } from '@/lib/displayNormalize';
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
  const content =
    typeof children === 'string' ? normalizeDisplayText(children) : children;

  return (
    <Text {...rest} style={[styles.base, variantStyle, style]}>
      {content}
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
