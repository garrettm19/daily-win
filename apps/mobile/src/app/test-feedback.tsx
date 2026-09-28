import { useState } from 'react';
import { Share, StyleSheet, TextInput, View } from 'react-native';
import { Redirect, useRouter } from 'expo-router';

import { useParentPilotView } from '@/hooks/useParentPilotView';
import { clampText, TEXT_LIMITS } from '@/lib/textLimits';
import { colors, radius, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { Screen } from '@/ui/Screen';
import { TextButton } from '@/ui/TextButton';

const QUESTIONS = [
  { key: 'confused', prompt: 'What confused you?' },
  { key: 'useful', prompt: 'What felt useful?' },
  { key: 'unnecessary', prompt: 'What felt unnecessary?' },
  { key: 'weekly', prompt: 'Would you realistically use this a few times a week?' },
] as const;

export default function TestFeedbackScreen() {
  const router = useRouter();
  const parentPilotView = useParentPilotView();
  const [answers, setAnswers] = useState({
    confused: '',
    useful: '',
    unnecessary: '',
    weekly: '',
    extra: '',
  });
  const [shareError, setShareError] = useState<string | null>(null);

  const update = (key: keyof typeof answers, value: string) => {
    setAnswers((current) => ({
      ...current,
      [key]: clampText(value, TEXT_LIMITS.testerFeedback),
    }));
  };

  const copyFeedback = async () => {
    const lines = [
      ...QUESTIONS.map((item) => `${item.prompt}\n${answers[item.key].trim() || '—'}`),
      `Anything else?\n${answers.extra.trim() || '—'}`,
    ];
    try {
      await Share.share({ message: lines.join('\n\n') });
      setShareError(null);
    } catch {
      setShareError('Could not open share. Your answers are still here.');
    }
  };

  if (!__DEV__) {
    return (
      <Screen>
        <AppText variant="screenTitle">Not available</AppText>
        <AppButton label="Home" onPress={() => router.dismissTo('/')} />
      </Screen>
    );
  }

  if (parentPilotView) {
    return <Redirect href="/" />;
  }

  return (
    <Screen keyboard>
      <AppText variant="sectionLabel">Tester notes</AppText>
      <AppText variant="screenTitle" style={styles.title}>
        A few questions for Mason
      </AppText>
      <AppText variant="secondary" style={styles.body}>
        Answers stay on this phone. Nothing is sent to Daily Win or an AI
        provider.
      </AppText>
      {QUESTIONS.map((item) => (
        <View key={item.key}>
          <AppText variant="bodyEmphasized" style={styles.prompt}>
            {item.prompt}
          </AppText>
          <TextInput
            accessibilityLabel={item.prompt}
            value={answers[item.key]}
            onChangeText={(value) => update(item.key, value)}
            placeholder="Type here"
            placeholderTextColor={colors.textSecondary}
            maxLength={TEXT_LIMITS.testerFeedback}
            multiline
            style={styles.input}
          />
        </View>
      ))}
      <AppText variant="bodyEmphasized" style={styles.prompt}>
        Anything else?
      </AppText>
      <AppText variant="caption" style={styles.optional}>
        Optional
      </AppText>
      <TextInput
        accessibilityLabel="Anything else, optional"
        value={answers.extra}
        onChangeText={(value) => update('extra', value)}
        placeholder="Optional"
        placeholderTextColor={colors.textSecondary}
        maxLength={TEXT_LIMITS.testerFeedback}
        multiline
        style={styles.input}
      />
      {shareError ? (
        <AppText variant="secondary" style={styles.error}>
          {shareError}
        </AppText>
      ) : null}
      <AppButton label="Share feedback" onPress={() => void copyFeedback()} />
      <TextButton label="Back" onPress={() => router.back()} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: {
    marginTop: space.xs,
  },
  body: {
    marginTop: space.sm,
  },
  prompt: {
    marginTop: space.lg,
    marginBottom: space.xs,
  },
  optional: {
    marginBottom: space.xs,
  },
  input: {
    minHeight: 88,
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
  error: {
    marginTop: space.md,
    color: colors.danger,
  },
});
