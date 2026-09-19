import { useEffect, useRef, useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
import { useRouter } from 'expo-router';

import { ApiError } from '@/lib/api/client';
import { fetchOnboardingCatalog, setupCustomProfile } from '@/lib/api/demo';
import { parentMessage, type ApiErrorKind } from '@/lib/api/parentErrors';
import { clampText, TEXT_LIMITS } from '@/lib/textLimits';
import type { DemoOnboardingCatalog } from '@/lib/api/types';
import { colors, radius, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { ChoiceChip } from '@/ui/ChoiceChip';
import { ChipPicker } from '@/ui/ChipPicker';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { Screen } from '@/ui/Screen';
import { SectionLabel } from '@/ui/SectionLabel';
import { TextButton } from '@/ui/TextButton';

const DEMO_COPY = 'Demo mode — use made-up information only.';

type Draft = {
  nickname: string;
  ageYears: string;
  grade: string;
  interests: string[];
  strengths: string[];
  difficulties: string[];
  response: string;
  goalCodes: string[];
  primaryGoalCode: string;
  motivators: string[];
  minutes: number | null;
  customInterest: string;
  customStrength: string;
  customDifficulty: string;
};

const EMPTY: Draft = {
  nickname: '',
  ageYears: '7',
  grade: '1',
  interests: [],
  strengths: [],
  difficulties: [],
  response: '',
  goalCodes: [],
  primaryGoalCode: '',
  motivators: [],
  minutes: 20,
  customInterest: '',
  customStrength: '',
  customDifficulty: '',
};

export default function SetupScreen() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [catalog, setCatalog] = useState<DemoOnboardingCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const submitLock = useRef(false);

  const loadCatalog = () => {
    void fetchOnboardingCatalog()
      .then((next) => {
        setCatalog(next);
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
      });
  };

  useEffect(() => {
    let cancelled = false;
    void fetchOnboardingCatalog()
      .then((next) => {
        if (!cancelled) {
          setCatalog(next);
        }
      })
      .catch((caught: unknown) => {
        if (cancelled) {
          return;
        }
        setError(parentMessage('load'));
        if (caught instanceof ApiError) {
          setErrorCode(caught.errorCode ?? null);
          setErrorKind(caught.kind);
        } else {
          setErrorKind('unavailable');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const total = 5;
  const canContinue = stepIsValid(step, draft);

  const goNext = () => {
    setError(null);
    if (step < 5) {
      setStep(step + 1);
      return;
    }
    if (submitLock.current || submitting || catalog === null) {
      return;
    }
    const age = Number.parseInt(draft.ageYears, 10);
    if (Number.isNaN(age) || age < 5 || age > 9) {
      setError('Age must be between 5 and 9.');
      return;
    }
    submitLock.current = true;
    setSubmitting(true);
    void setupCustomProfile({
      nickname: draft.nickname.trim(),
      age_years: age,
      grade: draft.grade,
      interests: draft.interests,
      strengths: draft.strengths,
      current_difficulties: draft.difficulties,
      response_to_difficulty: draft.response,
      goal_codes: draft.goalCodes,
      primary_goal_code: draft.primaryGoalCode,
      motivators: draft.motivators,
      preferred_activity_minutes: draft.minutes ?? 20,
    })
      .then(() => {
        router.replace('/');
      })
      .catch((caught: unknown) => {
        submitLock.current = false;
        if (caught instanceof ApiError) {
          setError(parentMessage('saveProfile', caught.kind));
          setErrorCode(caught.errorCode ?? null);
          setErrorKind(caught.kind);
          return;
        }
        setError(parentMessage('saveProfile'));
        setErrorKind('unavailable');
      })
      .finally(() => {
        setSubmitting(false);
      });
  };

  return (
    <Screen keyboard>
          {step > 1 ? (
            <TextButton
              label="Back"
              disabled={submitting}
              onPress={() => {
                setError(null);
                setStep(step - 1);
              }}
            />
          ) : null}
          <AppText variant="caption">Step {step} of {total}</AppText>
          <View
            style={styles.track}
            accessibilityRole="progressbar"
            accessibilityValue={{ min: 1, max: total, now: step }}
            accessibilityLabel={`Step ${step} of ${total}`}>
            <View style={[styles.fill, { width: `${(step / total) * 100}%` }]} />
          </View>
          {step === 1 ? (
            <AboutStep draft={draft} setDraft={setDraft} catalog={catalog} />
          ) : null}
          {step === 2 ? (
            <EnjoyStep draft={draft} setDraft={setDraft} catalog={catalog} />
          ) : null}
          {step === 3 ? (
            <HarderStep draft={draft} setDraft={setDraft} catalog={catalog} />
          ) : null}
          {step === 4 ? (
            <GoalsStep draft={draft} setDraft={setDraft} catalog={catalog} />
          ) : null}
          {step === 5 ? (
            <WorksStep draft={draft} setDraft={setDraft} catalog={catalog} />
          ) : null}
          {error ? (
            <ErrorCallout
              message={error}
              errorCode={errorCode}
              errorKind={errorKind}
            />
          ) : null}
          {catalog === null && error ? (
            <AppButton label="Retry" variant="secondary" onPress={loadCatalog} />
          ) : null}
          <AppButton
            label={step === 5 ? 'Create demo profile' : 'Next'}
            onPress={goNext}
            disabled={!canContinue || submitting}
            loading={submitting}
          />
          <AppText variant="caption" style={styles.demoCopy}>
            {DEMO_COPY}
          </AppText>
    </Screen>
  );
}

function AboutStep({
  draft,
  setDraft,
  catalog,
}: {
  draft: Draft;
  setDraft: (next: Draft) => void;
  catalog: DemoOnboardingCatalog | null;
}) {
  return (
    <>
      <AppText variant="screenTitle" style={styles.stepTitle}>About this child</AppText>
      <AppText variant="secondary">Use a fictional nickname in demo mode.</AppText>
      <SectionLabel>Nickname</SectionLabel>
      <TextInput
        accessibilityLabel="Nickname"
        value={draft.nickname}
        onChangeText={(nickname) =>
          setDraft({ ...draft, nickname: clampText(nickname, TEXT_LIMITS.nickname) })
        }
        placeholder="A made-up nickname"
        placeholderTextColor={colors.textSecondary}
        maxLength={TEXT_LIMITS.nickname}
        autoCapitalize="words"
        returnKeyType="done"
        blurOnSubmit
        style={styles.input}
      />
      <SectionLabel>Age</SectionLabel>
      <View style={styles.row}>
        {['5', '6', '7', '8', '9'].map((age) => (
          <ChoiceChip
            key={age}
            label={age}
            selected={draft.ageYears === age}
            onPress={() => setDraft({ ...draft, ageYears: age })}
          />
        ))}
      </View>
      <SectionLabel>Grade</SectionLabel>
      <View style={styles.row}>
        {(catalog?.grades ?? []).map((grade) => (
          <ChoiceChip
            key={grade.code}
            label={grade.label}
            selected={draft.grade === grade.code}
            onPress={() => setDraft({ ...draft, grade: grade.code })}
          />
        ))}
      </View>
    </>
  );
}

function EnjoyStep({
  draft,
  setDraft,
  catalog,
}: {
  draft: Draft;
  setDraft: (next: Draft) => void;
  catalog: DemoOnboardingCatalog | null;
}) {
  return (
    <>
      <AppText variant="screenTitle" style={styles.stepTitle}>What they enjoy / do well</AppText>
      <SectionLabel>Interests · up to 5</SectionLabel>
      <ChipPicker
        options={mergeOptions(catalog?.interest_suggestions ?? [], draft.interests)}
        selected={draft.interests}
        max={catalog?.max_interests ?? 5}
        onToggle={(value) =>
          setDraft({
            ...draft,
            interests: toggle(draft.interests, value, catalog?.max_interests ?? 5),
          })
        }
      />
      <AddCustom
        value={draft.customInterest}
        onChange={(customInterest) => setDraft({ ...draft, customInterest })}
        onAdd={() => {
          const next = toggle(
            draft.interests,
            draft.customInterest.trim(),
            catalog?.max_interests ?? 5,
          );
          setDraft({ ...draft, interests: next, customInterest: '' });
        }}
      />
      <SectionLabel>Strengths · up to 5</SectionLabel>
      <ChipPicker
        options={mergeOptions(catalog?.strength_suggestions ?? [], draft.strengths)}
        selected={draft.strengths}
        max={catalog?.max_strengths ?? 5}
        onToggle={(value) =>
          setDraft({
            ...draft,
            strengths: toggle(draft.strengths, value, catalog?.max_strengths ?? 5),
          })
        }
      />
      <AddCustom
        value={draft.customStrength}
        onChange={(customStrength) => setDraft({ ...draft, customStrength })}
        onAdd={() => {
          const next = toggle(
            draft.strengths,
            draft.customStrength.trim(),
            catalog?.max_strengths ?? 5,
          );
          setDraft({ ...draft, strengths: next, customStrength: '' });
        }}
      />
    </>
  );
}

function HarderStep({
  draft,
  setDraft,
  catalog,
}: {
  draft: Draft;
  setDraft: (next: Draft) => void;
  catalog: DemoOnboardingCatalog | null;
}) {
  return (
    <>
      <AppText variant="screenTitle" style={styles.stepTitle}>What is harder</AppText>
      <AppText variant="secondary">Parent-reported only. Not a diagnosis.</AppText>
      <SectionLabel>Things that are harder · up to 5</SectionLabel>
      <ChipPicker
        options={mergeOptions(
          catalog?.difficulty_suggestions ?? [],
          draft.difficulties,
        )}
        selected={draft.difficulties}
        max={catalog?.max_difficulties ?? 5}
        onToggle={(value) =>
          setDraft({
            ...draft,
            difficulties: toggle(
              draft.difficulties,
              value,
              catalog?.max_difficulties ?? 5,
            ),
          })
        }
      />
      <AddCustom
        value={draft.customDifficulty}
        onChange={(customDifficulty) => setDraft({ ...draft, customDifficulty })}
        onAdd={() => {
          const next = toggle(
            draft.difficulties,
            draft.customDifficulty.trim(),
            catalog?.max_difficulties ?? 5,
          );
          setDraft({ ...draft, difficulties: next, customDifficulty: '' });
        }}
      />
      <SectionLabel>When something is difficult</SectionLabel>
      <View style={styles.stack}>
        {(catalog?.response_options ?? []).map((option) => (
          <ChoiceChip
            key={option}
            label={option}
            selected={draft.response === option}
            onPress={() => setDraft({ ...draft, response: option })}
            block
          />
        ))}
      </View>
    </>
  );
}

function GoalsStep({
  draft,
  setDraft,
  catalog,
}: {
  draft: Draft;
  setDraft: (next: Draft) => void;
  catalog: DemoOnboardingCatalog | null;
}) {
  const goals = catalog?.goals ?? [];
  const grouped = groupGoals(goals);
  return (
    <>
      <AppText variant="screenTitle" style={styles.stepTitle}>Goals</AppText>
      <AppText variant="secondary">Choose 2 or 3, then pick which matters most.</AppText>
      {Object.entries(grouped).map(([domain, items]) => (
        <View key={domain} style={styles.group}>
          <SectionLabel>{domain}</SectionLabel>
          <View style={styles.stack}>
            {items.map((item) => (
              <ChoiceChip
                key={item.code}
                label={item.label}
                selected={draft.goalCodes.includes(item.code)}
                onPress={() => {
                  const next = toggle(
                    draft.goalCodes,
                    item.code,
                    catalog?.max_goals ?? 3,
                  );
                  const primary =
                    next.includes(draft.primaryGoalCode) ? draft.primaryGoalCode : '';
                  setDraft({ ...draft, goalCodes: next, primaryGoalCode: primary });
                }}
                block
              />
            ))}
          </View>
        </View>
      ))}
      {draft.goalCodes.length >= 2 ? (
        <>
          <SectionLabel>Which is #1?</SectionLabel>
          <View style={styles.stack}>
          {draft.goalCodes.map((code) => {
            const item = goals.find((goal) => goal.code === code);
            return (
              <ChoiceChip
                key={code}
                label={item?.label ?? code}
                selected={draft.primaryGoalCode === code}
                onPress={() => setDraft({ ...draft, primaryGoalCode: code })}
                block
              />
            );
          })}
          </View>
        </>
      ) : null}
    </>
  );
}

function WorksStep({
  draft,
  setDraft,
  catalog,
}: {
  draft: Draft;
  setDraft: (next: Draft) => void;
  catalog: DemoOnboardingCatalog | null;
}) {
  const goals = catalog?.goals ?? [];
  return (
    <>
      <AppText variant="screenTitle" style={styles.stepTitle}>What works</AppText>
      <SectionLabel>Motivators · up to 4</SectionLabel>
      <ChipPicker
        options={catalog?.motivator_suggestions ?? []}
        selected={draft.motivators}
        max={catalog?.max_motivators ?? 4}
        onToggle={(value) =>
          setDraft({
            ...draft,
            motivators: toggle(draft.motivators, value, catalog?.max_motivators ?? 4),
          })
        }
      />
      <SectionLabel>Preferred activity length</SectionLabel>
      <View style={styles.row}>
        {(catalog?.durations ?? [10, 15, 20, 25]).map((minutes) => (
          <ChoiceChip
            key={minutes}
            label={`${minutes} min`}
            selected={draft.minutes === minutes}
            onPress={() => setDraft({ ...draft, minutes })}
          />
        ))}
      </View>
      <View style={styles.review}>
        <SectionLabel>Review</SectionLabel>
        <AppText variant="secondary">
          {draft.nickname.trim() || 'Nickname'}, age {draft.ageYears}, grade{' '}
          {draft.grade === 'K' ? 'K' : draft.grade}
        </AppText>
        <AppText variant="secondary">Enjoys: {draft.interests.join(', ') || '—'}</AppText>
        <AppText variant="secondary">Strengths: {draft.strengths.join(', ') || '—'}</AppText>
        <AppText variant="secondary">
          Working on: {draft.difficulties.join(', ') || '—'}
        </AppText>
        <AppText variant="secondary">
          Top goal:{' '}
          {goals.find((item) => item.code === draft.primaryGoalCode)?.label ?? '—'}
        </AppText>
        <AppText variant="secondary">About {draft.minutes ?? 20} minutes</AppText>
      </View>
    </>
  );
}

function AddCustom({
  value,
  onChange,
  onAdd,
}: {
  value: string;
  onChange: (value: string) => void;
  onAdd: () => void;
}) {
  return (
    <View style={styles.addRow}>
      <AppText variant="caption">Optional</AppText>
      <TextInput
        accessibilityLabel="Add a short made-up word, optional"
        value={value}
        onChangeText={(next) => onChange(clampText(next, TEXT_LIMITS.customLabel))}
        placeholder="Add a short made-up word"
        placeholderTextColor={colors.textSecondary}
        maxLength={TEXT_LIMITS.customLabel}
        returnKeyType="done"
        blurOnSubmit
        style={[styles.input, styles.addInput]}
      />
      <AppButton label="Add" variant="secondary" onPress={onAdd} disabled={!value.trim()} />
    </View>
  );
}

function stepIsValid(step: number, draft: Draft): boolean {
  if (step === 1) {
    return draft.nickname.trim().length >= 1 && draft.grade.length > 0;
  }
  if (step === 2) {
    return draft.interests.length > 0 && draft.strengths.length > 0;
  }
  if (step === 3) {
    return draft.difficulties.length > 0 && draft.response.length > 0;
  }
  if (step === 4) {
    return (
      draft.goalCodes.length >= 2 &&
      draft.goalCodes.length <= 3 &&
      draft.goalCodes.includes(draft.primaryGoalCode)
    );
  }
  return (
    draft.motivators.length > 0 &&
    draft.minutes !== null &&
    draft.nickname.trim().length >= 1
  );
}

function toggle(values: string[], value: string, max: number): string[] {
  const cleaned = value.trim();
  if (!cleaned) {
    return values;
  }
  if (values.some((item) => item.toLowerCase() === cleaned.toLowerCase())) {
    return values.filter((item) => item.toLowerCase() !== cleaned.toLowerCase());
  }
  if (values.length >= max) {
    return values;
  }
  return [...values, cleaned];
}

function mergeOptions(suggestions: string[], selected: string[]): string[] {
  const extra = selected.filter(
    (item) =>
      !suggestions.some((option) => option.toLowerCase() === item.toLowerCase()),
  );
  return [...suggestions, ...extra];
}

function groupGoals(
  goals: { code: string; domain_label: string; label: string }[],
) {
  const grouped: Record<string, typeof goals> = {};
  for (const goal of goals) {
    grouped[goal.domain_label] = [...(grouped[goal.domain_label] ?? []), goal];
  }
  return grouped;
}

const styles = StyleSheet.create({
  track: {
    marginTop: space.xs,
    marginBottom: space.md,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.borderSubtle,
    overflow: 'hidden',
  },
  fill: {
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.actionPrimary,
  },
  demoCopy: {
    marginTop: space.md,
  },
  stepTitle: {
    marginTop: space.xs,
    marginBottom: space.xs,
  },
  input: {
    minHeight: 50,
    borderRadius: radius.input,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    paddingHorizontal: 14,
    fontSize: 17,
    color: colors.textPrimary,
    backgroundColor: colors.surface,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  stack: {
    gap: 8,
  },
  group: {
    marginTop: space.md,
    gap: 8,
  },
  review: {
    marginTop: space.xl,
    gap: 6,
  },
  addRow: {
    marginTop: space.xs,
    gap: 8,
  },
  addInput: {
    marginTop: 0,
  },
});
