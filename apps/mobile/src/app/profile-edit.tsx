import { useCallback, useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';

import { ApiError } from '@/lib/api/client';
import {
  fetchDemoChildProfile,
  fetchOnboardingCatalog,
  updateDemoProfile,
} from '@/lib/api/demo';
import { parentMessage, type ApiErrorKind } from '@/lib/api/parentErrors';
import type { DemoChildProfile, DemoOnboardingCatalog } from '@/lib/api/types';
import { space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { ChoiceChip } from '@/ui/ChoiceChip';
import { ChipPicker } from '@/ui/ChipPicker';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { SectionLabel } from '@/ui/SectionLabel';

export default function ProfileEditScreen() {
  const router = useRouter();
  const [catalog, setCatalog] = useState<DemoOnboardingCatalog | null>(null);
  const [profile, setProfile] = useState<DemoChildProfile | null>(null);
  const [interests, setInterests] = useState<string[]>([]);
  const [strengths, setStrengths] = useState<string[]>([]);
  const [difficulties, setDifficulties] = useState<string[]>([]);
  const [response, setResponse] = useState('');
  const [goalCodes, setGoalCodes] = useState<string[]>([]);
  const [primary, setPrimary] = useState('');
  const [motivators, setMotivators] = useState<string[]>([]);
  const [minutes, setMinutes] = useState(20);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const lock = useRef(false);

  const load = useCallback(() => {
    void Promise.all([fetchOnboardingCatalog(), fetchDemoChildProfile()])
      .then(([nextCatalog, nextProfile]) => {
        setCatalog(nextCatalog);
        setProfile(nextProfile);
        setInterests(nextProfile.baseline.interests);
        setStrengths(nextProfile.baseline.strengths);
        setDifficulties(nextProfile.baseline.current_difficulties);
        setResponse(nextProfile.baseline.response_to_difficulty ?? '');
        setGoalCodes(nextProfile.goals.map((goal) => goal.skill_code));
        setPrimary(nextProfile.goals[0]?.skill_code ?? '');
        setMotivators(nextProfile.baseline.motivators);
        setMinutes(nextProfile.baseline.preferred_activity_minutes);
        setError(null);
        setErrorCode(null);
        setErrorKind(null);
      })
      .catch((caught: unknown) => {
        setError(parentMessage('load'));
        if (caught instanceof ApiError) {
          setErrorCode(caught.errorCode ?? null);
          setErrorKind(caught.kind);
        } else {
          setErrorKind('unavailable');
        }
      })
      .finally(() => setLoading(false));
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const save = () => {
    if (lock.current || saving) {
      return;
    }
    lock.current = true;
    setSaving(true);
    setError(null);
    setErrorCode(null);
    setErrorKind(null);
    void updateDemoProfile({
      interests,
      strengths,
      current_difficulties: difficulties,
      response_to_difficulty: response,
      goal_codes: goalCodes,
      primary_goal_code: primary,
      motivators,
      preferred_activity_minutes: minutes,
    })
      .then(() => router.back())
      .catch((caught: unknown) => {
        lock.current = false;
        if (caught instanceof ApiError) {
          setError(parentMessage('saveProfile', caught.kind));
          setErrorCode(caught.errorCode ?? null);
          setErrorKind(caught.kind);
          return;
        }
        setError(parentMessage('saveProfile'));
        setErrorKind('unavailable');
      })
      .finally(() => setSaving(false));
  };

  const maxGoals = catalog?.max_goals ?? 3;
  const canSave =
    interests.length > 0 &&
    strengths.length > 0 &&
    difficulties.length > 0 &&
    response.length > 0 &&
    goalCodes.length >= 2 &&
    goalCodes.length <= maxGoals &&
    goalCodes.includes(primary) &&
    motivators.length > 0;

  return (
    <Screen keyboard>
      {loading && !profile ? <ScreenLoading title="Loading profile" /> : null}
      {error && !profile ? (
        <ErrorCallout
          message={error}
          errorCode={errorCode}
          errorKind={errorKind}
          onRetry={load}
        />
      ) : null}
      {profile ? (
        <>
          <AppText variant="screenTitle">Edit {profile.child.nickname}</AppText>
          <AppText variant="secondary" style={styles.hint}>
            Changes affect future Daily Wins only. Past activities stay as they were.
          </AppText>
          <SectionLabel>Interests</SectionLabel>
          <ChipPicker
            options={unique([...(catalog?.interest_suggestions ?? []), ...interests])}
            selected={interests}
            max={catalog?.max_interests ?? 5}
            onToggle={(value) =>
              setInterests(toggle(interests, value, catalog?.max_interests ?? 5))
            }
          />
          <SectionLabel>Things that feel easier</SectionLabel>
          <ChipPicker
            options={unique([...(catalog?.strength_suggestions ?? []), ...strengths])}
            selected={strengths}
            max={catalog?.max_strengths ?? 5}
            onToggle={(value) =>
              setStrengths(toggle(strengths, value, catalog?.max_strengths ?? 5))
            }
          />
          <SectionLabel>Things that feel harder</SectionLabel>
          <ChipPicker
            options={unique([
              ...(catalog?.difficulty_suggestions ?? []),
              ...difficulties,
            ])}
            selected={difficulties}
            max={catalog?.max_difficulties ?? 5}
            onToggle={(value) =>
              setDifficulties(
                toggle(difficulties, value, catalog?.max_difficulties ?? 5),
              )
            }
          />
          <SectionLabel>When something is difficult</SectionLabel>
          <View style={styles.stack}>
            {(catalog?.response_options ?? []).map((option) => (
              <ChoiceChip
                key={option}
                label={option}
                selected={response === option}
                onPress={() => setResponse(option)}
                block
              />
            ))}
          </View>
          <SectionLabel>Goals · 2 or 3</SectionLabel>
          <AppText variant="caption" style={styles.hint}>
            #1 gets the strongest preference, but Daily Win will still rotate other
            active goals.
          </AppText>
          <View style={styles.stack}>
            {(catalog?.goals ?? []).map((goal) => (
              <ChoiceChip
                key={goal.code}
                label={goal.label}
                selected={goalCodes.includes(goal.code)}
                onPress={() => {
                  const next = toggle(goalCodes, goal.code, maxGoals);
                  setGoalCodes(next);
                  if (!next.includes(primary)) {
                    setPrimary('');
                  }
                }}
                block
              />
            ))}
          </View>
          {goalCodes.length >= 2 ? (
            <>
              <SectionLabel>Which is #1 Main focus?</SectionLabel>
              <View style={styles.stack}>
                {goalCodes.map((code) => {
                  const item = catalog?.goals.find((goal) => goal.code === code);
                  return (
                    <ChoiceChip
                      key={code}
                      label={item?.label ?? 'Goal'}
                      selected={primary === code}
                      onPress={() => setPrimary(code)}
                      block
                    />
                  );
                })}
              </View>
            </>
          ) : null}
          <SectionLabel>Motivators</SectionLabel>
          <ChipPicker
            options={unique([
              ...(catalog?.motivator_suggestions ?? []),
              ...motivators,
            ])}
            selected={motivators}
            max={catalog?.max_motivators ?? 4}
            onToggle={(value) =>
              setMotivators(toggle(motivators, value, catalog?.max_motivators ?? 4))
            }
          />
          <SectionLabel>Preferred length</SectionLabel>
          <AppText variant="caption">About how long — not a stopwatch.</AppText>
          <View style={styles.row}>
            {(catalog?.durations ?? [10, 15, 20, 25]).map((value) => (
              <ChoiceChip
                key={value}
                label={`About ${value} min`}
                selected={minutes === value}
                onPress={() => setMinutes(value)}
              />
            ))}
          </View>
          {error && profile ? (
            <ErrorCallout
              message={error}
              errorCode={errorCode}
              errorKind={errorKind}
            />
          ) : null}
          <AppButton
            label="Save"
            onPress={save}
            disabled={!canSave || saving}
            loading={saving}
          />
        </>
      ) : null}
    </Screen>
  );
}

function toggle(values: string[], value: string, max: number): string[] {
  if (values.includes(value)) {
    return values.filter((item) => item !== value);
  }
  if (values.length >= max) {
    return values;
  }
  return [...values, value];
}

function unique(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    const key = value.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(value);
  }
  return result;
}

const styles = StyleSheet.create({
  hint: {
    marginTop: space.xs,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  stack: {
    gap: 8,
  },
});
