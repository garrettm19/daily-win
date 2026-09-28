import { Pressable, StyleSheet, View } from 'react-native';

import {
  independenceTrendCopy,
  recentSupportSummary,
  stageFromProgress,
  type IndependenceLevel,
} from '@/lib/competency';
import type { DemoAcademicProgress } from '@/lib/api/types';
import { colors, radius, space } from '@/theme';
import { AppText } from '@/ui/AppText';
import { IndependenceTrend } from '@/ui/IndependenceTrend';
import { ProgressStage } from '@/ui/ProgressStage';

export function SkillCard({
  skill,
  points,
  nextMove,
  onPress,
}: {
  skill: DemoAcademicProgress;
  points: IndependenceLevel[];
  nextMove?: string | null;
  onPress?: () => void;
}) {
  const stage = stageFromProgress(skill);
  const summary = recentSupportSummary(points);
  const trend = independenceTrendCopy(points);
  const inner = (
    <>
      <AppText variant="caption">{skill.domain_label}</AppText>
      <AppText variant="cardTitle">{skill.skill_name}</AppText>
      <ProgressStage stage={stage} compact />
      {summary ? <AppText variant="secondary">{summary}</AppText> : null}
      <IndependenceTrend points={points} caption={trend} />
      {nextMove ? (
        <AppText variant="caption" style={styles.next}>
          Next: {nextMove}
        </AppText>
      ) : null}
    </>
  );
  if (!onPress) {
    return <View style={styles.card}>{inner}</View>;
  }
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${skill.skill_name}, ${skill.state_label}`}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}>
      {inner}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minWidth: 148,
    padding: space.md,
    borderRadius: radius.card,
    backgroundColor: colors.surface,
    gap: space.xs,
  },
  pressed: {
    opacity: 0.88,
  },
  next: {
    marginTop: space.xxs,
  },
});
