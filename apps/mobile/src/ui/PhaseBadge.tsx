import { StyleSheet, View } from 'react-native';

import { colors, radius } from '@/theme';
import { AppText } from '@/ui/AppText';
import { Icon, type IconName } from '@/ui/Icon';

const PHASE = {
  LEARN: {
    label: 'Learn',
    icon: 'book-outline' as IconName,
    accent: colors.phaseLearn,
  },
  DO: {
    label: 'Do',
    icon: 'walk-outline' as IconName,
    accent: colors.phaseDo,
  },
  GROW: {
    label: 'Grow',
    icon: 'leaf-outline' as IconName,
    accent: colors.phaseGrow,
  },
};

export function PhaseBadge({ type }: { type: 'LEARN' | 'DO' | 'GROW' }) {
  const phase = PHASE[type];
  return (
    <View style={styles.row}>
      <View style={[styles.mark, { backgroundColor: phase.accent }]} />
      <Icon name={phase.icon} size={16} color={phase.accent} />
      <AppText variant="sectionLabel">{phase.label}</AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  mark: {
    width: 8,
    height: 8,
    borderRadius: radius.chipPill,
  },
});
