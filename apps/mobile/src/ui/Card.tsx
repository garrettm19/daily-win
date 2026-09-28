import { type ReactNode } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';

import { colors, radius, space } from '@/theme';

export function Card({
  children,
  style,
  tone = 'surface',
}: {
  children: ReactNode;
  style?: ViewStyle;
  tone?: 'surface' | 'soft' | 'highlight' | 'plain';
}) {
  return (
    <View
      style={[
        styles.card,
        tone === 'soft' && styles.soft,
        tone === 'highlight' && styles.highlight,
        tone === 'plain' && styles.plain,
        style,
      ]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: space.card,
    borderRadius: radius.card,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignSelf: 'stretch',
  },
  soft: {
    backgroundColor: colors.actionPrimarySoft,
    borderColor: colors.actionPrimarySoft,
  },
  highlight: {
    backgroundColor: colors.highlightSoft,
    borderColor: colors.highlightSoft,
  },
  plain: {
    backgroundColor: 'transparent',
    borderWidth: 0,
    padding: 0,
  },
});
