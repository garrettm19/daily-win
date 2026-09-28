import { StyleSheet, View } from 'react-native';

import { radius, space } from '@/theme';
import { AppText } from '@/ui/AppText';

export function ResultMetric({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  if (!value) {
    return null;
  }
  return (
    <View style={styles.wrap}>
      <AppText variant="sectionLabel">{label}</AppText>
      <AppText variant="cardTitle">{value}</AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexGrow: 1,
    minWidth: 120,
    paddingVertical: space.sm,
    paddingRight: space.md,
    gap: space.xxs,
    borderRadius: radius.card,
  },
});
