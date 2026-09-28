import { type Href, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { useBackendStatus } from '@/hooks/useBackendStatus';
import { useParentPilotView } from '@/hooks/useParentPilotView';
import { backendStatusLabel } from '@/lib/api/backendStatus';
import { resetDemoActivityHistory, restartDemoSession } from '@/lib/api/demo';
import { describeCaughtError, type ApiErrorKind } from '@/lib/api/parentErrors';
import { DEMO_BUILD_DATE, DEMO_VERSION } from '@/lib/buildInfo';
import {
  formatTesterLabel,
  getCachedTesterFingerprint,
  getDemoSession,
  subscribeTesterFingerprint,
} from '@/lib/demoSession';
import { hapticSuccess } from '@/lib/haptics';
import { setParentPilotView } from '@/lib/pilotView';
import { colors, radius, space, type } from '@/theme';
import { DevError } from '@/ui/DevError';

type DemoControlsProps = {
  disabled?: boolean;
  testerFingerprint?: string | null;
  onActivityResetSucceeded: () => void;
  onRestartSucceeded: () => void;
};

function useLocalTesterFingerprint(): string | null {
  const [fingerprint, setFingerprint] = useState<string | null>(
    getCachedTesterFingerprint,
  );

  useEffect(() => {
    const unsubscribe = subscribeTesterFingerprint(() => {
      setFingerprint(getCachedTesterFingerprint());
    });
    void getDemoSession()
      .then(() => {
        setFingerprint(getCachedTesterFingerprint());
      })
      .catch(() => {
        setFingerprint(getCachedTesterFingerprint());
      });
    return unsubscribe;
  }, []);

  return fingerprint;
}

export function DemoControls({
  disabled = false,
  testerFingerprint,
  onActivityResetSucceeded,
  onRestartSucceeded,
}: DemoControlsProps) {
  const router = useRouter();
  const backendStatus = useBackendStatus();
  const localFingerprint = useLocalTesterFingerprint();
  const testerLabel = formatTesterLabel(localFingerprint ?? testerFingerprint);
  const [resetting, setResetting] = useState<'activity' | 'session' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const resetLock = useRef(false);
  const busy = resetting !== null || disabled;
  const parentPilotView = useParentPilotView();

  if (!__DEV__ || parentPilotView) {
    return null;
  }

  const confirmActivityReset = () => {
    if (resetLock.current || busy) {
      return;
    }
    Alert.alert(
      'Reset activity history?',
      'This removes Daily Wins, reflections, and what Daily Win has learned so far. The demo profile stays.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset history',
          style: 'destructive',
          onPress: () => {
            void runActivityReset();
          },
        },
      ],
    );
  };

  const confirmRestart = () => {
    if (resetLock.current || busy) {
      return;
    }
    Alert.alert(
      'Start fresh parent pilot?',
      'This deletes this session’s demo profile and activity history. You will return to the first screen. Other testers are not affected.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Erase this demo',
          style: 'destructive',
          onPress: () => {
            Alert.alert(
              'Are you sure?',
              'This cannot be undone for this tester session.',
              [
                { text: 'Cancel', style: 'cancel' },
                {
                  text: 'Start fresh parent pilot',
                  style: 'destructive',
                  onPress: () => {
                    void runRestart();
                  },
                },
              ],
            );
          },
        },
      ],
    );
  };

  const runActivityReset = async () => {
    if (resetLock.current || busy) {
      return;
    }
    resetLock.current = true;
    setResetting('activity');
    setError(null);
    setErrorCode(null);
    setErrorKind(null);
    try {
      await resetDemoActivityHistory();
      hapticSuccess();
      onActivityResetSucceeded();
    } catch (caught: unknown) {
      const described = describeCaughtError(
        caught,
        "Couldn't reset activity history. Try again.",
      );
      setError(described.message);
      setErrorCode(described.code);
      setErrorKind(described.kind);
    } finally {
      resetLock.current = false;
      setResetting(null);
    }
  };

  const runRestart = async () => {
    if (resetLock.current || busy) {
      return;
    }
    resetLock.current = true;
    setResetting('session');
    setError(null);
    setErrorCode(null);
    setErrorKind(null);
    try {
      await restartDemoSession();
      hapticSuccess();
      onRestartSucceeded();
    } catch (caught: unknown) {
      const described = describeCaughtError(
        caught,
        "Couldn't restart the demo. Try again.",
      );
      setError(described.message);
      setErrorCode(described.code);
      setErrorKind(described.kind);
    } finally {
      resetLock.current = false;
      setResetting(null);
    }
  };

  return (
    <View style={styles.wrap}>
      <Text style={styles.eyebrow}>Development</Text>
      <Text style={styles.meta}>{`Demo ${DEMO_VERSION}`}</Text>
      {testerLabel ? <Text style={styles.meta}>{testerLabel}</Text> : null}
      <Text style={styles.meta}>
        Backend: {backendStatusLabel(backendStatus)}
      </Text>
      <Text style={styles.hint}>{`Build ${DEMO_BUILD_DATE}. Testing utility — not part of the parent experience.`}</Text>
      {error ? (
        <>
          <Text style={styles.error}>{error}</Text>
          <DevError code={errorCode} kind={errorKind} />
        </>
      ) : null}
      <MutedAction
        label={resetting === 'activity' ? 'Resetting…' : 'Reset activity history'}
        accessibilityLabel="Reset activity history"
        disabled={busy}
        busy={resetting === 'activity'}
        onPress={confirmActivityReset}
      />
      <MutedAction
        label={
          resetting === 'session' ? 'Starting fresh…' : 'Start fresh parent pilot'
        }
        accessibilityLabel="Start fresh parent pilot"
        disabled={busy}
        busy={resetting === 'session'}
        onPress={confirmRestart}
      />
      <MutedAction
        label="Turn on Parent Pilot View"
        accessibilityLabel="Turn on Parent Pilot View"
        disabled={busy}
        onPress={() => setParentPilotView(true)}
      />
      <MutedAction
        label="Learning QA"
        accessibilityLabel="Open learning QA"
        disabled={busy}
        onPress={() => router.push('/learning-qa' as Href)}
      />
      <MutedAction
        label="Test feedback"
        accessibilityLabel="Test feedback"
        disabled={busy}
        onPress={() => router.push('/test-feedback')}
      />
    </View>
  );
}

function MutedAction({
  label,
  accessibilityLabel,
  disabled,
  busy = false,
  onPress,
}: {
  label: string;
  accessibilityLabel: string;
  disabled: boolean;
  busy?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ disabled, busy }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        disabled && styles.disabled,
        pressed && !disabled && styles.pressed,
      ]}>
      <Text style={styles.buttonLabel}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: space.xxl,
    paddingTop: space.lg,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderSubtle,
  },
  eyebrow: {
    ...type.sectionLabel,
    color: colors.textSecondary,
  },
  meta: {
    ...type.caption,
    marginTop: 4,
  },
  hint: {
    ...type.caption,
    marginTop: 8,
  },
  error: {
    ...type.secondary,
    marginTop: 10,
    color: colors.danger,
  },
  button: {
    alignSelf: 'flex-start',
    marginTop: 10,
    minHeight: 44,
    minWidth: 44,
    paddingHorizontal: 12,
    borderRadius: radius.chip,
    justifyContent: 'center',
  },
  disabled: {
    opacity: 0.45,
  },
  pressed: {
    opacity: 0.7,
  },
  buttonLabel: {
    ...type.caption,
    fontWeight: '600',
    color: colors.textSecondary,
  },
});
