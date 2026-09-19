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
import { homeWinPhase } from '@/lib/homeState';
import { clearReflectionDraft } from '@/lib/reflectionDraft';
import type {
  DemoChildProfile,
  DemoDailyWin,
} from '@/lib/api/types';
import { colors, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { Card } from '@/ui/Card';
import { DemoControls } from '@/ui/DemoControls';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { Icon } from '@/ui/Icon';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { StatusBadge } from '@/ui/StatusBadge';
import { TextButton } from '@/ui/TextButton';

const DEMO_COPY = 'Demo mode — use made-up information only.';

export default function Index() {
  const {
    session,
    profile,
    dailyWin,
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
    router.push('/daily-win');
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
        refresh();
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
        router.push('/daily-win');
      })
      .catch((caught: unknown) => {
        generateLock.current = false;
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
          <ScreenLoading title="Loading Daily Win" />
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

function BrandMark() {
  return (
    <View style={styles.brandRow}>
      <Icon name="sparkles" size={16} color={colors.highlight} />
      <AppText variant="sectionLabel">Daily Win</AppText>
    </View>
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
      <AppText variant="display" style={styles.heroTitle}>
        Daily Win
      </AppText>
      <AppText variant="body" style={styles.heroBody}>
        One personalized thing to do with your child today.
      </AppText>
      <AppText variant="secondary" style={styles.heroSupport}>
        It learns from what happens and makes the next Win better.
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
        label="Try the Hayes demo"
        onPress={onHayes}
        loading={loading}
        disabled={loading}
      />
      <AppButton
        label="Create a demo profile"
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
  const focusGoal = profile.goals[0];

  return (
    <>
      <BrandMark />
      <AppText variant="display" style={styles.nickname}>
        {profile.child.nickname}
      </AppText>
      <AppText variant="secondary">
        Age {profile.baseline.age_years} • Grade {formatGrade(profile.baseline.grade)}
      </AppText>
      {focusGoal ? (
        <AppText variant="caption" style={styles.focusLine}>
          Today’s focus: {focusGoal.display_name}
        </AppText>
      ) : null}
      {loadError ? (
        <ErrorCallout
          message={loadError}
          errorCode={loadErrorCode}
          errorKind={loadErrorKind}
          onRetry={onRetryLoad}
        />
      ) : null}

      <Card tone="highlight" style={styles.winCard}>
        <AppText variant="sectionLabel">
          {dailyWin ? 'Today’s Win' : 'Ready for today’s Win?'}
        </AppText>
        {resetNotice ? (
          <AppText variant="caption" style={styles.notice}>
            {resetNotice}
          </AppText>
        ) : null}
        <HomeWinCard
          profile={profile}
          dailyWin={dailyWin}
          generating={generating}
          generateError={generateError}
          generateErrorCode={generateErrorCode}
          generateErrorKind={generateErrorKind}
          onGenerate={onGenerate}
          onView={onView}
        />
      </Card>

      <View style={styles.navRow}>
        <NavLink
          label="Profile"
          icon="person-outline"
          onPress={() => router.push('/profile')}
        />
        <NavLink
          label="Progress"
          icon="leaf-outline"
          onPress={() => router.push('/progress')}
        />
        <NavLink
          label="History"
          icon="time-outline"
          onPress={() => router.push('/history')}
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

function HomeWinCard({
  profile,
  dailyWin,
  generating,
  generateError,
  generateErrorCode,
  generateErrorKind,
  onGenerate,
  onView,
}: {
  profile: DemoChildProfile;
  dailyWin: DemoDailyWin | null;
  generating: boolean;
  generateError: string | null;
  generateErrorCode: string | null;
  generateErrorKind: ApiErrorKind | null;
  onGenerate: () => void;
  onView: () => void;
}) {
  const phase = homeWinPhase(dailyWin);
  const nickname = profile.child.nickname;

  if (generating) {
    return (
      <ScreenLoading
        title={`Designing ${nickname}'s Daily Win…`}
        body="Creating one short activity for you to do together."
        supporting
      />
    );
  }

  if (phase === 'none') {
    return (
      <>
        <AppText variant="cardTitle" style={styles.winTitle}>
          Ready for today’s Win?
        </AppText>
        <AppText variant="secondary" style={styles.winBody}>
          One short activity designed from what you reported.
        </AppText>
        {generateError ? (
          <ErrorCallout
            message={generateError}
            errorCode={generateErrorCode}
            errorKind={generateErrorKind}
          />
        ) : null}
        <AppButton label="Generate today’s Daily Win" onPress={onGenerate} />
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
          {dailyWin.primary_skill_display_name} • About {dailyWin.duration_minutes}{' '}
          minutes
        </AppText>
        <StatusBadge label="Reflection pending" tone="pending" />
        <AppButton label="View Daily Win" onPress={onView} />
      </>
    );
  }

  return (
    <>
      <AppText variant="cardTitle" style={styles.winTitle}>
        {dailyWin.title}
      </AppText>
      <StatusBadge label="Completed" tone="win" />
      {generateError ? (
        <ErrorCallout
          message={generateError}
          errorCode={generateErrorCode}
          errorKind={generateErrorKind}
        />
      ) : null}
      <AppButton
        label={`Generate ${nickname}'s next Daily Win`}
        onPress={onGenerate}
      />
      <TextButton label="View completed Win" onPress={onView} />
    </>
  );
}

function NavLink({
  label,
  icon,
  onPress,
}: {
  label: string;
  icon: 'person-outline' | 'leaf-outline' | 'time-outline';
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
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
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  heroTitle: {
    marginTop: space.md,
  },
  heroBody: {
    marginTop: space.md,
  },
  heroSupport: {
    marginTop: space.xs,
  },
  demoCopy: {
    marginTop: space.lg,
  },
  nickname: {
    marginTop: space.sm,
  },
  focusLine: {
    marginTop: space.xs,
  },
  winCard: {
    marginTop: space.xl,
  },
  winTitle: {
    marginTop: space.sm,
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
