import { useEffect, useRef, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';

import { ApiError } from '@/lib/api/client';
import {
  fetchLatestDemoDailyWin,
  submitDemoDailyWinFeedback,
} from '@/lib/api/demo';
import type {
  DailyWinFeedbackCreate,
  DemoDailyWin,
} from '@/lib/api/types';

const DIFFICULTY: { value: DailyWinFeedbackCreate['difficulty']; label: string }[] =
  [
    { value: 'too_easy', label: 'Too easy' },
    { value: 'about_right', label: 'About right' },
    { value: 'too_hard', label: 'Too hard' },
  ];

const ENGAGEMENT: { value: DailyWinFeedbackCreate['engagement']; label: string }[] =
  [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
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
  const [whatHelped, setWhatHelped] = useState('');
  const [additionalNote, setAdditionalNote] = useState('');
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
        setDailyWin(result);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (generation !== generationRef.current) {
          return;
        }
        setDailyWin(null);
        setError(
          caught instanceof Error
            ? caught.message
            : 'The Daily Win could not be loaded.',
        );
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

  const canSubmit =
    difficulty !== null &&
    engagement !== null &&
    completion !== null &&
    setbackResponse !== null &&
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
      engagement === null ||
      completion === null ||
      setbackResponse === null
    ) {
      return;
    }
    submitLock.current = true;
    setSubmitting(true);
    setError(null);
    setErrorCode(null);
    const payload: DailyWinFeedbackCreate = {
      difficulty,
      engagement,
      completion,
      setback_response: setbackResponse,
    };
    const helped = whatHelped.trim();
    const extra = additionalNote.trim();
    if (helped) {
      payload.what_helped = helped;
    }
    if (extra) {
      payload.additional_note = extra;
    }
    void submitDemoDailyWinFeedback(dailyWin.id, payload)
      .then((result) => {
        router.replace({
          pathname: '/insight',
          params: {
            observation: result.insight.observation,
            next_adjustment: result.insight.next_adjustment,
            nickname: dailyWin.child_nickname,
          },
        });
      })
      .catch((caught: unknown) => {
        submitLock.current = false;
        if (caught instanceof ApiError) {
          setError(caught.message);
          setErrorCode(caught.errorCode ?? null);
          if (caught.errorCode === 'already_submitted') {
            setDailyWin({ ...dailyWin, has_feedback: true });
          }
          return;
        }
        setError(
          caught instanceof Error
            ? caught.message
            : 'Reflection could not be saved. Please try again.',
        );
      })
      .finally(() => {
        setSubmitting(false);
      });
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      {loading ? (
        <View style={styles.centered}>
          <Text style={styles.brand}>Daily Win</Text>
          <Text style={styles.statusTitle}>Loading this Daily Win</Text>
        </View>
      ) : null}
      {!loading && error && dailyWin === null ? (
        <View style={styles.centered}>
          <Text style={styles.brand}>Daily Win</Text>
          <Text style={styles.statusTitle}>{"Couldn't load the Daily Win"}</Text>
          <Text style={styles.statusBody}>{error}</Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Go back"
            onPress={() => router.back()}
            style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
            <Text style={styles.buttonLabel}>Go back</Text>
          </Pressable>
        </View>
      ) : null}
      {!loading && dailyWin ? (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <Text style={styles.brand}>Daily Win</Text>
          <Text style={styles.title}>How did it go?</Text>
          <Text style={styles.meta}>
            A short report for {dailyWin.child_nickname}. No extra writing required.
          </Text>

          {dailyWin.has_feedback ? (
            <Text style={styles.error}>This Daily Win already has a reflection.</Text>
          ) : null}

          <ChoiceGroup
            title="Difficulty"
            options={DIFFICULTY}
            value={difficulty}
            onChange={setDifficulty}
            disabled={submitting || dailyWin.has_feedback}
          />
          <ChoiceGroup
            title="Engagement"
            options={ENGAGEMENT}
            value={engagement}
            onChange={setEngagement}
            disabled={submitting || dailyWin.has_feedback}
          />
          <ChoiceGroup
            title="Completion"
            options={COMPLETION}
            value={completion}
            onChange={setCompletion}
            disabled={submitting || dailyWin.has_feedback}
          />
          <ChoiceGroup
            title="After the first setback..."
            options={SETBACK}
            value={setbackResponse}
            onChange={setSetbackResponse}
            disabled={submitting || dailyWin.has_feedback}
          />

          <Text style={styles.sectionTitle}>What helped them rejoin?</Text>
          <TextInput
            accessibilityLabel="What helped them rejoin"
            value={whatHelped}
            onChangeText={setWhatHelped}
            placeholder="Optional"
            placeholderTextColor="#8A8279"
            editable={!submitting && !dailyWin.has_feedback}
            style={styles.input}
            multiline
          />
          <Text style={styles.sectionTitle}>Anything else?</Text>
          <TextInput
            accessibilityLabel="Anything else"
            value={additionalNote}
            onChangeText={setAdditionalNote}
            placeholder="Optional"
            placeholderTextColor="#8A8279"
            editable={!submitting && !dailyWin.has_feedback}
            style={styles.input}
            multiline
          />

          {error && dailyWin ? (
            <>
              <Text style={styles.error}>{error}</Text>
              {errorCode ? (
                <Text style={styles.devError}>{`Dev error: ${errorCode}`}</Text>
              ) : null}
            </>
          ) : null}

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Save reflection"
            disabled={!canSubmit}
            onPress={handleSubmit}
            style={({ pressed }) => [
              styles.button,
              !canSubmit && styles.disabled,
              pressed && canSubmit && styles.pressed,
            ]}>
            <Text style={styles.buttonLabel}>
              {submitting ? 'Saving…' : 'Save reflection'}
            </Text>
          </Pressable>
        </ScrollView>
      ) : null}
    </SafeAreaView>
  );
}

