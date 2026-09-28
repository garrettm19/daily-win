import { useCallback, useState, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { Redirect, useFocusEffect, useRouter } from 'expo-router';

import { useParentPilotView } from '@/hooks/useParentPilotView';

import {
  fetchLearningQa,
  generateDemoDailyWinSafely,
  resetDemoActivityHistory,
  restartDemoSession,
} from '@/lib/api/demo';
import { describeCaughtError, type ApiErrorKind } from '@/lib/api/parentErrors';
import type { LearningQaBundle } from '@/lib/api/types';
import { colors, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { Card } from '@/ui/Card';
import { Screen } from '@/ui/Screen';
import { ScreenLoading } from '@/ui/ScreenLoading';
import { TextButton } from '@/ui/TextButton';

function ms(value: number | null | undefined): string {
  if (value == null) {
    return '—';
  }
  return `${value}ms`;
}

export default function LearningQaScreen() {
  const router = useRouter();
  const parentPilotView = useParentPilotView();
  const [bundle, setBundle] = useState<LearningQaBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    void fetchLearningQa()
      .then((next) => {
        setBundle(next);
        setError(null);
        setErrorKind(null);
      })
      .catch((caught: unknown) => {
        const described = describeCaughtError(
          caught,
          "Couldn't load Learning QA.",
        );
        setError(described.message);
        setErrorKind(described.kind);
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

  if (!__DEV__) {
    return (
      <Screen>
        <AppText>This screen is not available.</AppText>
      </Screen>
    );
  }

  if (parentPilotView) {
    return <Redirect href="/" />;
  }

  if (loading && !bundle) {
    return <ScreenLoading title="Loading Learning QA" />;
  }

  const trace = bundle?.latest_trace as
    | {
        instruction_plan?: { primary_skill?: string; mode?: string; scaffold?: string };
        scheduler?: {
          selected_goal?: string;
          why_selected?: string;
          deferred_goals?: string[];
          urgency_class?: string;
        };
        why_not?: {
          why_not_next_skill?: string;
          why_not_previous_skill?: string;
          why_not_second_goal?: string;
          why_not_review?: string;
          why_not_terminal?: string;
          why_this_coaching?: string;
        };
        coach_protocol?: {
          expected_challenge?: string;
          initial_parent_behavior?: string;
          prompt_ceiling?: string;
          frustration_response?: string;
          assessment_boundary?: string;
        };
        weekly_context?: {
          summary_version?: string;
          wins_this_week?: number;
          next_week_focus?: string;
        };
        next_win_implication?: string;
        generation_status?: string;
      }
    | null
    | undefined;

  return (
    <Screen scroll>
      <AppText variant="sectionLabel">Development only</AppText>
      <AppText style={styles.hint}>
        Backend-authoritative learning engine inspectability. Not a parent screen.
      </AppText>
      {error ? <AppText style={styles.error}>{error}</AppText> : null}
      {errorKind ? <AppText style={styles.hint}>{errorKind}</AppText> : null}

      <View style={styles.actions}>
        <AppButton
          label={busy ? 'Working…' : 'Generate'}
          onPress={() => {
            setBusy(true);
            void generateDemoDailyWinSafely()
              .then(() => load())
              .catch((caught: unknown) => {
                const described = describeCaughtError(caught, "Couldn't generate.");
                setError(described.message);
              })
              .finally(() => setBusy(false));
          }}
          disabled={busy}
        />
        <TextButton label="Reflect" onPress={() => router.push('/reflect')} />
        <TextButton label="Progress" onPress={() => router.push('/progress')} />
        <TextButton label="History" onPress={() => router.push('/history')} />
        <TextButton
          label="Reset activity history"
          onPress={() => {
            setBusy(true);
            void resetDemoActivityHistory()
              .then(() => load())
              .finally(() => setBusy(false));
          }}
        />
        <TextButton
          label="Restart demo"
          onPress={() => {
            setBusy(true);
            void restartDemoSession()
              .then(() => router.replace('/'))
              .finally(() => setBusy(false));
          }}
        />
      </View>

      {bundle ? (
        <>
          <QaGroup title="ENGINE" defaultOpen>
            <AppText>{bundle.snapshot.nickname}</AppText>
            <AppText style={styles.meta}>
              {bundle.engine.curriculum_version} · {bundle.engine.placement_policy} ·{' '}
              {bundle.engine.instruction_policy} · {bundle.engine.instruction_scheduler}
            </AppText>
            <AppText style={styles.meta}>
              {bundle.engine.prompt_version} · {bundle.engine.renderer_model}
            </AppText>
            <AppText style={styles.meta}>
              Latest Win: {bundle.latest_win_title ?? 'none'}{' '}
              {bundle.latest_has_feedback ? '(reflected)' : '(needs reflection)'}
            </AppText>
          </QaGroup>

          <QaGroup title="GENERATION">
            <AppText style={styles.row}>
              Intent: {bundle.generation_performance?.generation_intent_label ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Reasoning: {bundle.generation_performance?.reasoning_effort ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Requested tier:{' '}
              {bundle.generation_performance?.requested_service_tier ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Returned tier: {bundle.generation_performance?.returned_service_tier ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Provider: {ms(bundle.generation_performance?.latest_provider_ms)}
            </AppText>
            <AppText style={styles.row}>
              Latest total: {ms(bundle.generation_performance?.latest_total_ms)}
            </AppText>
            <AppText style={styles.row}>
              Validation: {ms(bundle.generation_performance?.latest_validation_ms)}
            </AppText>
            <AppText style={styles.row}>
              Attempts: {bundle.generation_performance?.latest_attempts ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Tokens: {bundle.generation_performance?.latest_input_tokens ?? '—'} in /{' '}
              {bundle.generation_performance?.latest_output_tokens ?? '—'} out
            </AppText>
            <AppText style={styles.meta}>
              Recent {bundle.generation_performance?.recent_count ?? 0}: median total{' '}
              {ms(bundle.generation_performance?.median_total_ms)} · median provider{' '}
              {ms(bundle.generation_performance?.median_provider_ms)} · min{' '}
              {ms(bundle.generation_performance?.min_total_ms)} · max{' '}
              {ms(bundle.generation_performance?.max_total_ms)}
            </AppText>
            <AppText style={styles.row}>
              Status: {bundle.next_win_preparation?.status ?? 'not_started'}
            </AppText>
            <AppText style={styles.row}>
              Trigger: {bundle.next_win_preparation?.trigger ?? '—'}
            </AppText>
            <AppText style={styles.meta}>
              {bundle.next_win_preparation?.model ?? '—'} ·{' '}
              {bundle.next_win_preparation?.prompt_version ?? '—'} ·{' '}
              {ms(bundle.next_win_preparation?.latency_ms)}
              {bundle.next_win_preparation?.error_code
                ? ` · ${bundle.next_win_preparation.error_code}`
                : ''}
            </AppText>
            <AppText style={styles.row}>
              Ready before Guide complete:{' '}
              {bundle.first_win_timing?.ready_before_guide == null
                ? '—'
                : bundle.first_win_timing.ready_before_guide
                  ? 'yes'
                  : 'no'}
            </AppText>
            <AppText style={styles.meta}>
              Raw model: {ms(bundle.first_win_timing?.raw_model_ms)} · visible wait{' '}
              {ms(bundle.first_win_timing?.visible_wait_ms)}
            </AppText>
          </QaGroup>

          <QaGroup title="LEARNER STATE">
            {bundle.snapshot.academic.length === 0 ? (
              <AppText style={styles.hint}>No academic state yet.</AppText>
            ) : (
              bundle.snapshot.academic.map((item) => (
                <AppText key={item.skill_code} style={styles.row}>
                  {item.domain_label} — {item.skill_name}: {item.band_label} (
                  {item.session_count} sessions)
                </AppText>
              ))
            )}
            {bundle.snapshot.growth.map((item) => (
              <AppText key={item.skill_code} style={styles.row}>
                {item.skill_name}: {item.latest_signal ?? 'not observed'}
              </AppText>
            ))}
          </QaGroup>

          <QaGroup title="SCHEDULER">
            <AppText style={styles.row}>
              Selected: {trace?.scheduler?.selected_goal ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              {typeof trace?.scheduler?.why_selected === 'string'
                ? trace.scheduler.why_selected
                : ''}
            </AppText>
            <AppText style={styles.meta}>
              Urgency: {trace?.scheduler?.urgency_class ?? '—'}
            </AppText>
            <AppText style={styles.meta}>
              Deferred: {(trace?.scheduler?.deferred_goals ?? []).join(', ') || '—'}
            </AppText>
            {bundle.next_preview ? (
              <>
                <AppText style={styles.row}>
                  Likely next: {bundle.next_preview.likely_parent_friendly_name}
                </AppText>
                <AppText style={styles.row}>
                  {bundle.next_preview.scheduler_reason ?? bundle.next_preview.reason}
                </AppText>
              </>
            ) : (
              <AppText style={styles.hint}>No preview until a profile exists.</AppText>
            )}
          </QaGroup>

          <QaGroup title="PLANNER">
            <AppText style={styles.meta}>
              Status: {trace?.generation_status ?? 'none'}
            </AppText>
            <AppText style={styles.row}>
              Target: {trace?.instruction_plan?.primary_skill ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Mode: {trace?.instruction_plan?.mode ?? '—'} scaffold{' '}
              {trace?.instruction_plan?.scaffold ?? '—'}
            </AppText>
            <AppText style={styles.meta}>{bundle.graph.strand || '—'}</AppText>
            {bundle.graph.nodes.map((node) => (
              <AppText key={node.skill_code} style={styles.row}>
                {node.is_target ? '→ ' : '  '}
                {node.parent_friendly_name} [{node.band}]
                {node.is_retained ? ' retained' : ''}
                {node.is_blocked ? ' blocked' : ''}
              </AppText>
            ))}
          </QaGroup>

          <QaGroup title="COACH PROTOCOL">
            <AppText style={styles.row}>
              Expected challenge: {trace?.coach_protocol?.expected_challenge ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Initial parent behavior:{' '}
              {trace?.coach_protocol?.initial_parent_behavior ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Prompt ceiling: {trace?.coach_protocol?.prompt_ceiling ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              If frustrated: {trace?.coach_protocol?.frustration_response ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Assessment boundary: {trace?.coach_protocol?.assessment_boundary ?? '—'}
            </AppText>
            <AppText style={styles.row}>{trace?.why_not?.why_this_coaching ?? ''}</AppText>
          </QaGroup>

          <QaGroup title="EVIDENCE">
            <AppText style={styles.row}>
              Summary: {trace?.weekly_context?.summary_version ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Wins this week: {trace?.weekly_context?.wins_this_week ?? '—'}
            </AppText>
            <AppText style={styles.row}>
              Next week focus: {trace?.weekly_context?.next_week_focus ?? '—'}
            </AppText>
            <AppText style={styles.row}>{trace?.why_not?.why_not_next_skill}</AppText>
            <AppText style={styles.row}>
              {trace?.why_not?.why_not_previous_skill}
            </AppText>
            <AppText style={styles.row}>{trace?.why_not?.why_not_second_goal}</AppText>
            <AppText style={styles.row}>{trace?.why_not?.why_not_review}</AppText>
            <AppText style={styles.row}>{trace?.why_not?.why_not_terminal}</AppText>
            <AppText style={styles.row}>
              {typeof trace?.next_win_implication === 'string'
                ? trace.next_win_implication
                : ''}
            </AppText>
          </QaGroup>
        </>
      ) : null}
    </Screen>
  );
}

function QaGroup({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card style={styles.group}>
      <TextButton
        label={open ? title : `${title} · show`}
        onPress={() => setOpen((value) => !value)}
      />
      {open ? <View style={styles.groupBody}>{children}</View> : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  hint: {
    color: colors.textSecondary,
    marginTop: space.sm,
  },
  error: {
    color: colors.danger,
    marginTop: space.sm,
  },
  actions: {
    gap: space.sm,
    marginVertical: space.lg,
  },
  meta: {
    color: colors.textSecondary,
    marginTop: 4,
  },
  row: {
    marginTop: 6,
  },
  group: {
    marginTop: space.md,
  },
  groupBody: {
    marginTop: space.sm,
  },
});
