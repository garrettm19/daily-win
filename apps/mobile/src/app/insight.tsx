import { StyleSheet, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';

import {
  academicResultLabel,
  difficultyLabel,
  persistenceLabel,
  selfCorrectionLabel,
} from '@/lib/competency';
import { normalizeDisplayText } from '@/lib/displayNormalize';
import { hasVisibleText } from '@/lib/productCopy';
import { colors, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { Card } from '@/ui/Card';
import { GeneratedText } from '@/ui/GeneratedText';
import { ResultMetric } from '@/ui/ResultMetric';
import { Screen } from '@/ui/Screen';

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
    skill?: string | string[];
    academic_result?: string | string[];
    difficulty?: string | string[];
    setback?: string | string[];
    self_correction?: string | string[];
  }>();
  const observation = firstString(params.observation);
  const nextAdjustment = firstString(params.next_adjustment);
  const academicObservation = firstString(params.academic_observation);
  const growthObservation = firstString(params.growth_observation);
  const academicArea = firstString(params.academic_area);
  const skill = firstString(params.skill) || academicArea;
  const independence = academicResultLabel(firstString(params.academic_result));
  const challenge = difficultyLabel(firstString(params.difficulty));
  const persistence = persistenceLabel(firstString(params.setback));
  const selfCorrected = selfCorrectionLabel(firstString(params.self_correction));
  const showGrowth =
    hasVisibleText(growthObservation) &&
    growthObservation !== academicObservation &&
    growthObservation !== observation;

  const goHome = () => {
    router.dismissTo('/');
  };

  return (
    <Screen>
      <AppText variant="caption">Session complete</AppText>
      <AppText variant="screenTitle" style={styles.title}>
        Result
      </AppText>
      {hasVisibleText(skill) ? (
        <AppText variant="secondary">{skill}</AppText>
      ) : null}

      <View style={styles.metrics}>
        <ResultMetric label="Independence" value={independence} />
        <ResultMetric label="Challenge" value={challenge} />
        <ResultMetric label="Self-correction" value={selfCorrected} />
        <ResultMetric label="Persistence" value={persistence} />
      </View>

      {hasVisibleText(academicObservation) ? (
        <GeneratedText variant="body" style={styles.note}>
          {academicObservation}
        </GeneratedText>
      ) : hasVisibleText(observation) ? (
        <GeneratedText variant="body" style={styles.note}>
          {observation}
        </GeneratedText>
      ) : null}
      {showGrowth ? (
        <GeneratedText variant="body" style={styles.note}>
          {growthObservation}
        </GeneratedText>
      ) : null}

      <Card tone="soft" style={styles.block}>
        <AppText variant="sectionLabel">What changes next</AppText>
        <GeneratedText variant="emphasized">
          {hasVisibleText(nextAdjustment)
            ? normalizeDisplayText(nextAdjustment)
            : 'Same skill next time, adjusted from what you reported.'}
        </GeneratedText>
      </Card>
      <AppText variant="secondary" style={styles.note}>
        Next Win is preparing. You can close the app.
      </AppText>
      <AppButton label="Done" onPress={goHome} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: {
    marginTop: space.xs,
  },
  metrics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: space.lg,
    marginBottom: space.md,
  },
  block: {
    marginTop: space.md,
    marginBottom: space.lg,
    gap: space.xs,
  },
  note: {
    marginTop: space.sm,
    marginBottom: space.sm,
    color: colors.textSecondary,
  },
});
