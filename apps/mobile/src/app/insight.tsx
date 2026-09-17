import { useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';

import { ApiError } from '@/lib/api/client';
import { generateDemoDailyWin } from '@/lib/api/demo';

function firstString(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] ?? '';
  }
  return value ?? '';
}

export default function InsightScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    observation?: string | string[];
    next_adjustment?: string | string[];
    nickname?: string | string[];
  }>();
  const observation = firstString(params.observation);
  const nextAdjustment = firstString(params.next_adjustment);
  const nickname = firstString(params.nickname) || 'this child';
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const generateLock = useRef(false);

  const handleGenerate = () => {
    if (generateLock.current || generating) {
      return;
    }
    generateLock.current = true;
    setGenerating(true);
    setError(null);
    setErrorCode(null);
    void generateDemoDailyWin()
      .then(() => {
        router.replace('/daily-win');
      })
      .catch((caught: unknown) => {
        generateLock.current = false;
        if (caught instanceof ApiError) {
          setError(caught.message);
          setErrorCode(caught.errorCode ?? null);
          return;
        }
        setError(
          caught instanceof Error
            ? caught.message
            : 'Daily Win could not be created. Please try again.',
        );
      })
      .finally(() => {
        setGenerating(false);
      });
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.brand}>Daily Win</Text>
        <Text style={styles.title}>What we learned</Text>
        <Text style={styles.body}>{observation || 'The reflection was saved.'}</Text>

        <Text style={styles.sectionTitle}>What changes next</Text>
        <Text style={styles.body}>
          {nextAdjustment || 'The next Daily Win can now be generated.'}
        </Text>

        {generating ? (
          <View style={styles.loadingCard}>
            <Text style={styles.loadingTitle}>
              {`Designing ${nickname}'s Daily Win…`}
            </Text>
            <Text style={styles.loadingBody}>
              Using what you reported to make a modest adjustment.
            </Text>
          </View>
        ) : null}

        {error ? (
          <>
            <Text style={styles.error}>{error}</Text>
            {errorCode ? (
              <Text style={styles.devError}>{`Dev error: ${errorCode}`}</Text>
            ) : null}
          </>
        ) : null}

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={
            generating
              ? `Designing ${nickname}'s Daily Win`
              : `Generate ${nickname}'s next Daily Win`
          }
          disabled={generating}
          onPress={handleGenerate}
          style={({ pressed }) => [
            styles.button,
            generating && styles.disabled,
            pressed && !generating && styles.pressed,
          ]}>
          <Text style={styles.buttonLabel}>
            {generating
              ? 'Designing…'
              : error
                ? 'Retry next Daily Win'
                : `Generate ${nickname}'s next Daily Win`}
          </Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
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
  sectionTitle: {
    marginTop: 28,
    marginBottom: 10,
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: '#6F6A64',
  },
  body: {
    marginTop: 10,
    fontSize: 18,
    lineHeight: 26,
    color: '#1C1917',
  },
  loadingCard: {
    marginTop: 24,
    padding: 18,
    borderRadius: 18,
    backgroundColor: '#EAE4DA',
  },
  loadingTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1C1917',
  },
  loadingBody: {
    marginTop: 8,
    fontSize: 15,
    lineHeight: 22,
    color: '#6F6A64',
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
    marginTop: 28,
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
