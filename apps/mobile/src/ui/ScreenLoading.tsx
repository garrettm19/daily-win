import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';
import { colors, space } from '@/theme';
import { AppText } from '@/ui/AppText';

const SUPPORTING = [
  "Using this child's goals",
  'Considering recent reflections',
  "Building today's activity",
];

export function ScreenLoading({
  title,
  body,
  supporting = false,
}: {
  title: string;
  body?: string;
  supporting?: boolean;
}) {
  const [index, setIndex] = useState(0);
  const reduceMotion = usePrefersReducedMotion();

  useEffect(() => {
    if (!supporting || reduceMotion) {
      return;
    }
    const timer = setInterval(() => {
      setIndex((current) => (current + 1) % SUPPORTING.length);
    }, 2400);
    return () => clearInterval(timer);
  }, [supporting, reduceMotion]);

  return (
    <View
      style={styles.wrap}
      accessibilityRole="progressbar"
      accessibilityLabel={title}>
      <ActivityIndicator color={colors.actionPrimary} />
      <AppText variant="bodyEmphasized">{title}</AppText>
      {body ? <AppText variant="secondary">{body}</AppText> : null}
      {supporting ? (
        <AppText
          variant="caption"
          accessibilityLiveRegion="polite"
          accessibilityLabel={`Status: ${SUPPORTING[index]}`}>
          {SUPPORTING[index]}
        </AppText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: space.md,
    alignItems: 'flex-start',
    gap: 8,
  },
});
