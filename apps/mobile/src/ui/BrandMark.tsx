import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { DEMO_VERSION } from '@/lib/buildInfo';
import { isParentPilotView, setParentPilotView } from '@/lib/pilotView';
import { colors, space } from '@/theme';
import { useParentPilotView } from '@/hooks/useParentPilotView';
import { AppText } from '@/ui/AppText';
import { Icon } from '@/ui/Icon';
import { TextButton } from '@/ui/TextButton';

const ENGINE_STAMP = [
  `Daily Win ${DEMO_VERSION}`,
  'curriculum_v2',
  'instruction_policy_v4',
  'prompt v5',
];

export function BrandMark() {
  const pilot = useParentPilotView();
  const taps = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [inspect, setInspect] = useState(false);

  useEffect(() => {
    return () => {
      if (timer.current) {
        clearTimeout(timer.current);
      }
    };
  }, []);

  const onSecretTap = () => {
    if (!__DEV__) {
      return;
    }
    taps.current += 1;
    if (timer.current) {
      clearTimeout(timer.current);
    }
    timer.current = setTimeout(() => {
      taps.current = 0;
    }, 900);
    if (taps.current >= 5) {
      taps.current = 0;
      setInspect(true);
    }
  };

  return (
    <View>
      <Pressable
        onPress={onSecretTap}
        accessibilityRole="button"
        accessibilityLabel="Daily Win"
        accessibilityHint={
          __DEV__ ? 'Tap five times to inspect the development build' : undefined
        }>
        <View style={styles.brandRow}>
          <Icon name="sparkles" size={16} color={colors.highlight} />
          <AppText variant="sectionLabel">Daily Win</AppText>
        </View>
      </Pressable>
      {__DEV__ && inspect ? (
        <View style={styles.inspect}>
          {ENGINE_STAMP.map((line) => (
            <AppText key={line} variant="caption">
              {line}
            </AppText>
          ))}
          <TextButton
            label={
              isParentPilotView() || pilot
                ? 'Show developer tools'
                : 'Hide developer tools'
            }
            onPress={() => {
              setParentPilotView(!isParentPilotView());
              setInspect(false);
            }}
          />
          <TextButton label="Close" onPress={() => setInspect(false)} />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: space.lg,
  },
  inspect: {
    marginBottom: space.md,
    gap: 2,
  },
});
