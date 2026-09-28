import { StyleSheet, View } from 'react-native';

import type { SessionStep } from '@/lib/sessionSteps';
import { actionSteps } from '@/lib/sessionSteps';
import { colors, radius, space } from '@/theme';
import { AppText } from '@/ui/AppText';

export function SessionStepper({
  steps,
  currentId,
}: {
  steps: readonly SessionStep[];
  currentId: string;
}) {
  const actionable = actionSteps(steps);
  if (actionable.length === 0) {
    return null;
  }
  const active = actionable.findIndex((step) => step.id === currentId);
  const safeActive = active < 0 ? 0 : active;
  return (
    <View
      style={styles.wrap}
      accessibilityRole="text"
      accessibilityLabel={`Step ${safeActive + 1} of ${actionable.length}: ${actionable[safeActive]?.label ?? ''}`}>
      <View style={styles.dots}>
        {actionable.map((step, index) => (
          <View key={step.id} style={styles.unit}>
            <View
              style={[
                styles.dot,
                index <= safeActive ? styles.on : styles.off,
              ]}
            />
            {index < actionable.length - 1 ? (
              <View style={[styles.line, index < safeActive && styles.lineOn]} />
            ) : null}
          </View>
        ))}
      </View>
      <AppText variant="caption">
        {safeActive + 1} / {actionable.length} · {actionable[safeActive]?.label}
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: space.xs,
    marginBottom: space.md,
  },
  dots: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  unit: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: radius.chipPill,
  },
  on: {
    backgroundColor: colors.actionPrimary,
  },
  off: {
    backgroundColor: colors.borderSubtle,
  },
  line: {
    width: 22,
    height: 2,
    marginHorizontal: 4,
    backgroundColor: colors.borderSubtle,
  },
  lineOn: {
    backgroundColor: colors.actionPrimary,
  },
});
