import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, type } from '@/theme';

export function StatusBadge({
  label,
  tone = 'neutral',
}: {
  label: string;
  tone?: 'neutral' | 'success' | 'pending' | 'adapted' | 'win';
}) {
  return (
    <View
      style={[
        styles.badge,
        tone === 'success' && styles.success,
        tone === 'pending' && styles.pending,
        tone === 'adapted' && styles.adapted,
        tone === 'win' && styles.win,
      ]}>
      <Text
        style={[
          styles.label,
          tone === 'win' && styles.winLabel,
          tone === 'success' && styles.successLabel,
        ]}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.chipPill,
    backgroundColor: colors.surfaceMuted,
  },
  success: {
    backgroundColor: colors.actionPrimarySoft,
  },
  pending: {
    backgroundColor: colors.surfaceMuted,
  },
  adapted: {
    backgroundColor: colors.highlightSoft,
  },
  win: {
    backgroundColor: colors.highlightSoft,
  },
  label: {
    ...type.caption,
    color: colors.textSecondary,
  },
  successLabel: {
    color: colors.actionPrimary,
  },
  winLabel: {
    color: colors.textPrimary,
  },
});
