import { useCallback, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';

import { fetchDemoDailyWins } from '@/lib/api/demo';
import {
  EMPTY_COPY,
  PARENT_ERRORS,
  describeCaughtError,
  type ApiErrorKind,
} from '@/lib/api/parentErrors';
import type { DemoDailyWinSummary } from '@/lib/api/types';
import { colors, space } from '@/theme';
import { AppText } from '@/ui/AppText';
import { EmptyState } from '@/ui/EmptyState';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { StatusBadge } from '@/ui/StatusBadge';

export default function HistoryScreen() {
  const router = useRouter();
  const [items, setItems] = useState<DemoDailyWinSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    void fetchDemoDailyWins()
      .then((next) => {
        setItems(next);
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
      <AppText variant="screenTitle">Recent Daily Wins</AppText>
      {loading && !items ? <ScreenLoading title="Loading Daily Wins" /> : null}
      {error ? (
        <ErrorCallout
          message={error}
          errorCode={errorCode}
          errorKind={errorKind}
          onRetry={load}
        />
      ) : null}
      {items && items.length === 0 ? (
        <EmptyState title={EMPTY_COPY.history} icon="time-outline" />
      ) : null}
      {items?.map((item) => (
        <Pressable
          key={item.id}
          accessibilityRole="button"
          accessibilityLabel={`${item.title}. ${item.has_feedback ? 'Completed' : 'Reflection pending'}`}
          onPress={() =>
            router.push({ pathname: '/daily-win', params: { id: item.id } })
          }
          style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
          <AppText variant="bodyEmphasized">{item.title}</AppText>
          <AppText variant="caption" style={styles.meta}>
            {new Date(item.created_at).toLocaleDateString()} • {item.primary_focus}
          </AppText>
          <View style={styles.badges}>
            <StatusBadge
              label={item.has_feedback ? 'Completed' : 'Reflection pending'}
              tone={item.has_feedback ? 'success' : 'pending'}
            />
            {item.is_adaptive ? <StatusBadge label="Adapted" tone="adapted" /> : null}
          </View>
        </Pressable>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: {
    marginTop: space.md,
    paddingVertical: space.md,
    minHeight: 44,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.borderSubtle,
    alignSelf: 'stretch',
  },
  pressed: {
    opacity: 0.7,
  },
  meta: {
    marginTop: 4,
  },
  badges: {
    marginTop: 8,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
});
