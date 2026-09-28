import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useFocusEffect } from 'expo-router';

import { fetchWeeklyCoachReport } from '@/lib/api/demo';
import { EMPTY_COPY, parentMessage } from '@/lib/api/parentErrors';
import type { WeeklyCoachReport } from '@/lib/api/types';
import {
  DISPLAY_LIMITS,
  formatWeekRange,
  hasVisibleText,
  visibleLines,
  weeklySparseNote,
} from '@/lib/productCopy';
import { space } from '@/theme';
import { AppText } from '@/ui/AppText';
import { EmptyState } from '@/ui/EmptyState';
import { ErrorCallout } from '@/ui/ErrorCallout';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';

export default function WeeklyReportScreen() {
  const [report, setReport] = useState<WeeklyCoachReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    void fetchWeeklyCoachReport()
      .then((result) => {
        setReport(result);
        setError(null);
      })
      .catch(() => {
        setError(parentMessage('weekly'));
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  if (loading && !report) {
    return (
      <Screen scroll={false}>
        <ScreenLoading title="Loading this week..." />
      </Screen>
    );
  }

  if (error && !report) {
    return (
      <Screen scroll={false}>
        <ErrorCallout message={error} onRetry={load} />
      </Screen>
    );
  }

  if (!report) {
    return (
      <Screen>
        <AppText variant="screenTitle">This week</AppText>
        <EmptyState
          title={EMPTY_COPY.weekly}
          body="Complete a Daily Win this week to start a picture."
        />
      </Screen>
    );
  }

  const wins = report.this_week.wins_completed ?? report.source_session_count;
  const areas = report.this_week.academic_areas ?? [];
  const sparse = weeklySparseNote(wins);
  const strength = visibleLines(report.what_looked_strong, DISPLAY_LIMITS.weeklyBullets);
  const working = visibleLines(report.what_still_took_work, DISPLAY_LIMITS.weeklyBullets);
  const coaching = visibleLines(
    report.how_they_handled_challenge,
    DISPLAY_LIMITS.weeklyBullets,
  );

  return (
    <Screen>
      <AppText variant="screenTitle">This week</AppText>
      <AppText variant="secondary" style={styles.meta}>
        {formatWeekRange(report.week_start, report.week_end)}
      </AppText>
      {error ? <ErrorCallout message={error} onRetry={load} /> : null}

      <View style={styles.summary}>
        <AppText variant="metric">{wins}</AppText>
        <AppText variant="secondary">
          Win{wins === 1 ? '' : 's'}
          {areas.length ? ` · ${areas.length} skill${areas.length === 1 ? '' : 's'}` : ''}
        </AppText>
        {sparse ? (
          <AppText variant="caption" style={styles.meta}>
            {sparse}
          </AppText>
        ) : null}
      </View>

      <WeekBlock title="Strength" lines={strength} />
      <WeekBlock title="Working on" lines={working} />
      <WeekBlock title="Coaching" lines={coaching} />

      {report.next_week && hasVisibleText(report.next_week.primary_academic_focus) ? (
        <View style={styles.block}>
          <AppText variant="sectionLabel">Next week</AppText>
          <AppText>{report.next_week.primary_academic_focus}</AppText>
          {hasVisibleText(report.next_week.secondary_academic_focus) ? (
            <AppText variant="secondary">{report.next_week.secondary_academic_focus}</AppText>
          ) : null}
          {hasVisibleText(report.next_week.growth_focus) ? (
            <AppText variant="secondary">{report.next_week.growth_focus}</AppText>
          ) : null}
        </View>
      ) : null}

      {hasVisibleText(report.one_thing_for_the_parent) ? (
        <View style={styles.block}>
          <AppText variant="sectionLabel">For you</AppText>
          <AppText>{report.one_thing_for_the_parent}</AppText>
        </View>
      ) : null}
    </Screen>
  );
}

function WeekBlock({ title, lines }: { title: string; lines: string[] }) {
  if (lines.length === 0) {
    return null;
  }
  return (
    <View style={styles.block}>
      <AppText variant="sectionLabel">{title}</AppText>
      {lines.map((item) => (
        <AppText key={item}>{item}</AppText>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  meta: {
    marginTop: space.xs,
    marginBottom: space.sm,
  },
  summary: {
    marginTop: space.md,
    marginBottom: space.lg,
    gap: space.xxs,
  },
  block: {
    marginTop: space.lg,
    gap: space.xs,
  },
});
