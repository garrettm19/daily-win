import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';

import { fetchDemoChildProfile } from '@/lib/api/demo';
import {
  PARENT_ERRORS,
  describeCaughtError,
  type ApiErrorKind,
} from '@/lib/api/parentErrors';
import type { DemoChildProfile } from '@/lib/api/types';
import { colors, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { SectionLabel } from '@/ui/SectionLabel';

export default function ProfileScreen() {
  const router = useRouter();
  const [profile, setProfile] = useState<DemoChildProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    void fetchDemoChildProfile()
      .then((next) => {
        setProfile(next);
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

  return (
    <Screen>
      {loading && !profile ? <ScreenLoading title="Loading profile" /> : null}
      {error ? (
        <ErrorCallout
          message={error}
          errorCode={errorCode}
          errorKind={errorKind}
          onRetry={load}
        />
      ) : null}
      {profile ? (
        <>
          <SectionLabel>About</SectionLabel>
          <AppText variant="display" style={styles.title}>
            {profile.child.nickname}
          </AppText>
          <AppText variant="secondary">
            Age {profile.baseline.age_years} • Grade {profile.baseline.grade}
          </AppText>
          <ProfileGroup title="Interests" values={profile.baseline.interests} />
          <ProfileGroup title="Strengths" values={profile.baseline.strengths} />
          <ProfileGroup
            title="Working on"
            values={profile.baseline.current_difficulties}
          />
          <View style={styles.group}>
            <SectionLabel>Goals</SectionLabel>
            {profile.goals.map((goal) => (
              <AppText key={goal.skill_code} variant="body">
                {goal.priority}. {goal.display_name}
              </AppText>
            ))}
          </View>
          <View style={styles.group}>
            <SectionLabel>What works</SectionLabel>
            <AppText variant="body">
              {profile.baseline.motivators.join(', ') || '—'}
            </AppText>
            <AppText variant="secondary">
              About {profile.baseline.preferred_activity_minutes} minutes
            </AppText>
          </View>
          <AppButton
            label="Edit profile"
            variant="secondary"
            onPress={() => router.push('/profile-edit')}
          />
        </>
      ) : null}
    </Screen>
  );
}

function ProfileGroup({ title, values }: { title: string; values: string[] }) {
  return (
    <View style={styles.group}>
      <SectionLabel>{title}</SectionLabel>
      <AppText variant="body">{values.join(', ') || '—'}</AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  title: {
    marginTop: space.xs,
    marginBottom: space.xs,
  },
  group: {
    marginTop: space.xl,
    gap: 6,
    paddingTop: space.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderSubtle,
  },
});
