import { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';

import { useHomeData } from '@/hooks/useHomeData';
import { ApiError } from '@/lib/api/client';
import { generateDemoDailyWinSafely, setupHayesProfile } from '@/lib/api/demo';
import {
  type ApiErrorKind,
  parentMessage,
} from '@/lib/api/parentErrors';
import { changedTodayCopy } from '@/lib/academicLoop';
import {
  academicResultLabel,
  independencePoints,
  nextMoveCopy,
} from '@/lib/competency';
import { homePresentationPhase, onePrimaryCtaLabel } from '@/lib/homePresentation';
import { firstWinFailed, generationStageCopy, homeWinPhase } from '@/lib/homeState';
import { formatFriendlyDate } from '@/lib/productCopy';
import { clearReflectionDraft } from '@/lib/reflectionDraft';
import type {
  DemoChildProfile,
  DemoDailyWin,
  DemoProgress,
  NextWinState,
} from '@/lib/api/types';
import { colors, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { BrandMark } from '@/ui/BrandMark';
import { Card } from '@/ui/Card';
import { DemoControls } from '@/ui/DemoControls';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { Icon } from '@/ui/Icon';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { SkillCard } from '@/ui/SkillCard';
import { StatusBadge } from '@/ui/StatusBadge';
import { TextButton } from '@/ui/TextButton';

const DEMO_COPY = 'Demo mode — use made-up information only.';

export default function Index() {
  const {
    session,
    profile,
    dailyWin,
    nextWin,
    progress,
    pendingReady,
    error,
    errorKind,
    errorCode,
    loading,
    retry,
    refresh,
    forgetDailyWin,
    rememberDailyWin,
  } = useHomeData();
  const router = useRouter();
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [generateErrorCode, setGenerateErrorCode] = useState<string | null>(null);
  const [generateErrorKind, setGenerateErrorKind] = useState<ApiErrorKind | null>(
    null,
  );
  const [resetNotice, setResetNotice] = useState<string | null>(null);
  const [hayesLoading, setHayesLoading] = useState(false);
  const [hayesError, setHayesError] = useState<string | null>(null);
  const [hayesErrorCode, setHayesErrorCode] = useState<string | null>(null);
  const [hayesErrorKind, setHayesErrorKind] = useState<ApiErrorKind | null>(null);
  const generateLock = useRef(false);
  const hayesLock = useRef(false);
  const noticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useFocusEffect(
    useCallback(() => {
      generateLock.current = false;
      hayesLock.current = false;
    }, []),
  );

  useEffect(() => {
    return () => {
      if (noticeTimer.current) {
        clearTimeout(noticeTimer.current);
      }
    };
  }, []);

  const showNotice = (message: string) => {
    setResetNotice(message);
    if (noticeTimer.current) {
      clearTimeout(noticeTimer.current);
    }
    noticeTimer.current = setTimeout(() => {
      setResetNotice(null);
      noticeTimer.current = null;
    }, 4000);
  };

  const openDailyWin = () => {
    router.push('/daily-win?begin=1');
  };

  const handleActivityResetSucceeded = () => {
    clearReflectionDraft();
    forgetDailyWin();
    setGenerateError(null);
    setGenerateErrorCode(null);
    setGenerateErrorKind(null);
    if (router.canDismiss()) {
      router.dismissAll();
    }
    refresh();
    showNotice('Activity history cleared. Profile is ready for a new Daily Win.');
  };

  const handleRestartSucceeded = () => {
    clearReflectionDraft();
    forgetDailyWin();
    setGenerateError(null);
    setGenerateErrorCode(null);
    setGenerateErrorKind(null);
    if (router.canDismiss()) {
      router.dismissAll();
    }
    refresh();
  };

  const handleHayes = () => {
    if (hayesLock.current || hayesLoading) {
      return;
    }
    hayesLock.current = true;
    setHayesLoading(true);
    setHayesError(null);
    setHayesErrorCode(null);
    setHayesErrorKind(null);
    void setupHayesProfile()
      .then(() => {
        router.replace('/guide');
      })
      .catch((caught: unknown) => {
        hayesLock.current = false;
        if (caught instanceof ApiError && caught.errorCode === 'already_configured') {
          refresh();
          return;
        }
        if (caught instanceof ApiError) {
          setHayesError(parentMessage('setup', caught.kind));
          setHayesErrorCode(caught.errorCode ?? null);
          setHayesErrorKind(caught.kind);
          return;
        }
        setHayesError(parentMessage('setup'));
        setHayesErrorKind('unavailable');
      })
      .finally(() => {
        setHayesLoading(false);
      });
  };

  const handleGenerate = () => {
    if (generateLock.current || generating) {
      return;
    }
    generateLock.current = true;
    setGenerating(true);
    setGenerateError(null);
    setGenerateErrorCode(null);
    setGenerateErrorKind(null);
    void generateDemoDailyWinSafely()
      .then((created) => {
        rememberDailyWin(created);
        router.push('/daily-win?begin=1');
      })
      .catch((caught: unknown) => {
        generateLock.current = false;
        if (caught instanceof ApiError && caught.errorCode === 'generation_in_progress') {
          refresh();
          return;
        }
        if (caught instanceof ApiError) {
          setGenerateError(parentMessage('generate', caught.kind));
          setGenerateErrorCode(caught.errorCode ?? null);
          setGenerateErrorKind(caught.kind);
          return;
        }
        setGenerateError(parentMessage('generate'));
        setGenerateErrorCode(null);
        setGenerateErrorKind('unavailable');
      })
      .finally(() => {
        setGenerating(false);
      });
  };

  const firstRun = !loading && session?.status === 'new';

  return (
    <Screen edges={['top', 'bottom', 'left', 'right']}>
      {loading && !session ? (
        <>
          <BrandMark />
          <ScreenLoading title="Daily Win" />
        </>
      ) : null}
      {!loading && error && !session ? (
        <FirstRun
          loading={hayesLoading}
          fingerprint={undefined}
          error={hayesError}
          errorCode={hayesErrorCode}
          errorKind={hayesErrorKind}
          loadError={error}
          loadErrorCode={errorCode}
          loadErrorKind={errorKind}
          onRetryLoad={retry}
          onHayes={handleHayes}
          onCustom={() => router.push('/setup')}
          onActivityResetSucceeded={handleActivityResetSucceeded}
          onRestartSucceeded={handleRestartSucceeded}
        />
      ) : null}
      {firstRun ? (
        <FirstRun
          loading={hayesLoading}
          fingerprint={session?.tester_fingerprint}
          error={hayesError}
          errorCode={hayesErrorCode}
          errorKind={hayesErrorKind}
          loadError={error}
          loadErrorCode={errorCode}
          loadErrorKind={errorKind}
          onRetryLoad={retry}
          onHayes={handleHayes}
          onCustom={() => router.push('/setup')}
          onActivityResetSucceeded={handleActivityResetSucceeded}
          onRestartSucceeded={handleRestartSucceeded}
        />
      ) : null}
      {profile ? (
        <ProfileHome
          profile={profile}
          dailyWin={dailyWin}
          nextWin={nextWin}
          progress={progress}
          pendingReady={pendingReady}
          generating={generating}
          generateError={generateError}
          generateErrorCode={generateErrorCode}
          generateErrorKind={generateErrorKind}
          loadError={error}
          loadErrorCode={errorCode}
          loadErrorKind={errorKind}
          onRetryLoad={retry}
          resetNotice={resetNotice}
          onGenerate={handleGenerate}
          onView={openDailyWin}
          onActivityResetSucceeded={handleActivityResetSucceeded}
          onRestartSucceeded={handleRestartSucceeded}
        />
      ) : null}
    </Screen>
  );
}

function FirstRun({
  loading,
  fingerprint,
  error,
  errorCode,
  errorKind,
  loadError,
  loadErrorCode,
  loadErrorKind,
  onRetryLoad,
  onHayes,
  onCustom,
  onActivityResetSucceeded,
  onRestartSucceeded,
}: {
  loading: boolean;
  fingerprint?: string;
  error: string | null;
  errorCode: string | null;
  errorKind: ApiErrorKind | null;
  loadError: string | null;
  loadErrorCode: string | null;
  loadErrorKind: ApiErrorKind | null;
  onRetryLoad: () => void;
  onHayes: () => void;
  onCustom: () => void;
  onActivityResetSucceeded: () => void;
  onRestartSucceeded: () => void;
}) {
  return (
    <>
      <BrandMark />
      <AppText variant="display" style={styles.heroTitle}>
        Daily Win
      </AppText>
      <AppText variant="body" style={styles.heroBody}>
        20 minutes. One challenge. Know exactly how to coach it.
      </AppText>
      <AppText variant="secondary" style={styles.heroSupport}>
        Built for parents who want to be more intentional with 20 minutes.
      </AppText>
      <AppText variant="caption" style={styles.heroCaption}>
        Daily Win gives you the plan. You bring the relationship.
      </AppText>
      {loadError ? (
        <ErrorCallout
          message={loadError}
          errorCode={loadErrorCode}
          errorKind={loadErrorKind}
          onRetry={onRetryLoad}
        />
      ) : null}
      {error ? (
        <ErrorCallout message={error} errorCode={errorCode} errorKind={errorKind} />
      ) : null}
      <AppButton
        label="Start with Hayes"
        onPress={onHayes}
        loading={loading}
        disabled={loading}
      />
      <AppButton
        label="Create a profile"
        variant="secondary"
        onPress={onCustom}
        disabled={loading}
      />
      <AppText variant="caption" style={styles.demoCopy}>
        {DEMO_COPY}
      </AppText>
      <DemoControls
        testerFingerprint={fingerprint}
        onActivityResetSucceeded={onActivityResetSucceeded}
        onRestartSucceeded={onRestartSucceeded}
      />
    </>
  );
}

function ProfileHome({
  profile,
  dailyWin,
  nextWin,
  progress,
  pendingReady,
  generating,
  generateError,
  generateErrorCode,
  generateErrorKind,
  loadError,
  loadErrorCode,
  loadErrorKind,
  onRetryLoad,
  resetNotice,
  onGenerate,
  onView,
  onActivityResetSucceeded,
  onRestartSucceeded,
}: {
  profile: DemoChildProfile;
  dailyWin: DemoDailyWin | null;
  nextWin: NextWinState | null;
  progress: DemoProgress | null;
  pendingReady: boolean;
  generating: boolean;
  generateError: string | null;
  generateErrorCode: string | null;
  generateErrorKind: ApiErrorKind | null;
  loadError: string | null;
  loadErrorCode: string | null;
  loadErrorKind: ApiErrorKind | null;
  onRetryLoad: () => void;
  resetNotice: string | null;
  onGenerate: () => void;
  onView: () => void;
  onActivityResetSucceeded: () => void;
  onRestartSucceeded: () => void;
}) {
  const router = useRouter();
  const phase = homePresentationPhase({
    presentedWin: dailyWin,
    latestWin: nextWin?.daily_win ?? null,
    preparationStatus: nextWin?.preparation_status,
    pendingReady,
  });
  const skills = (progress?.academic_skills ?? []).slice(0, 3);
  const snapshot = dailyWin?.has_feedback ? dailyWin.result_snapshot : null;
  const latestResult = snapshot
    ? academicResultLabel(snapshot.academic_result) ||
      progress?.academic_skills?.[0]?.recent_evidence
    : progress?.academic_skills?.[0]?.recent_evidence;
  const nextMove = nextMoveCopy({
    oneThing: dailyWin?.one_thing_to_improve,
    changedToday: dailyWin ? changedTodayCopy(dailyWin) : null,
    currentAdjustment: progress?.growth_skills?.[0]?.current_adjustment,
  });
  const dateLabel = formatFriendlyDate(new Date().toISOString());
  const momentum =
    phase === 'preparing_first' || phase === 'reflected_preparing_next'
      ? 'Preparing next'
      : phase === 'current_unreflected' || phase === 'next_ready'
        ? 'Ready today'
        : phase === 'next_ready_pending_presentation'
          ? 'Last session saved'
          : phase === 'prep_failed'
            ? 'Needs a retry'
            : 'Let’s go';

  return (
    <>
      <BrandMark />
      <AppText variant="display" style={styles.nickname}>
        {profile.child.nickname}
      </AppText>
      <AppText variant="secondary">
        {dateLabel} · Grade {formatGrade(profile.baseline.grade)}
      </AppText>
      <AppText variant="caption" style={styles.momentum}>
        {momentum}
      </AppText>
      {loadError ? (
        <ErrorCallout
          message={loadError}
          errorCode={loadErrorCode}
          errorKind={loadErrorKind}
          onRetry={onRetryLoad}
        />
      ) : null}

      <Card tone="highlight" style={styles.winCard}>
        <AppText variant="sectionLabel">Today</AppText>
        {resetNotice ? (
          <AppText variant="caption" style={styles.notice}>
            {resetNotice}
          </AppText>
        ) : null}
        <HomeWinCard
          dailyWin={dailyWin}
          nextWin={nextWin}
          pendingReady={pendingReady}
          generating={generating}
          generateError={generateError}
          generateErrorCode={generateErrorCode}
          generateErrorKind={generateErrorKind}
          onGenerate={onGenerate}
          onView={onView}
        />
      </Card>

      {skills.length > 0 ? (
        <View style={styles.section}>
          <AppText variant="sectionLabel">Progress</AppText>
          <ScrollSkills skills={skills} nextMove={nextMove} />
        </View>
      ) : null}

      {latestResult ? (
        <View style={styles.section}>
          <AppText variant="sectionLabel">Latest result</AppText>
          <AppText variant="cardTitle" style={styles.winTitle}>
            {progress?.academic_skills?.[0]?.skill_name ?? dailyWin?.primary_skill_display_name}
          </AppText>
          <AppText variant="secondary">{latestResult}</AppText>
        </View>
      ) : null}

      {nextMove && (phase === 'current_unreflected' || phase === 'next_ready') ? (
        <View style={styles.section}>
          <AppText variant="sectionLabel">Next move</AppText>
          <AppText variant="bodyEmphasized">{nextMove}</AppText>
        </View>
      ) : null}

      <View style={styles.navRow}>
        <NavLink
          label="Progress"
          icon="leaf-outline"
          onPress={() => router.push('/progress')}
        />
        <NavLink
          label="Week"
          icon="calendar-outline"
          onPress={() => router.push('/weekly-report')}
          accessibilityLabel="This week"
        />
        <NavLink
          label="History"
          icon="time-outline"
          onPress={() => router.push('/history')}
        />
        <NavLink
          label="Profile"
          icon="person-outline"
          onPress={() => router.push('/profile')}
        />
      </View>

      <DemoControls
        disabled={generating}
        testerFingerprint={profile.tester_fingerprint}
        onActivityResetSucceeded={onActivityResetSucceeded}
        onRestartSucceeded={onRestartSucceeded}
      />
    </>
  );
}

function ScrollSkills({
  skills,
  nextMove,
}: {
  skills: NonNullable<DemoProgress['academic_skills']>;
  nextMove: string | null;
}) {
  return (
    <View style={styles.skillRow}>
      {skills.map((skill, index) => (
        <SkillCard
          key={`${skill.domain_label}-${skill.skill_name}`}
          skill={skill}
          points={independencePoints(skill)}
          nextMove={index === 0 ? nextMove : null}
        />
      ))}
    </View>
  );
}

function HomeWinCard({
  dailyWin,
  nextWin,
  pendingReady,
  generating,
  generateError,
  generateErrorCode,
  generateErrorKind,
  onGenerate,
  onView,
}: {
  dailyWin: DemoDailyWin | null;
  nextWin: NextWinState | null;
  pendingReady: boolean;
  generating: boolean;
  generateError: string | null;
  generateErrorCode: string | null;
  generateErrorKind: ApiErrorKind | null;
  onGenerate: () => void;
  onView: () => void;
}) {
  const phase = homeWinPhase(
    dailyWin,
    pendingReady ? (dailyWin ? 'ready' : nextWin?.preparation_status) : nextWin?.preparation_status,
  );
  const ctaPhase = homePresentationPhase({
    presentedWin: dailyWin,
    latestWin: nextWin?.daily_win ?? null,
    preparationStatus: nextWin?.preparation_status,
    pendingReady,
  });
  const primary = onePrimaryCtaLabel(ctaPhase);

  if (generating || phase === 'preparing') {
    const focus = nextWin?.focus_preview;
    return (
      <>
        {focus ? (
          <AppText variant="cardTitle" style={styles.winTitle}>
            {focus}
          </AppText>
        ) : null}
        <AppText variant={focus ? 'secondary' : 'cardTitle'} style={styles.winBody}>
          {generationStageCopy()}
        </AppText>
        <AppText variant="caption">You can leave. It will be here when you come back.</AppText>
      </>
    );
  }

  if (phase === 'failed') {
    const invalidated = nextWin?.preparation_status === 'invalidated';
    const firstFail = firstWinFailed(nextWin, dailyWin !== null);
    return (
      <>
        <AppText variant="cardTitle" style={styles.winTitle}>
          {invalidated
            ? 'Rebuilding today’s plan'
            : firstFail
              ? "Couldn't prepare today's Win."
              : 'Today’s Win is not ready yet'}
        </AppText>
        <AppText variant="secondary" style={styles.winBody}>
          {invalidated
            ? 'Your profile update is saved. Daily Win is making a new plan from it.'
            : firstFail
              ? 'Try again when you are ready.'
              : 'Your last reflection was saved. Create today’s Win when you are ready.'}
        </AppText>
        {generateError ? (
          <ErrorCallout
            message={generateError}
            errorCode={generateErrorCode}
            errorKind={generateErrorKind}
          />
        ) : null}
        <AppButton label={primary ?? 'Try again'} onPress={onGenerate} />
      </>
    );
  }

  if (phase === 'none') {
    return (
      <>
        <AppText variant="cardTitle" style={styles.winTitle}>
          {nextWin?.focus_preview ?? 'Ready for today’s Win?'}
        </AppText>
        <AppText variant="secondary" style={styles.winBody}>
          One short challenge. You’ll know the job before you start.
        </AppText>
        {generateError ? (
          <ErrorCallout
            message={generateError}
            errorCode={generateErrorCode}
            errorKind={generateErrorKind}
          />
        ) : null}
        <AppButton label={primary ?? "Create today's Win"} onPress={onGenerate} />
      </>
    );
  }

  if (dailyWin === null) {
    return null;
  }

  if (phase === 'reflection_pending') {
    return (
      <>
        <AppText variant="cardTitle" style={styles.winTitle}>
          {dailyWin.title}
        </AppText>
        <AppText variant="secondary" style={styles.winBody}>
          {dailyWin.primary_skill_display_name} · ~{dailyWin.duration_minutes} min
        </AppText>
        <AppButton label={primary ?? 'Start Daily Win'} onPress={onView} />
      </>
    );
  }

  return (
    <>
      <AppText variant="cardTitle" style={styles.winTitle}>
        {dailyWin.title}
      </AppText>
      <StatusBadge label="Saved" tone="win" />
      <AppText variant="secondary" style={styles.winBody}>
        {pendingReady
          ? 'Next Win is ready when you come back to this screen.'
          : 'Saved. Next Win is preparing. You can close the app.'}
      </AppText>
      <TextButton label="View last Win" onPress={onView} />
    </>
  );
}

function NavLink({
  label,
  icon,
  onPress,
  accessibilityLabel,
}: {
  label: string;
  icon: 'person-outline' | 'leaf-outline' | 'time-outline' | 'calendar-outline';
  onPress: () => void;
  accessibilityLabel?: string;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      onPress={onPress}
      style={({ pressed }) => [styles.navLink, pressed && styles.navPressed]}>
      <Icon name={icon} size={18} color={colors.actionPrimary} />
      <AppText variant="caption" style={styles.navLabel}>
        {label}
      </AppText>
    </Pressable>
  );
}

function formatGrade(grade: string): string {
  if (grade === 'K') {
    return 'K';
  }
  return grade;
}

const styles = StyleSheet.create({
  heroTitle: {
    marginTop: space.md,
  },
  heroBody: {
    marginTop: space.md,
  },
  heroSupport: {
    marginTop: space.xs,
  },
  heroCaption: {
    marginTop: space.sm,
    marginBottom: space.sm,
  },
  demoCopy: {
    marginTop: space.lg,
  },
  nickname: {
    marginTop: space.sm,
  },
  momentum: {
    marginTop: space.xxs,
    marginBottom: space.sm,
  },
  winCard: {
    marginTop: space.xl,
  },
  section: {
    marginTop: space.xl,
    gap: space.xs,
  },
  skillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: space.sm,
    marginTop: space.sm,
  },
  winTitle: {
    marginTop: space.sm,
  },
  jobLabel: {
    marginTop: space.md,
  },
  winBody: {
    marginTop: space.xs,
    marginBottom: space.sm,
  },
  notice: {
    marginTop: space.xs,
    color: colors.actionPrimary,
  },
  navRow: {
    marginTop: space.xl,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: space.sm,
  },
  navLink: {
    minHeight: 44,
    minWidth: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  navPressed: {
    opacity: 0.7,
  },
  navLabel: {
    color: colors.actionPrimary,
    fontWeight: '600',
  },
});
