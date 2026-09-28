import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';

import { fetchDemoProgress } from '@/lib/api/demo';
import {
  EMPTY_COPY,
  PARENT_ERRORS,
  describeCaughtError,
  progressHasNoEvidence,
  type ApiErrorKind,
} from '@/lib/api/parentErrors';
import type { DemoAcademicProgress, DemoGoalProgress, DemoProgress } from '@/lib/api/types';
import {
  formatCheckDate,
  independenceFromResult,
  independenceLabel,
  independencePoints,
  independenceTrendCopy,
  nextMoveCopy,
  stageFromProgress,
} from '@/lib/competency';
import { hasVisibleText } from '@/lib/productCopy';
import { space } from '@/theme';
import { AppText } from '@/ui/AppText';
import { EmptyState } from '@/ui/EmptyState';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { IndependenceTrend } from '@/ui/IndependenceTrend';
import { ProgressStage } from '@/ui/ProgressStage';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { SkillCard } from '@/ui/SkillCard';
import { TextButton } from '@/ui/TextButton';

export default function ProgressScreen() {
  const router = useRouter();
  const [progress, setProgress] = useState<DemoProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [openSkill, setOpenSkill] = useState<string | null>(null);

  const load = useCallback(() => {
    void fetchDemoProgress()
      .then((next) => {
        setProgress(next);
        setError(null);
        setErrorKind(null);
        setErrorCode(null);
      })
      .catch((caught: unknown) => {
        const described = describeCaughtError(caught, PARENT_ERRORS.progress);
        setError(described.message);
        setErrorKind(described.kind);
        setErrorCode(described.code);
      })
      .finally(() => setLoading(false));
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const empty = progress !== null && progressHasNoEvidence(progress);
  const skills = progress?.academic_skills ?? [];
  const growth = progress?.growth_skills ?? progress?.goals ?? [];

  return (
    <Screen>
      <AppText variant="screenTitle">Progress</AppText>
      {loading && !progress ? <ScreenLoading title="Loading progress..." /> : null}
      {error ? (
        <ErrorCallout
          message={error}
          errorCode={errorCode}
          errorKind={errorKind}
          onRetry={load}
        />
      ) : null}
      {empty ? (
        <EmptyState
          title="Still gathering"
          body={EMPTY_COPY.progress}
          icon="leaf-outline"
        />
      ) : null}
      {skills.length > 0 ? (
        <View style={styles.section}>
          <AppText variant="sectionLabel">Skills</AppText>
          <View style={styles.cards}>
            {skills.map((skill) => {
              const key = `${skill.domain_label}-${skill.skill_name}`;
              const points = independencePoints(skill);
              return (
                <SkillCard
                  key={key}
                  skill={skill}
                  points={points}
                  nextMove={nextMoveCopy({ currentAdjustment: skill.supporting_copy })}
                  onPress={() => setOpenSkill((current) => (current === key ? null : key))}
                />
              );
            })}
          </View>
          {skills.map((skill) => {
            const key = `${skill.domain_label}-${skill.skill_name}`;
            if (openSkill !== key) {
              return null;
            }
            return <SkillDetail key={`${key}-detail`} skill={skill} />;
          })}
        </View>
      ) : null}
      {growth.length > 0 && !empty ? (
        <View style={styles.section}>
          <AppText variant="sectionLabel">Coaching</AppText>
          {growth.map((goal) => (
            <GrowthSkillBlock key={goal.display_name} goal={goal} />
          ))}
        </View>
      ) : null}
      <TextButton
        label="Recent Daily Wins"
        onPress={() => router.push('/history')}
      />
    </Screen>
  );
}

function SkillDetail({ skill }: { skill: DemoAcademicProgress }) {
  const points = independencePoints(skill);
  const checks = [...(skill.recent_checks ?? [])].reverse();
  return (
    <View style={styles.detail}>
      <AppText variant="cardTitle">{skill.skill_name}</AppText>
      <ProgressStage stage={stageFromProgress(skill)} />
      {checks.length > 0 ? (
        <View style={styles.checks}>
          {checks.map((check) => {
            const level = independenceFromResult(check.result);
            return (
              <AppText key={check.occurred_at} variant="secondary">
                {formatCheckDate(check.occurred_at)}
                {level ? ` · ${independenceLabel(level)}` : ''}
              </AppText>
            );
          })}
        </View>
      ) : hasVisibleText(skill.recent_evidence) ? (
        <AppText variant="secondary">{skill.recent_evidence}</AppText>
      ) : null}
      <IndependenceTrend points={points} caption={independenceTrendCopy(points)} />
    </View>
  );
}

function GrowthSkillBlock({ goal }: { goal: DemoGoalProgress }) {
  return (
    <View style={styles.growth}>
      <AppText variant="bodyEmphasized">{goal.display_name}</AppText>
      {goal.latest_observation && !goal.still_learning ? (
        <AppText variant="secondary">{goal.latest_observation}</AppText>
      ) : (
        <AppText variant="caption">Still gathering evidence</AppText>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    marginTop: space.xl,
    gap: space.sm,
  },
  cards: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: space.sm,
  },
  detail: {
    marginTop: space.md,
    gap: space.xs,
    paddingBottom: space.md,
  },
  checks: {
    gap: space.xxs,
  },
  growth: {
    gap: space.xxs,
    paddingBottom: space.md,
  },
});
