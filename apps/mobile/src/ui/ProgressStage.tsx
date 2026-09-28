import { StyleSheet, View } from 'react-native';

import {
  COMPETENCY_STAGES,
  stageIndex,
  stageLabel,
  type CompetencyStage,
} from '@/lib/competency';
import { colors, radius, space } from '@/theme';
import { AppText } from '@/ui/AppText';

export function ProgressStage({
  stage,
  compact = false,
}: {
  stage: CompetencyStage;
  compact?: boolean;
}) {
  const active = stageIndex(stage);
  return (
    <View
      style={styles.row}
      accessibilityRole="text"
      accessibilityLabel={`Current: ${stageLabel(stage)}`}>
      {COMPETENCY_STAGES.filter((item) => item !== 'not_observed').map((item, index) => {
        const filled = active > 0 && index < active;
        return (
          <View
            key={item}
            style={[
              compact ? styles.dotCompact : styles.dot,
              filled ? styles.filled : styles.empty,
            ]}
          />
        );
      })}
      <AppText variant={compact ? 'caption' : 'bodyEmphasized'} style={styles.label}>
        {stageLabel(stage)}
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.xs,
    flexWrap: 'wrap',
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: radius.chipPill,
  },
  dotCompact: {
    width: 8,
    height: 8,
    borderRadius: radius.chipPill,
  },
  filled: {
    backgroundColor: colors.actionPrimary,
  },
  empty: {
    backgroundColor: colors.borderSubtle,
  },
  label: {
    color: colors.textPrimary,
  },
});
