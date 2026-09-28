import { useCallback, useEffect, useRef, useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
import { useRouter } from 'expo-router';

import { ApiError } from '@/lib/api/client';
import {
  fetchLatestDemoDailyWin,
  submitDemoDailyWinFeedback,
} from '@/lib/api/demo';
import { parentMessage, type ApiErrorKind } from '@/lib/api/parentErrors';
import { hapticSuccess } from '@/lib/haptics';
import {
  clearReflectionDraft,
  loadReflectionDraft,
  saveReflectionDraft,
} from '@/lib/reflectionDraft';
import { clampText, TEXT_LIMITS } from '@/lib/textLimits';
import {
  ACADEMIC_RESULT_OPTIONS,
  asksAboutSetback,
  asksEngagementQuestion,
  asksForCounts,
  checkCaption,
  countsAreValid,
  hasAcademicProbe,
} from '@/lib/academicLoop';
import { isSelectableLabel } from '@/lib/displayNormalize';
import { DISPLAY_LIMITS, optionLabel, selectableOptionLabel } from '@/lib/productCopy';
import type {
  AcademicResult,
  DailyWinFeedbackCreate,
  DemoDailyWin,
} from '@/lib/api/types';
import { colors, radius, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { ChoiceChip } from '@/ui/ChoiceChip';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { SectionLabel } from '@/ui/SectionLabel';

const DIFFICULTY: { value: DailyWinFeedbackCreate['difficulty']; label: string }[] =
  [
    { value: 'too_easy', label: 'Too easy' },
    { value: 'about_right', label: 'About right' },
    { value: 'too_hard', label: 'Too hard' },
  ];

const ENGAGEMENT: { value: DailyWinFeedbackCreate['engagement']; label: string }[] =
  [
    { value: 'low', label: 'Not into it' },
    { value: 'medium', label: 'Into it' },
    { value: 'high', label: 'Really into it' },
  ];

const COMPLETION: { value: DailyWinFeedbackCreate['completion']; label: string }[] =
  [
    { value: 'completed', label: 'Completed' },
    { value: 'partially_completed', label: 'Partly' },
    { value: 'stopped_early', label: 'Stopped early' },
  ];

const SETBACK: {
  value: DailyWinFeedbackCreate['setback_response'];
  label: string;
}[] = [
  { value: 'kept_going_independently', label: 'Kept going independently' },
  { value: 'continued_after_prompt', label: 'Continued after a prompt' },
  { value: 'needed_significant_help', label: 'Needed significant help' },
  { value: 'stopped_or_avoided', label: 'Stopped / avoided' },
  { value: 'no_setback_occurred', label: "There wasn't a setback" },
];

export default function ReflectScreen() {
  const router = useRouter();
  const [dailyWin, setDailyWin] = useState<DemoDailyWin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [difficulty, setDifficulty] =
    useState<DailyWinFeedbackCreate['difficulty'] | null>(null);
  const [engagement, setEngagement] =
    useState<DailyWinFeedbackCreate['engagement'] | null>(null);
  const [completion, setCompletion] =
    useState<DailyWinFeedbackCreate['completion'] | null>(null);
  const [setbackResponse, setSetbackResponse] =
    useState<DailyWinFeedbackCreate['setback_response'] | null>(null);
  const [academicResult, setAcademicResult] = useState<AcademicResult | null>(null);
  const [correctCount, setCorrectCount] = useState<string>('');
  const [attemptedCount, setAttemptedCount] = useState<string>('');
  const [whatHelped, setWhatHelped] = useState('');
  const [additionalNote, setAdditionalNote] = useState('');
  const [selfCorrection, setSelfCorrection] = useState<string | null>(null);
  const [strategyObserved, setStrategyObserved] = useState<string | null>(null);
  const [performanceEffort, setPerformanceEffort] = useState<string | null>(null);
  const [noticeChips, setNoticeChips] = useState<string[]>([]);
  const [bonusEngagement, setBonusEngagement] = useState<string | null>(null);
  const generationRef = useRef(0);
  const submitLock = useRef(false);

  useEffect(() => {
    const generation = ++generationRef.current;
    void fetchLatestDemoDailyWin()
      .then((result) => {
        if (generation !== generationRef.current) {
          return;
        }
        if (result === null) {
          setError('No Daily Win is available yet.');
          setDailyWin(null);
          return;
        }
        const draft = loadReflectionDraft(result.id);
        if (draft) {
          setDifficulty(draft.difficulty);
          setEngagement(draft.engagement);
          setCompletion(draft.completion);
          setSetbackResponse(draft.setbackResponse);
          setAcademicResult(draft.academicResult ?? null);
          setCorrectCount(
            draft.correctCount === null ? '' : String(draft.correctCount),
          );
          setAttemptedCount(
            draft.attemptedCount === null ? '' : String(draft.attemptedCount),
          );
          setWhatHelped(draft.whatHelped);
          setAdditionalNote(draft.additionalNote);
        }
        setDailyWin(result);
        setError(null);
      })
      .catch(() => {
        if (generation !== generationRef.current) {
          return;
        }
        setError(parentMessage('load'));
        setErrorKind('unavailable');
      })
      .finally(() => {
        if (generation === generationRef.current) {
          setLoading(false);
        }
      });
    return () => {
      generationRef.current += 1;
    };
  }, []);

  const persistDraft = useCallback(
    (patch: {
      difficulty?: DailyWinFeedbackCreate['difficulty'] | null;
      engagement?: DailyWinFeedbackCreate['engagement'] | null;
      completion?: DailyWinFeedbackCreate['completion'] | null;
      setbackResponse?: DailyWinFeedbackCreate['setback_response'] | null;
      academicResult?: AcademicResult | null;
      correctCount?: string;
      attemptedCount?: string;
      whatHelped?: string;
      additionalNote?: string;
    }) => {
      if (dailyWin === null) {
        return;
      }
      const helped = patch.whatHelped ?? whatHelped;
      const extra = patch.additionalNote ?? additionalNote;
      const correctRaw = patch.correctCount ?? correctCount;
      const attemptedRaw = patch.attemptedCount ?? attemptedCount;
      saveReflectionDraft({
        dailyWinId: dailyWin.id,
        difficulty: patch.difficulty !== undefined ? patch.difficulty : difficulty,
        engagement: patch.engagement !== undefined ? patch.engagement : engagement,
        completion: patch.completion !== undefined ? patch.completion : completion,
        setbackResponse:
          patch.setbackResponse !== undefined ? patch.setbackResponse : setbackResponse,
        academicResult:
          patch.academicResult !== undefined ? patch.academicResult : academicResult,
        correctCount: correctRaw === '' ? null : Number(correctRaw),
        attemptedCount: attemptedRaw === '' ? null : Number(attemptedRaw),
        whatHelped: helped,
        additionalNote: extra,
      });
    },
    [
      additionalNote,
      academicResult,
      attemptedCount,
      completion,
      correctCount,
      dailyWin,
      difficulty,
      engagement,
      setbackResponse,
      whatHelped,
    ],
  );

  const needsAcademic = hasAcademicProbe(dailyWin);
  const needsSetback = asksAboutSetback(dailyWin);
  const needsCounts = asksForCounts(dailyWin);
  const asksEngagement = asksEngagementQuestion(
    difficulty,
    Boolean(dailyWin?.bonus_challenge),
  );
  const parsedCorrect = correctCount === '' ? null : Number(correctCount);
  const parsedAttempted = attemptedCount === '' ? null : Number(attemptedCount);
  const countOk = !needsCounts || countsAreValid(parsedCorrect, parsedAttempted);

  const canSubmit =
    difficulty !== null &&
    (asksEngagement ? engagement !== null : true) &&
    completion !== null &&
    (!needsSetback || setbackResponse !== null) &&
    (!needsAcademic || academicResult !== null) &&
    countOk &&
    !submitting &&
    dailyWin !== null &&
    !dailyWin.has_feedback;

  const handleSubmit = () => {
    if (
      submitLock.current ||
      submitting ||
      dailyWin === null ||
      dailyWin.has_feedback ||
      difficulty === null ||
      (asksEngagement && engagement === null) ||
      completion === null ||
      (needsAcademic && academicResult === null) ||
      (needsSetback && setbackResponse === null) ||
      !countOk
    ) {
      return;
    }
    submitLock.current = true;
    setSubmitting(true);
    setError(null);
    setErrorCode(null);
    setErrorKind(null);
    const payload: DailyWinFeedbackCreate = {
      difficulty,
      engagement: engagement ?? 'medium',
      completion,
      setback_response: setbackResponse ?? 'no_setback_occurred',
    };
    if (needsAcademic && academicResult) {
      payload.academic_result = academicResult;
      if (needsCounts && parsedCorrect !== null && parsedAttempted !== null) {
        payload.correct_count = parsedCorrect;
        payload.attempted_count = parsedAttempted;
      }
    }
    const helped = whatHelped.trim();
    const extra = additionalNote.trim();
    if (helped) {
      payload.what_helped = helped;
    }
    if (extra) {
      payload.additional_note = extra;
    }
    if (selfCorrection) {
      payload.self_correction = selfCorrection;
    }
    if (strategyObserved) {
      payload.strategy_observed = strategyObserved;
    }
    if (performanceEffort) {
      payload.performance_effort = performanceEffort;
    }
    if (noticeChips.length > 0) {
      payload.notice_chips = noticeChips;
    }
    if (bonusEngagement) {
      payload.bonus_engagement = bonusEngagement;
    }
    void submitDemoDailyWinFeedback(dailyWin.id, payload)
      .then((result) => {
        clearReflectionDraft(dailyWin.id);
        hapticSuccess();
        router.replace({
          pathname: '/insight',
          params: {
            observation: result.insight.observation,
            next_adjustment:
              result.what_changes_next ?? result.insight.next_adjustment,
            nickname: dailyWin.child_nickname,
            academic_observation: result.academic_observation ?? '',
            growth_observation:
              result.growth_observation ?? result.insight.observation,
            academic_area: result.what_we_learned?.[0]?.area ?? '',
            skill: dailyWin.primary_skill_display_name,
            academic_result: academicResult ?? '',
            difficulty,
            setback: setbackResponse ?? '',
            self_correction: selfCorrection ?? '',
          },
        });
      })
      .catch((caught: unknown) => {
        submitLock.current = false;
        if (caught instanceof ApiError) {
          setError(
            caught.errorCode === 'already_submitted'
              ? 'This Daily Win already has a reflection.'
              : parentMessage('saveReflection', caught.kind),
          );
          setErrorCode(caught.errorCode ?? null);
          setErrorKind(caught.kind);
          if (caught.errorCode === 'already_submitted') {
            clearReflectionDraft(dailyWin.id);
            setDailyWin({ ...dailyWin, has_feedback: true });
            router.dismissTo('/daily-win');
          }
          return;
        }
        setError(parentMessage('saveReflection'));
        setErrorKind('unavailable');
      })
      .finally(() => {
        setSubmitting(false);
      });
  };

  return (
    <Screen keyboard>
      {loading ? <ScreenLoading title="Loading this Daily Win" /> : null}
      {!loading && error && dailyWin === null ? (
        <ErrorCallout
          message={parentMessage('load')}
          onRetry={() => {
            setLoading(true);
            setError(null);
            generationRef.current += 1;
            const generation = generationRef.current;
            void fetchLatestDemoDailyWin()
              .then((result) => {
                if (generation !== generationRef.current) {
                  return;
                }
                if (result === null) {
                  setError('No Daily Win is available yet.');
                  setDailyWin(null);
                  return;
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
          }}
        />
      ) : null}
      {!loading && dailyWin ? (
        <>
            <AppText variant="screenTitle">How’d it go?</AppText>
            <AppText variant="secondary" style={styles.meta}>
              Report the session. About a minute.
            </AppText>

            {dailyWin.has_feedback ? (
              <ErrorCallout message="This Daily Win already has a reflection." />
            ) : null}

            <ChoiceGroup
              title="Challenge"
              options={DIFFICULTY}
              value={difficulty}
              onChange={(value) => {
                setDifficulty(value);
                persistDraft({ difficulty: value });
              }}
              disabled={submitting || dailyWin.has_feedback}
            />
            {needsAcademic && dailyWin.assessment ? (
              <>
                <ChoiceGroup
                  title="The check"
                  caption={checkCaption(dailyWin.assessment)}
                  options={ACADEMIC_RESULT_OPTIONS}
                  value={academicResult}
                  onChange={(value) => {
                    setAcademicResult(value);
                    persistDraft({ academicResult: value });
                  }}
                  disabled={submitting || dailyWin.has_feedback}
                />
                {needsCounts ? (
                  <View style={styles.group}>
                    <SectionLabel>How many were correct?</SectionLabel>
                    <View style={styles.countRow}>
                      <TextInput
                        accessibilityLabel="Correct count"
                        keyboardType="number-pad"
                        value={correctCount}
                        onChangeText={(value) => {
                          const next = value.replace(/[^0-9]/g, '').slice(0, 2);
                          setCorrectCount(next);
                          persistDraft({ correctCount: next });
                        }}
                        placeholder="0"
                        placeholderTextColor={colors.textSecondary}
                        editable={!submitting && !dailyWin.has_feedback}
                        style={styles.countInput}
                      />
                      <AppText variant="secondary">out of</AppText>
                      <TextInput
                        accessibilityLabel="Attempted count"
                        keyboardType="number-pad"
                        value={attemptedCount}
                        onChangeText={(value) => {
                          const next = value.replace(/[^0-9]/g, '').slice(0, 2);
                          setAttemptedCount(next);
                          persistDraft({ attemptedCount: next });
                        }}
                        placeholder="0"
                        placeholderTextColor={colors.textSecondary}
                        editable={!submitting && !dailyWin.has_feedback}
                        style={styles.countInput}
                      />
                    </View>
                    <AppText variant="caption">Optional</AppText>
                  </View>
                ) : null}
              </>
            ) : null}

            {needsSetback ? (
            <ChoiceGroup
              title="If they got stuck..."
              options={SETBACK}
              value={setbackResponse}
              onChange={(value) => {
                setSetbackResponse(value);
                persistDraft({ setbackResponse: value });
              }}
              disabled={submitting || dailyWin.has_feedback}
            />
            ) : null}

            {dailyWin.smart_reflection?.notice_chips ? (
              <View style={styles.group}>
                <SectionLabel>What stood out?</SectionLabel>
                <AppText variant="caption" style={styles.caption}>
                  Optional · pick any that fit
                </AppText>
                <View style={styles.chipRow}>
                  {dailyWin.smart_reflection.notice_chips
                    .slice(0, DISPLAY_LIMITS.noticeChips)
                    .map((chip) => {
                      const label = selectableOptionLabel(chip);
                      if (!label) {
                        return null;
                      }
                      return (
                    <ChoiceChip
                      key={chip}
                      label={label}
                      selected={noticeChips.includes(chip)}
                      disabled={submitting || dailyWin.has_feedback}
                      onPress={() => {
                        setNoticeChips((current) =>
                          current.includes(chip)
                            ? current.filter((item) => item !== chip)
                            : [...current, chip],
                        );
                      }}
                    />
                      );
                    })}
                </View>
              </View>
            ) : null}

            {dailyWin.smart_reflection?.self_correction_options &&
            dailyWin.primary_skill_code.startsWith('writing.') ? (
              <ChoiceGroup
                title="Did they notice and fix it?"
                options={dailyWin.smart_reflection.self_correction_options.map((value) => ({
                  value,
                  label: optionLabel(value),
                }))}
                value={selfCorrection}
                onChange={setSelfCorrection}
                disabled={submitting || dailyWin.has_feedback}
              />
            ) : null}

            {dailyWin.smart_reflection?.effort_options && needsAcademic ? (
              <ChoiceGroup
                title="Did this look automatic?"
                options={dailyWin.smart_reflection.effort_options.map((value) => ({
                  value,
                  label: optionLabel(value),
                }))}
                value={performanceEffort}
                onChange={setPerformanceEffort}
                disabled={submitting || dailyWin.has_feedback}
              />
            ) : null}

            {dailyWin.smart_reflection?.strategy_options &&
            dailyWin.smart_reflection.strategy_options.length > 1 &&
            needsAcademic ? (
              <ChoiceGroup
                title="What strategy did you see?"
                options={dailyWin.smart_reflection.strategy_options.map((value) => ({
                  value,
                  label: optionLabel(value),
                }))}
                value={strategyObserved}
                onChange={setStrategyObserved}
                disabled={submitting || dailyWin.has_feedback}
              />
            ) : null}

            <ChoiceGroup
              title="Did you finish?"
              options={COMPLETION}
              value={completion}
              onChange={(value) => {
                setCompletion(value);
                persistDraft({ completion: value });
              }}
              disabled={submitting || dailyWin.has_feedback}
            />

            {asksEngagement ? (
              <ChoiceGroup
                title="How into it were they?"
                options={ENGAGEMENT}
                value={engagement}
                onChange={(value) => {
                  setEngagement(value);
                  persistDraft({ engagement: value });
                }}
                disabled={submitting || dailyWin.has_feedback}
              />
            ) : null}

            {dailyWin.bonus_challenge && dailyWin.smart_reflection?.bonus_engagement_options ? (
              <ChoiceGroup
                title="If you tried the bonus..."
                options={dailyWin.smart_reflection.bonus_engagement_options.map((value) => ({
                  value,
                  label: optionLabel(value),
                }))}
                value={bonusEngagement}
                onChange={setBonusEngagement}
                disabled={submitting || dailyWin.has_feedback}
              />
            ) : null}

            {needsSetback ? (
              <>
            <SectionLabel>What helped them rejoin?</SectionLabel>
            <AppText variant="caption" style={styles.optional}>
              Optional
            </AppText>
            <TextInput
              accessibilityLabel="What helped them rejoin, optional"
              value={whatHelped}
              onChangeText={(value) => {
                const next = clampText(value, TEXT_LIMITS.reflectionNote);
                setWhatHelped(next);
                persistDraft({ whatHelped: next });
              }}
              placeholder="Optional"
              placeholderTextColor={colors.textSecondary}
              editable={!submitting && !dailyWin.has_feedback}
              maxLength={TEXT_LIMITS.reflectionNote}
              style={styles.input}
              multiline
            />
              </>
            ) : null}
            <SectionLabel>Anything else?</SectionLabel>
            <AppText variant="caption" style={styles.optional}>
              Optional
            </AppText>
            <TextInput
              accessibilityLabel="Anything else, optional"
              value={additionalNote}
              onChangeText={(value) => {
                const next = clampText(value, TEXT_LIMITS.reflectionNote);
                setAdditionalNote(next);
                persistDraft({ additionalNote: next });
              }}
              placeholder="Optional"
              placeholderTextColor={colors.textSecondary}
              editable={!submitting && !dailyWin.has_feedback}
              maxLength={TEXT_LIMITS.reflectionNote}
              style={styles.input}
              multiline
            />

            {error && dailyWin ? (
              <ErrorCallout
                message={error}
                errorCode={errorCode}
                errorKind={errorKind}
              />
            ) : null}

            <AppButton
              label={submitting ? 'Saving reflection…' : 'Save reflection'}
              accessibilityLabel="Save reflection"
              disabled={!canSubmit}
              loading={submitting}
              onPress={handleSubmit}
            />
            <AppButton
              label="Cancel"
              variant="secondary"
              disabled={submitting}
              onPress={() => router.back()}
            />
        </>
      ) : null}
    </Screen>
  );
}

function ChoiceGroup<T extends string>({
  title,
  caption,
  options,
  value,
  onChange,
  disabled = false,
}: {
  title: string;
  caption?: string;
  options: { value: T; label: string }[];
  value: T | null;
  onChange: (value: T) => void;
  disabled?: boolean;
}) {
  return (
    <View style={styles.group}>
      <SectionLabel>{title}</SectionLabel>
      {caption ? (
        <AppText variant="caption" style={styles.caption}>
          {caption}
        </AppText>
      ) : null}
      <View style={styles.chipRow}>
        {options
          .filter((option) => isSelectableLabel(option.label))
          .map((option) => (
          <ChoiceChip
            key={option.value}
            label={option.label}
            selected={option.value === value}
            disabled={disabled}
            onPress={() => onChange(option.value)}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  meta: {
    marginTop: space.xs,
    marginBottom: space.sm,
  },
  group: {
    marginTop: space.md,
    gap: space.xs,
  },
  caption: {
    marginBottom: space.xs,
  },
  countRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  countInput: {
    width: 56,
    minHeight: 44,
    paddingHorizontal: 8,
    borderRadius: radius.input,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    color: colors.textPrimary,
    fontSize: 17,
    textAlign: 'center',
  },
  optional: {
    marginTop: space.md,
    marginBottom: space.xs,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  input: {
    minHeight: 80,
    padding: 12,
    borderRadius: radius.input,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    color: colors.textPrimary,
    fontSize: 17,
    lineHeight: 24,
    textAlignVertical: 'top',
  },
});
