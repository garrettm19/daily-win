import { StyleSheet, View } from 'react-native';

import { normalizeDisplayText } from '@/lib/displayNormalize';
import { hasVisibleText } from '@/lib/productCopy';
import { colors, radius, space } from '@/theme';
import { AppText } from '@/ui/AppText';
import { GeneratedText } from '@/ui/GeneratedText';

export function CoachCue({
  label = 'Watch for',
  text,
}: {
  label?: string;
  text: string | null | undefined;
}) {
  const body = normalizeDisplayText(text);
  if (!hasVisibleText(body)) {
    return null;
  }
  return (
    <View style={styles.wrap}>
      <AppText variant="sectionLabel">{label}</AppText>
      <GeneratedText variant="emphasized">{body}</GeneratedText>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: space.md,
    padding: space.md,
    borderRadius: radius.card,
    backgroundColor: colors.highlightSoft,
    gap: space.xs,
  },
});