function ChoiceGroup<T extends string>({
  title,
  options,
  value,
  onChange,
  disabled = false,
}: {
  title: string;
  options: { value: T; label: string }[];
  value: T | null;
  onChange: (value: T) => void;
  disabled?: boolean;
}) {
  return (
    <View style={styles.group}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.chipRow}>
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <Pressable
              key={option.value}
              accessibilityRole="button"
              accessibilityState={{ selected, disabled }}
              accessibilityLabel={option.label}
              disabled={disabled}
              onPress={() => onChange(option.value)}
              style={({ pressed }) => [
                styles.chip,
                selected && styles.chipSelected,
                pressed && !disabled && styles.pressed,
              ]}>
              <Text style={[styles.chipLabel, selected && styles.chipLabelSelected]}>
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F4F1EB',
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 12,
    paddingBottom: 40,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 28,
  },
  brand: {
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    color: '#6F6A64',
  },
  title: {
    marginTop: 10,
    fontSize: 28,
    lineHeight: 34,
    fontWeight: '700',
    color: '#1C1917',
  },
  meta: {
    marginTop: 6,
    fontSize: 16,
    color: '#6F6A64',
  },
  statusTitle: {
    marginTop: 16,
    fontSize: 24,
    fontWeight: '600',
    color: '#1C1917',
  },
  statusBody: {
    marginTop: 10,
    fontSize: 16,
    lineHeight: 24,
    color: '#6F6A64',
  },
  group: {
    marginTop: 22,
  },
  sectionTitle: {
    marginTop: 22,
    marginBottom: 10,
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: '#6F6A64',
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 999,
    borderWidth: 2,
    borderColor: '#D7D0C6',
    backgroundColor: '#EDE8E0',
  },
  chipSelected: {
    backgroundColor: '#2C4A3E',
    borderColor: '#1C1917',
  },
  chipLabel: {
    fontSize: 14,
    color: '#3F3A36',
    fontWeight: '600',
  },
  chipLabelSelected: {
    color: '#F8F6F1',
  },
  input: {
    minHeight: 72,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E6E0D6',
    backgroundColor: '#FFFcf7',
    color: '#1C1917',
    fontSize: 16,
    textAlignVertical: 'top',
  },
  error: {
    marginTop: 16,
    fontSize: 15,
    lineHeight: 22,
    color: '#8A3A2A',
  },
  devError: {
    marginTop: 6,
    fontSize: 13,
    color: '#8A7E74',
  },
  button: {
    alignSelf: 'flex-start',
    marginTop: 24,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 12,
    backgroundColor: '#2C4A3E',
  },
  disabled: {
    opacity: 0.45,
  },
  buttonLabel: {
    color: '#F8F6F1',
    fontSize: 16,
    fontWeight: '600',
  },
  pressed: {
    opacity: 0.88,
  },
});
