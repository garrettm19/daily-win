import { StyleSheet, View } from 'react-native';

import { space } from '@/theme';
import { AppText } from '@/ui/AppText';

export function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  if (!value) {
    return null;
  }
  return (
    <View style={styles.wrap}>
      <AppText variant="sectionLabel">{label}</AppText>
      <AppText variant="bodyEmphasized">{value}</AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    minWidth: 96,
    gap: space.xxs,
    paddingVertical: space.xs,
    paddingRight: space.md,
  },
});
