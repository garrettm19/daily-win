import { useRef, useState } from 'react';
import { StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';

import { recordGuideTiming } from '@/lib/api/demo';
import { GUIDE_SCREENS } from '@/lib/firstWin';
import { space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { Screen } from '@/ui/Screen';
import { TextButton } from '@/ui/TextButton';

export default function GuideScreen() {
  const router = useRouter();
  const [index, setIndex] = useState(0);
  const skipLock = useRef(false);
  const startedAt = useRef(new Date());
  const screen = GUIDE_SCREENS[index];
  const last = index === GUIDE_SCREENS.length - 1;

  const finish = (skipped: boolean) => {
    if (skipLock.current) {
      return;
    }
    skipLock.current = true;
    const finishedAt = new Date();
    const dwellMs = Math.max(0, finishedAt.getTime() - startedAt.current.getTime());
    void recordGuideTiming({
      guide_started_at: startedAt.current.toISOString(),
      guide_finished_at: finishedAt.toISOString(),
      guide_skipped: skipped,
      guide_dwell_ms: dwellMs,
    }).catch(() => undefined);
    router.replace('/');
  };

  return (
    <Screen edges={['top', 'bottom', 'left', 'right']}>
      <AppText variant="caption">
        {index + 1} of {GUIDE_SCREENS.length}
      </AppText>
      <AppText variant="display" style={styles.title}>
        {screen.title}
      </AppText>
      <AppText variant="body" style={styles.body}>
        {screen.body}
      </AppText>
      <AppButton
        label={last ? "See today’s Win" : 'Next'}
        onPress={() => {
          if (last) {
            finish(false);
            return;
          }
          setIndex(index + 1);
        }}
      />
      <TextButton label="Skip intro" onPress={() => finish(true)} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: {
    marginTop: space.md,
  },
  body: {
    marginTop: space.md,
    marginBottom: space.xl,
  },
});
