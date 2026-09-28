import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Animated, ScrollView, StyleSheet, View } from 'react-native';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useParentPilotView } from '@/hooks/useParentPilotView';
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';
import { fetchDemoDailyWin, fetchLatestDemoDailyWin } from '@/lib/api/demo';
import { parentMessage } from '@/lib/api/parentErrors';
import type { DemoDailyWin, LearningEngineDebug } from '@/lib/api/types';
import { changedTodayCopy } from '@/lib/academicLoop';
import {
  academicResultLabel,
  difficultyLabel,
  persistenceLabel,
} from '@/lib/competency';
import { normalizeDisplayText } from '@/lib/displayNormalize';
import {
  cuesForSegment,
  DISPLAY_LIMITS,
  formatHistoryDate,
  hasVisibleText,
  materialsForDisplay,
  visibleLines,
} from '@/lib/productCopy';
import { buildSessionSteps, type SessionStep } from '@/lib/sessionSteps';
import { colors, motion, radius, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { Card } from '@/ui/Card';
import { CoachCue } from '@/ui/CoachCue';
import { Disclosure } from '@/ui/Disclosure';
import { EmptyState } from '@/ui/EmptyState';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { GeneratedText } from '@/ui/GeneratedText';
import { ResultMetric } from '@/ui/ResultMetric';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { SectionLabel } from '@/ui/SectionLabel';
import { SessionStepper } from '@/ui/SessionStepper';
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

export default function DailyWinScreen() {
  const params = useLocalSearchParams<{
    id?: string | string[];
    begin?: string | string[];
  }>();
  const requestedId = Array.isArray(params.id) ? params.id[0] : params.id;
  const beginNow =
    (Array.isArray(params.begin) ? params.begin[0] : params.begin) === '1';
  const [dailyWin, setDailyWin] = useState<DemoDailyWin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [started, setStarted] = useState(false);
  const loadedId = useRef<string | null>(null);
  const generationRef = useRef(0);

  const load = useCallback(
    (showLoading: boolean) => {
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
            setStarted(result.has_feedback || beginNow);
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
    },
    [beginNow, requestedId],
  );

  useFocusEffect(
    useCallback(() => {
      load(loadedId.current === null);
    }, [load]),
  );

  if (loading && !dailyWin) {
    return (
      <Screen scroll={false}>
        <ScreenLoading title="Daily Win" />
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
            body="Go home and start today’s Win."
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
        <ScreenLoading title="Daily Win" />
      </Screen>
    );
  }

  if (dailyWin.has_feedback && requestedId) {
    return (
      <Screen>
        <HistoryDetail win={dailyWin} />
      </Screen>
    );
  }

  return (
    <DailyWinSession
      key={dailyWin.id}
      dailyWin={dailyWin}
      started={started}
      onStart={() => setStarted(true)}
    />
  );
}

function HistoryDetail({ win }: { win: DemoDailyWin }) {
  const snapshot = win.result_snapshot;
  const date = formatHistoryDate(win.created_at);
  return (
    <>
      <AppText variant="caption">{date}</AppText>
      <GeneratedText variant="title">{win.title}</GeneratedText>
      <AppText variant="secondary" style={styles.meta}>
        {win.primary_skill_display_name}
      </AppText>
      <View style={styles.metrics}>
        <ResultMetric
          label="Result"
          value={academicResultLabel(snapshot?.academic_result)}
        />
        <ResultMetric label="Challenge" value={difficultyLabel(snapshot?.difficulty)} />
        <ResultMetric
          label="Persistence"
          value={persistenceLabel(snapshot?.setback_response)}
        />
      </View>
      {hasVisibleText(win.one_thing_to_improve) ? (
        <Card tone="plain" style={styles.block}>
          <SectionLabel style={styles.tightLabel}>Coach note</SectionLabel>
          <GeneratedText>{win.one_thing_to_improve ?? ''}</GeneratedText>
        </Card>
      ) : null}
    </>
  );
}

function DailyWinSession({
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
  const steps = useMemo(() => buildSessionSteps(dailyWin), [dailyWin]);
  const firstAction = steps.find((step) => step.kind !== 'mission')?.id ?? 'reflect';
  const [currentId, setCurrentId] = useState(started ? firstAction : 'mission');
  const [reveal] = useState(() => new Animated.Value(1));

  useEffect(() => {
    if (reduceMotion) {
      reveal.setValue(1);
      return;
    }
    reveal.setValue(0);
    Animated.timing(reveal, {
      toValue: 1,
      duration: motion.fast,
      useNativeDriver: true,
    }).start();
  }, [currentId, reduceMotion, reveal]);

  const current = steps.find((step) => step.id === currentId) ?? steps[0];
  const index = steps.findIndex((step) => step.id === currentId);
  const showFooter =
    started && current.kind !== 'mission' && current.kind !== 'reflect';

  const goNext = () => {
    const next = steps[index + 1];
    if (next) {
      setCurrentId(next.id);
    }
  };
  const goBack = () => {
    const prev = steps[index - 1];
    if (prev) {
      setCurrentId(prev.id);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['bottom', 'left', 'right']}>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={styles.scroll}
        style={styles.flex}>
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
          {started && current.kind !== 'mission' ? (
            <SessionStepper steps={steps} currentId={currentId} />
          ) : null}
          {current.kind === 'mission' ? (
            <MissionStep
              dailyWin={dailyWin}
              onStart={() => {
                onStart();
                setCurrentId(firstAction);
              }}
            />
          ) : null}
          {current.kind === 'learn' || current.kind === 'do' || current.kind === 'grow'
            ? (
              <ActionStep
                step={current}
                dailyWin={dailyWin}
              />
            )
            : null}
          {current.kind === 'bonus' ? <BonusStep dailyWin={dailyWin} /> : null}
          {current.kind === 'reflect' ? (
            <ReflectStep
              dailyWin={dailyWin}
              onReflect={() => router.push('/reflect')}
            />
          ) : null}
          <LearningEngineDebugCard engine={dailyWin.learning_engine} />
        </Animated.View>
      </ScrollView>
      {showFooter ? (
        <View style={styles.footer}>
          <View style={styles.footerBack}>
            {index > 0 ? (
              <TextButton label="Back" onPress={goBack} />
            ) : null}
          </View>
          <View style={styles.footerNext}>
            <AppButton label="Next" onPress={goNext} />
          </View>
        </View>
      ) : null}
    </SafeAreaView>
  );
}

function MissionStep({
  dailyWin,
  onStart,
}: {
  dailyWin: DemoDailyWin;
  onStart: () => void;
}) {
  const jobToday = visibleLines(dailyWin.coach_card, DISPLAY_LIMITS.jobBullets);
  const materials = materialsForDisplay(dailyWin.content.materials, MATERIAL_LABELS);
  const paperPencilOnly =
    materials.length > 0 &&
    materials.every((item) => item === 'Paper' || item === 'Pencil');
  const why = changedTodayCopy(dailyWin);
  return (
    <>
      <AppText variant="sectionLabel">Today</AppText>
      <GeneratedText variant="title">{dailyWin.title}</GeneratedText>
      <AppText variant="secondary" style={styles.meta}>
        {dailyWin.primary_skill_display_name} · ~{dailyWin.duration_minutes} min
      </AppText>
      {jobToday.length > 0 ? (
        <Card tone="highlight" style={styles.block}>
          <SectionLabel style={styles.tightLabel}>Your game plan</SectionLabel>
          {jobToday.map((item, index) => (
            <View key={item} style={styles.planRow}>
              <View style={styles.num}>
                <AppText variant="caption" style={styles.numText}>
                  {index + 1}
                </AppText>
              </View>
              <GeneratedText variant="emphasized" style={styles.planText}>
                {item}
              </GeneratedText>
            </View>
          ))}
        </Card>
      ) : null}
      {materials.length > 0 ? (
        <View style={styles.block}>
          <SectionLabel style={styles.tightLabel}>You’ll need</SectionLabel>
          <AppText variant="secondary">
            {paperPencilOnly ? 'Just paper and a pencil.' : materials.join(' · ')}
          </AppText>
        </View>
      ) : null}
      {why ? (
        <Disclosure label="Why this today?">
          <GeneratedText variant="body">{why}</GeneratedText>
        </Disclosure>
      ) : null}
      <AppButton label="Begin" onPress={onStart} />
    </>
  );
}

function ActionStep({
  step,
  dailyWin,
}: {
  step: SessionStep;
  dailyWin: DemoDailyWin;
}) {
  const segment = step.segment;
  const actions = visibleLines(segment?.steps);
  const cues = cuesForSegment(dailyWin.coach_cues, segment?.type ?? 'LEARN');
  const watch =
    step.kind === 'do' ? dailyWin.assessment?.what_to_check : null;
  return (
    <>
      <AppText variant="sectionLabel">{step.label}</AppText>
      {hasVisibleText(segment?.title) ? (
        <GeneratedText variant="title">{segment?.title ?? ''}</GeneratedText>
      ) : (
        <AppText variant="screenTitle">{step.label}</AppText>
      )}
      {segment ? (
        <AppText variant="caption">~{segment.minutes} min</AppText>
      ) : null}
      {actions.map((action, index) => (
        <View key={`${index}-${action}`} style={styles.actionRow}>
          <View style={styles.num}>
            <AppText variant="caption" style={styles.numText}>
              {index + 1}
            </AppText>
          </View>
          <GeneratedText
            variant={index === 0 ? 'emphasized' : 'body'}
            style={styles.planText}>
            {action}
          </GeneratedText>
        </View>
      ))}
      <CoachCue text={watch} />
      {cues.length > 0 || hasVisibleText(segment?.parent_role) ? (
        <Disclosure label="If needed">
          {cues.map((cue) => (
            <AppText key={`${cue.label}-${cue.text}`} variant="secondary">
              {normalizeDisplayText(cue.text)}
            </AppText>
          ))}
          {hasVisibleText(segment?.parent_role) ? (
            <AppText variant="secondary">{segment?.parent_role}</AppText>
          ) : null}
        </Disclosure>
      ) : null}
    </>
  );
}

function BonusStep({ dailyWin }: { dailyWin: DemoDailyWin }) {
  const bonus = dailyWin.bonus_challenge;
  if (!bonus) {
    return null;
  }
  return (
    <>
      <AppText variant="sectionLabel">Bonus</AppText>
      {hasVisibleText(bonus.title) ? (
        <GeneratedText variant="title">{bonus.title}</GeneratedText>
      ) : (
        <AppText variant="screenTitle">One more if you want it</AppText>
      )}
      <AppText variant="caption">~{bonus.minutes} min · optional</AppText>
      <GeneratedText style={styles.block}>{bonus.prompt}</GeneratedText>
    </>
  );
}

function ReflectStep({
  dailyWin,
  onReflect,
}: {
  dailyWin: DemoDailyWin;
  onReflect: () => void;
}) {
  if (dailyWin.has_feedback) {
    return (
      <Card>
        <AppText variant="cardTitle">Already reported</AppText>
        <AppText variant="secondary">You already saved how this Win went.</AppText>
      </Card>
    );
  }
  return (
    <Card>
      <AppText variant="cardTitle">How’d it go?</AppText>
      <AppText variant="secondary">
        About a minute. This is what shapes the next move.
      </AppText>
      <AppButton label="Save a reflection" onPress={onReflect} />
    </Card>
  );
}

function LearningEngineDebugCard({
  engine,
}: {
  engine: LearningEngineDebug | null | undefined;
}) {
  const [open, setOpen] = useState(false);
  const hide = useParentPilotView();
  if (__DEV__ === false || hide || !engine) {
    return null;
  }
  const blob = JSON.stringify(engine);
  if (blob.includes('"id"') || /[0-9a-f]{8}-[0-9a-f]{4}-/.test(blob)) {
    return null;
  }
  return (
    <Card tone="soft" style={styles.block}>
      <TextButton
        label={open ? 'Hide learning engine' : 'Learning engine'}
        onPress={() => setOpen((value) => !value)}
      />
      {open ? (
        <AppText variant="caption">Development only. Not shown in production.</AppText>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
  },
  flex: {
    flex: 1,
  },
  scroll: {
    paddingHorizontal: space.screenX,
    paddingTop: space.screenTop,
    paddingBottom: space.xl,
  },
  meta: {
    marginTop: space.xs,
    marginBottom: space.md,
  },
  block: {
    marginTop: space.lg,
  },
  tightLabel: {
    marginTop: 0,
  },
  planRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: space.sm,
    marginTop: space.sm,
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: space.sm,
    marginTop: space.md,
  },
  planText: {
    flex: 1,
  },
  num: {
    width: 24,
    height: 24,
    borderRadius: radius.chipPill,
    backgroundColor: colors.actionPrimarySoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  numText: {
    color: colors.actionPrimary,
    fontWeight: '700',
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: space.screenX,
    paddingTop: space.xs,
    paddingBottom: space.xs,
    backgroundColor: colors.background,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderSubtle,
    gap: space.sm,
  },
  footerBack: {
    flex: 1,
  },
  footerNext: {
    flex: 2,
  },
  metrics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: space.lg,
  },
});
