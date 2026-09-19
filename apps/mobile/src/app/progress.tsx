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
import { colors, space } from '@/theme';
import { AppText } from '@/ui/AppText';
import { EmptyState } from '@/ui/EmptyState';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { SectionLabel } from '@/ui/SectionLabel';
import { TextButton } from '@/ui/TextButton';

export default function ProgressScreen() {
  const router = useRouter();
  const [progress, setProgress] = useState<DemoProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    void fetchDemoProgress()
      .then((next) => {
        setProgress(next);
        setError(null);
        setErrorKind(null);
        setErrorCode(null);
      })
      .catch((caught: unknown) => {
        const described = describeCaughtError(caught, PARENT_ERRORS.load);
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

  return (
    <Screen>
      <AppText variant="screenTitle">What Daily Win is learning</AppText>
      {loading && !progress ? <ScreenLoading title="Loading progress" /> : null}
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
      {progress && (progress.academic_skills?.length ?? 0) > 0 ? (
        <View style={styles.section}>
          <SectionLabel>Academic skills</SectionLabel>
          {progress.academic_skills?.map((skill) => (
            <AcademicSkillBlock key={`${skill.domain_label}-${skill.skill_name}`} skill={skill} />
          ))}
          {progress.state_guide?.map((item) => (
            <AppText key={item.label} variant="caption" style={styles.guide}>
              {item.label}: {item.explanation}
            </AppText>
          ))}
          {progress.evidence_disclaimer ? (
            <AppText variant="caption" style={styles.disclaimer}>
              {progress.evidence_disclaimer}
            </AppText>
          ) : null}
        </View>
      ) : null}
      {progress && (progress.growth_skills ?? progress.goals).length > 0 ? (
        <View style={styles.section}>
          <SectionLabel>Growth skills</SectionLabel>
          {(progress.growth_skills ?? progress.goals).map((goal) => (
            <GrowthSkillBlock key={goal.display_name} goal={goal} />
          ))}
        </View>
      ) : null}
      {progress && progress.recent_observations.length > 0 ? (
        <View style={styles.obsBlock}>
          <SectionLabel>Recent observations</SectionLabel>
          {progress.recent_observations.map((item, index) => (
            <View key={`${item.goal_name}-${index}`} style={styles.obs}>
              <AppText variant="bodyEmphasized">{item.goal_name}</AppText>
              <AppText variant="secondary">{item.summary}</AppText>
            </View>
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

function AcademicSkillBlock({ skill }: { skill: DemoAcademicProgress }) {
  return (
    <View style={styles.goalBlock}>
      <AppText variant="caption">{skill.domain_label}</AppText>
      <AppText variant="cardTitle">{skill.skill_name}</AppText>
      <AppText variant="bodyEmphasized">{skill.state_label}</AppText>
      {skill.recent_evidence ? (
        <>
          <SectionLabel>Recent evidence</SectionLabel>
          <AppText variant="body">{skill.recent_evidence}</AppText>
        </>
      ) : null}
      <AppText variant="caption" style={styles.meta}>
        Evidence: {skill.evidence_label}
      </AppText>
      <AppText variant="secondary">{skill.supporting_copy}</AppText>
    </View>
  );
}

function GrowthSkillBlock({ goal }: { goal: DemoGoalProgress }) {
  return (
    <View style={styles.goalBlock}>
      <AppText variant="cardTitle">{goal.display_name}</AppText>
      {goal.latest_observation ? (
        <>
          <SectionLabel>Latest observation</SectionLabel>
          <AppText variant="body">{goal.latest_observation}</AppText>
        </>
      ) : null}
      {goal.current_adjustment ? (
        <>
          <SectionLabel>Current adjustment</SectionLabel>
          <AppText variant="body">{goal.current_adjustment}</AppText>
        </>
      ) : null}
      <AppText variant="caption" style={styles.meta}>
        {goal.evidence_label}
      </AppText>
      {goal.still_learning && goal.still_learning_message ? (
        <AppText variant="secondary">{goal.still_learning_message}</AppText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    marginTop: space.md,
  },
  goalBlock: {
    marginTop: space.xl,
    gap: 6,
    paddingBottom: space.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.borderSubtle,
  },
  meta: {
    marginTop: 4,
  },
  obsBlock: {
    marginTop: space.xl,
    gap: space.md,
  },
  obs: {
    gap: 4,
  },
  guide: {
    marginTop: space.sm,
  },
  disclaimer: {
    marginTop: space.md,
  },
});
