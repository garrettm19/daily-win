import { useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';

import { ApiError } from '@/lib/api/client';
import { generateDemoDailyWinSafely } from '@/lib/api/demo';
import { parentMessage, type ApiErrorKind } from '@/lib/api/parentErrors';
import { colors, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { Card } from '@/ui/Card';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { GeneratedText } from '@/ui/GeneratedText';
import { Icon } from '@/ui/Icon';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { SectionLabel } from '@/ui/SectionLabel';

function firstString(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] ?? '';
  }
  return value ?? '';
}

export default function InsightScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    observation?: string | string[];
    next_adjustment?: string | string[];
    nickname?: string | string[];
    academic_observation?: string | string[];
    growth_observation?: string | string[];
    academic_area?: string | string[];
  }>();
  const observation = firstString(params.observation);
  const nextAdjustment = firstString(params.next_adjustment);
  const nickname = firstString(params.nickname) || 'this child';
  const academicObservation = firstString(params.academic_observation);
  const growthObservation = firstString(params.growth_observation) || observation;
  const academicArea = firstString(params.academic_area);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const generateLock = useRef(false);

  const goHome = () => {
    router.dismissTo('/');
  };

  const handleGenerate = () => {
    if (generateLock.current || generating) {
      return;
    }
    generateLock.current = true;
    setGenerating(true);
    setError(null);
    setErrorCode(null);
    setErrorKind(null);
    void generateDemoDailyWinSafely()
      .then(() => {
        if (router.canDismiss()) {
          router.dismissTo('/');
        }
        router.push('/daily-win');
      })
      .catch((caught: unknown) => {
        generateLock.current = false;
        if (caught instanceof ApiError) {
          setError(parentMessage('generate', caught.kind));
          setErrorCode(caught.errorCode ?? null);
          setErrorKind(caught.kind);
          return;
        }
        setError(parentMessage('generate'));
        setErrorKind('unavailable');
      })
      .finally(() => {
        setGenerating(false);
      });
  };

  return (
    <Screen>
      <View style={styles.success}>
        <Icon name="checkmark-circle" size={28} color={colors.actionPrimary} />
        <AppText variant="caption">The app listened.</AppText>
      </View>
      <SectionLabel>What we learned</SectionLabel>
        {academicObservation ? (
        <Card style={styles.block}>
          {academicArea ? (
            <AppText variant="caption">{academicArea}</AppText>
          ) : null}
          <GeneratedText variant="emphasized">{academicObservation}</GeneratedText>
        </Card>
      ) : null}
      <Card style={styles.block}>
        {academicObservation ? (
          <AppText variant="caption">Persistence</AppText>
        ) : null}
        <GeneratedText variant="emphasized">
          {growthObservation || 'The reflection was saved.'}
        </GeneratedText>
      </Card>
      <SectionLabel>What changes next</SectionLabel>
      <Card tone="soft" style={styles.block}>
        <GeneratedText variant="emphasized">
          {nextAdjustment || 'The next Daily Win can now be generated.'}
        </GeneratedText>
      </Card>
      {generating ? (
        <ScreenLoading
          title={`Designing ${nickname}'s next Daily Win…`}
          body="Using what you reported to make a modest adjustment."
          supporting
        />
      ) : null}
      {error ? (
        <ErrorCallout message={error} errorCode={errorCode} errorKind={errorKind} />
      ) : null}
      <AppButton
        label={
          generating
            ? `Designing ${nickname}'s next Daily Win…`
            : error
              ? 'Retry'
              : `Generate ${nickname}'s next Daily Win`
        }
        accessibilityLabel={`Generate ${nickname}'s next Daily Win`}
        disabled={generating}
        loading={generating}
        onPress={handleGenerate}
      />
      <AppButton label="Back to Home" variant="secondary" onPress={goHome} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  success: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: space.lg,
  },
  block: {
    marginTop: space.sm,
    marginBottom: space.xl,
  },
});
