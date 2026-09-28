import { StyleSheet, View } from 'react-native';

import { type IndependenceLevel } from '@/lib/competency';
import { colors, radius, space } from '@/theme';
import { AppText } from '@/ui/AppText';

export function IndependenceTrend({
  points,
  caption,
}: {
  points: IndependenceLevel[];
  caption: string;
}) {
  if (points.length === 0) {
    return (
      <AppText variant="caption" accessibilityLabel={caption}>
        {caption}
      </AppText>
    );
  }
  return (
    <View accessibilityRole="text" accessibilityLabel={caption}>
      <View style={styles.row}>
        {points.map((point, index) => (
          <View
            key={`${point}-${index}`}
            style={[styles.dot, tone(point)]}
            accessibilityElementsHidden
          />
        ))}
      </View>
      <AppText variant="caption">{caption}</AppText>
    </View>
  );
}

function tone(level: IndependenceLevel) {
  if (level === 'independent') {
    return styles.independent;
  }
  if (level === 'light_help') {
    return styles.light;
  }
  if (level === 'significant_help') {
    return styles.heavy;
  }
  return styles.notYet;
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.xs,
    marginTop: space.xxs,
    marginBottom: space.xxs,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: radius.chipPill,
  },
  independent: {
    backgroundColor: colors.actionPrimary,
  },
  light: {
    backgroundColor: colors.highlight,
  },
  heavy: {
    backgroundColor: colors.phaseLearn,
  },
  notYet: {
    backgroundColor: colors.borderSubtle,
  },
});
