import { useCallback, useEffect, useRef, useState } from 'react';
import { Animated, StyleSheet, View } from 'react-native';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';
import { fetchDemoDailyWin, fetchLatestDemoDailyWin } from '@/lib/api/demo';
import { parentMessage } from '@/lib/api/parentErrors';
import type { DailyWinSegment, DemoDailyWin, LearningEngineDebug } from '@/lib/api/types';
import { changedTodayCopy } from '@/lib/academicLoop';
import { colors, motion, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { Card } from '@/ui/Card';
import { EmptyState } from '@/ui/EmptyState';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { GeneratedText } from '@/ui/GeneratedText';
import { Icon } from '@/ui/Icon';
import { PhaseBadge } from '@/ui/PhaseBadge';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { SectionLabel } from '@/ui/SectionLabel';
import { TextButton } from '@/ui/TextButton';

const MATERIAL_LABELS: Record<string, string> = {
  NONE: 'None needed',
  PAPER: 'Paper',
  PENCIL: 'Pencil',
  CRAYONS_OR_MARKERS: 'Crayons or markers',
  TAPE: 'Tape',
  INDEX_CARDS: 'Index cards',
  PLASTIC_CUPS: 'Plastic cups',
  BLOCKS: 'Blocks',
  BOOK: 'Book',
  COINS: 'Coins',
  SOFT_BALL: 'Soft ball',
  TIMER: 'Timer',
};

const SEGMENT_ORDER: DailyWinSegment['type'][] = ['LEARN', 'DO', 'GROW'];

export default function DailyWinScreen() {
  const params = useLocalSearchParams<{ id?: string | string[] }>();
  const requestedId = Array.isArray(params.id) ? params.id[0] : params.id;
  const [dailyWin, setDailyWin] = useState<DemoDailyWin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [started, setStarted] = useState(false);
  const loadedId = useRef<string | null>(null);
  const generationRef = useRef(0);

  const load = useCallback((showLoading: boolean) => {
    const generation = ++generationRef.current;
    if (showLoading) {
      setLoading(true);
    }
    const request = requestedId
      ? fetchDemoDailyWin(requestedId)
      : fetchLatestDemoDailyWin();
    void request
      .then((result) => {
        if (generation !== generationRef.current) {
          return;
        }
        if (result === null) {
          setError('No Daily Win is available yet.');
          setDailyWin(null);
          return;
        }
        if (loadedId.current !== result.id) {
          loadedId.current = result.id;
          setStarted(result.has_feedback);
        }
        setDailyWin(result);
        setError(null);
      })
      .catch(() => {
        if (generation !== generationRef.current) {
          return;
        }
        setError(parentMessage('load'));
      })
      .finally(() => {
        if (generation === generationRef.current) {
          setLoading(false);
        }
      });
  }, [requestedId]);

  useFocusEffect(
    useCallback(() => {
      load(loadedId.current === null);
    }, [load]),
  );

  if (loading && !dailyWin) {
    return (
      <Screen scroll={false}>
        <ScreenLoading title="Loading today’s Daily Win" body="Pulling the saved activity." />
      </Screen>
    );
  }

  if (!loading && error && !dailyWin) {
    const empty = error === 'No Daily Win is available yet.';
    return (
      <Screen scroll={false}>
        {empty ? (
          <EmptyState
            title="No Daily Win is available yet."
            body="Go home and generate today’s Daily Win."
          />
        ) : (
          <ErrorCallout
            message={parentMessage('load')}
            onRetry={() => load(true)}
          />
        )}
      </Screen>
    );
  }

  if (!dailyWin) {
    return (
      <Screen scroll={false}>
        <ScreenLoading title="Loading today’s Daily Win" />
      </Screen>
    );
  }

  return (
    <Screen>
      <DailyWinBody
        key={dailyWin.id}
        dailyWin={dailyWin}
        started={started}
        onStart={() => setStarted(true)}
      />
    </Screen>
  );
}

function DailyWinBody({
  dailyWin,
  started,
  onStart,
}: {
  dailyWin: DemoDailyWin;
  started: boolean;
  onStart: () => void;
}) {
  const router = useRouter();
  const reduceMotion = usePrefersReducedMotion();
  const skipIntro = useRef(started);
  const [reveal] = useState(() => new Animated.Value(started ? 1 : 0));
  const changedToday = changedTodayCopy(dailyWin);
  const materials = dailyWin.content.materials
    .filter((item) => item !== 'NONE')
    .map((item) => MATERIAL_LABELS[item] ?? item);
  const segments = [...dailyWin.content.segments].sort(
    (left, right) =>
      SEGMENT_ORDER.indexOf(left.type) - SEGMENT_ORDER.indexOf(right.type),
  );

  useEffect(() => {
    if (!started) {
      return;
    }
    if (skipIntro.current) {
      skipIntro.current = false;
      reveal.setValue(1);
      return;
    }
    if (reduceMotion) {
      reveal.setValue(1);
      return;
    }
    reveal.setValue(0);
    Animated.timing(reveal, {
      toValue: 1,
      duration: motion.normal,
      useNativeDriver: true,
    }).start();
  }, [reduceMotion, reveal, started]);

  return (
    <>
      <GeneratedText variant="title">{dailyWin.title}</GeneratedText>
      <AppText variant="secondary" style={styles.meta}>
        {dailyWin.primary_skill_display_name} • About {dailyWin.duration_minutes}{' '}
        minutes
      </AppText>
      <GeneratedText variant="body" style={styles.objective}>
        {dailyWin.objective}
      </GeneratedText>

      {changedToday ? (
        <Card tone="highlight" style={styles.changeCard}>
          <View style={styles.changeHeader}>
            <Icon name="sparkles" size={16} color={colors.textPrimary} />
            <SectionLabel style={styles.changeLabel}>What changed today</SectionLabel>
          </View>
          <GeneratedText variant="emphasized" style={styles.changeBody}>
            {changedToday}
          </GeneratedText>
        </Card>
      ) : null}

      <View style={styles.briefing}>
        <SectionLabel>Why this Win</SectionLabel>
        <GeneratedText style={styles.briefIntro}>
          {dailyWin.content.personalization_summary}
        </GeneratedText>
        <BriefBlock label="Purpose" text={dailyWin.content.parent_briefing.purpose} />
        <BriefBlock
          label="How to coach"
          text={dailyWin.content.parent_briefing.how_to_coach}
        />
        <BriefBlock
          label="Watch for"
          text={dailyWin.content.parent_briefing.watch_for}
        />
        <BriefBlock label="Avoid" text={dailyWin.content.parent_briefing.avoid} />
      </View>

      <AppText variant="caption" style={styles.materials}>
        {materials.length > 0
          ? `Before you start: ${materials.join(', ')}`
          : 'Before you start: no extra materials.'}
      </AppText>

      {!started ? (
        <AppButton
          label={`Start with ${dailyWin.child_nickname}`}
          onPress={onStart}
        />
      ) : null}

      {started ? (
        <Animated.View
          style={{
            opacity: reveal,
            transform: [
              {
                translateY: reveal.interpolate({
                  inputRange: [0, 1],
                  outputRange: [reduceMotion ? 0 : motion.enterOffset, 0],
                }),
              },
            ],
          }}>
          {segments.map((segment) => (
            <SegmentBlock key={segment.type} segment={segment} />
          ))}

          {dailyWin.assessment ? (
            <View style={styles.checkBlock}>
              <SectionLabel>What to check</SectionLabel>
              <GeneratedText variant="emphasized">
                {dailyWin.assessment.what_to_check}
              </GeneratedText>
              <SectionLabel>Success looks like</SectionLabel>
              <GeneratedText>{dailyWin.assessment.success_looks_like}</GeneratedText>
            </View>
          ) : null}

          <View style={styles.adaptBlock}>
            <SectionLabel>If it’s too easy</SectionLabel>
            <GeneratedText>{dailyWin.content.adaptations.if_too_easy}</GeneratedText>
            <SectionLabel>If it’s too hard</SectionLabel>
            <GeneratedText>{dailyWin.content.adaptations.if_too_hard}</GeneratedText>
          </View>

          {dailyWin.has_feedback ? (
            <Card style={styles.closing}>
              <AppText variant="cardTitle">Reflected</AppText>
              <AppText variant="secondary">
                You already reported how this activity went.
              </AppText>
            </Card>
          ) : (
            <Card style={styles.closing}>
              <AppText variant="cardTitle">How did it go?</AppText>
              <AppText variant="secondary">
                A short reflection helps the next activity fit a little better.
              </AppText>
              <AppButton
                label="Reflect on this Win"
                onPress={() => router.push('/reflect')}
              />
            </Card>
          )}
          <LearningEngineDebugCard engine={dailyWin.learning_engine} />
        </Animated.View>
      ) : null}
    </>
  );
}

function SegmentBlock({ segment }: { segment: DailyWinSegment }) {
  return (
    <View style={styles.segment}>
      <PhaseBadge type={segment.type} />
      <GeneratedText variant="emphasized" style={styles.segmentTitle}>
        {segment.title}
      </GeneratedText>
      <AppText variant="caption">About {segment.minutes} minutes</AppText>
      {segment.steps.map((step) => (
        <GeneratedText key={step} style={styles.listItem}>
          {step}
        </GeneratedText>
      ))}
      <AppText variant="secondary" style={styles.parentRole}>
        Parent role: {segment.parent_role}
      </AppText>
    </View>
  );
}

function BriefBlock({ label, text }: { label: string; text: string }) {
  return (
    <View style={styles.briefItem}>
      <SectionLabel style={styles.briefLabel}>{label}</SectionLabel>
      <GeneratedText>{text}</GeneratedText>
    </View>
  );
}

function LearningEngineDebugCard({
  engine,
}: {
  engine: LearningEngineDebug | null | undefined;
}) {
  const [open, setOpen] = useState(false);
  if (!__DEV__ || !engine) {
    return null;
  }
  const blob = JSON.stringify(engine);
  if (blob.includes('"id"') || /[0-9a-f]{8}-[0-9a-f]{4}-/.test(blob)) {
    return null;
  }
  return (
    <Card tone="soft" style={styles.engineCard}>
      <TextButton
        label={open ? 'Hide learning engine' : 'Learning engine'}
        onPress={() => setOpen((value) => !value)}
      />
      {open ? (
        <View style={styles.engineBody}>
          <AppText variant="caption">Development only. Not shown in production.</AppText>
          <EngineRow label="Target" value={engine.target} />
          <EngineRow label="Mode" value={engine.mode} />
          <EngineRow label="Difficulty" value={engine.difficulty} />
          <EngineRow label="Scaffold" value={engine.scaffold} />
          <EngineRow label="Why" value={engine.why.join('\n')} />
          <EngineRow label="Assessment" value={engine.assessment} />
          <EngineRow label="Policy" value={engine.policy} />
        </View>
      ) : null}
    </Card>
  );
}

function EngineRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.engineRow}>
      <SectionLabel style={styles.briefLabel}>{label}</SectionLabel>
      <AppText variant="body">{value}</AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  meta: {
    marginTop: space.xs,
  },
  objective: {
    marginTop: space.sm,
  },
  changeCard: {
    marginTop: space.xl,
  },
  changeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: space.sm,
  },
  changeLabel: {
    marginTop: 0,
    marginBottom: 0,
  },
  changeBody: {
    color: colors.textPrimary,
  },
  briefing: {
    marginTop: space.xl,
    gap: space.sm,
  },
  briefIntro: {
    marginBottom: space.xs,
  },
  briefItem: {
    paddingTop: space.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderSubtle,
    gap: 4,
  },
  briefLabel: {
    marginTop: 0,
    marginBottom: 4,
  },
  materials: {
    marginTop: space.lg,
  },
  segment: {
    marginTop: space.xl,
    paddingTop: space.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderSubtle,
    gap: 6,
  },
  segmentTitle: {
    marginTop: 4,
  },
  listItem: {
    marginTop: 4,
  },
  parentRole: {
    marginTop: space.sm,
  },
  adaptBlock: {
    marginTop: space.xl,
    gap: space.sm,
  },
  checkBlock: {
    marginTop: space.xl,
    paddingTop: space.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderSubtle,
    gap: space.sm,
  },
  engineCard: {
    marginTop: space.xl,
  },
  engineBody: {
    marginTop: space.md,
    gap: space.sm,
  },
  engineRow: {
    gap: 4,
  },
  closing: {
    marginTop: space.xl,
  },
});
