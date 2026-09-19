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
  tone?: 'surface' | 'soft' | 'highlight';
}) {
  return (
    <View
      style={[
        styles.card,
        tone === 'soft' && styles.soft,
        tone === 'highlight' && styles.highlight,
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
});
