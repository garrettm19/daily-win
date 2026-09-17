import { type ReactNode } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useDemoChildProfile } from '@/hooks/useDemoChildProfile';
import type { DemoChildProfile, DemoGoalSummary } from '@/lib/api/types';

export default function Index() {
  const { profile, error, loading, retry } = useDemoChildProfile();

  return (
    <SafeAreaView style={styles.safeArea}>
      {loading ? <LoadingState /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={retry} /> : null}
      {!loading && profile ? <ProfileHome profile={profile} /> : null}
    </SafeAreaView>
  );
}

function LoadingState() {
  return (
    <View style={styles.centered}>
      <Text style={styles.brand}>Daily Win</Text>
      <Text style={styles.statusTitle}>{"Loading this child's profile"}</Text>
      <Text style={styles.statusBody}>
        Pulling the latest parent-reported baseline and goals from Daily Win.
      </Text>
    </View>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <View style={styles.centered}>
      <Text style={styles.brand}>Daily Win</Text>
      <Text style={styles.statusTitle}>{"Couldn't load the profile"}</Text>
      <Text style={styles.statusBody}>{message}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Retry loading the child profile"
        onPress={onRetry}
        style={({ pressed }) => [styles.retryButton, pressed && styles.pressed]}>
        <Text style={styles.retryLabel}>Retry</Text>
      </Pressable>
    </View>
  );
}

function ProfileHome({ profile }: { profile: DemoChildProfile }) {
  const focusGoal = profile.goals[0];

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.brand}>Daily Win</Text>
      <Text style={styles.nickname}>{profile.child.nickname}</Text>
      <Text style={styles.meta}>
        Age {profile.baseline.age_years} · Grade {profile.baseline.grade}
      </Text>

      {focusGoal ? <FocusCard goal={focusGoal} /> : null}

      <Section title="Profile">
        <Field label="Interests" values={profile.baseline.interests} />
        <Field label="Strengths" values={profile.baseline.strengths} />
        <Field
          label="Current challenges"
          values={profile.baseline.current_difficulties}
        />
        <Field label="What motivates" values={profile.baseline.motivators} />
        {profile.baseline.response_to_difficulty ? (
          <Text style={styles.note}>
            When something is hard: {profile.baseline.response_to_difficulty}
          </Text>
        ) : null}
      </Section>

      <Section title="Goals">
        {profile.goals.map((goal) => (
          <View key={goal.skill_code} style={styles.goalRow}>
            <Text style={styles.goalPriority}>{goal.priority}</Text>
            <View style={styles.goalCopy}>
              <Text style={styles.goalName}>{goal.display_name}</Text>
              <Text style={styles.goalDomain}>{formatDomain(goal.domain)}</Text>
            </View>
          </View>
        ))}
      </Section>

      <Section title="Activity preference">
        <Text style={styles.body}>
          About {profile.baseline.preferred_activity_minutes} minutes
        </Text>
      </Section>

      <View style={styles.comingCard}>
        <Text style={styles.comingEyebrow}>{"Today's Daily Win"}</Text>
        <Text style={styles.comingTitle}>Generation is coming next.</Text>
        <Text style={styles.comingBody}>
          You will get a short activity and a parent briefing designed to do
          together, then continue offline.
        </Text>
      </View>
    </ScrollView>
  );
}

function FocusCard({ goal }: { goal: DemoGoalSummary }) {
  return (
    <View style={styles.focusCard}>
      <Text style={styles.focusEyebrow}>{"Today's focus"}</Text>
      <Text style={styles.focusTitle}>{goal.display_name}</Text>
      <Text style={styles.focusBody}>
        The north-star goal for this child, based on what you reported.
      </Text>
    </View>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Field({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) {
    return null;
  }

  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={styles.chipRow}>
        {values.map((value) => (
          <View key={value} style={styles.chip}>
            <Text style={styles.chipLabel}>{value}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function formatDomain(domain: string): string {
  if (!domain) {
    return domain;
  }
  return domain.charAt(0).toUpperCase() + domain.slice(1).toLowerCase();
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
  nickname: {
    marginTop: 10,
    fontSize: 34,
    lineHeight: 40,
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
  retryButton: {
    alignSelf: 'flex-start',
    marginTop: 24,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 12,
    backgroundColor: '#2C4A3E',
  },
  retryLabel: {
    color: '#F8F6F1',
    fontSize: 16,
    fontWeight: '600',
  },
  pressed: {
    opacity: 0.88,
  },
  focusCard: {
    marginTop: 28,
    padding: 20,
    borderRadius: 18,
    backgroundColor: '#2C4A3E',
  },
  focusEyebrow: {
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: '#C5D4CC',
  },
  focusTitle: {
    marginTop: 8,
    fontSize: 26,
    fontWeight: '700',
    color: '#F8F6F1',
  },
  focusBody: {
    marginTop: 8,
    fontSize: 15,
    lineHeight: 22,
    color: '#D7E2DC',
  },
  section: {
    marginTop: 28,
    padding: 20,
    borderRadius: 18,
    backgroundColor: '#FFFcf7',
    borderWidth: 1,
    borderColor: '#E6E0D6',
  },
  sectionTitle: {
    marginBottom: 14,
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: '#6F6A64',
  },
  field: {
    marginBottom: 16,
  },
  fieldLabel: {
    marginBottom: 8,
    fontSize: 15,
    fontWeight: '600',
    color: '#1C1917',
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 999,
    backgroundColor: '#EDE8E0',
  },
  chipLabel: {
    fontSize: 14,
    color: '#3F3A36',
  },
  note: {
    fontSize: 15,
    lineHeight: 22,
    color: '#4A4541',
  },
  goalRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 14,
  },
  goalPriority: {
    width: 28,
    fontSize: 16,
    fontWeight: '700',
    color: '#2C4A3E',
  },
  goalCopy: {
    flex: 1,
  },
  goalName: {
    fontSize: 17,
    fontWeight: '600',
    color: '#1C1917',
  },
  goalDomain: {
    marginTop: 2,
    fontSize: 13,
    color: '#6F6A64',
  },
  body: {
    fontSize: 16,
    color: '#1C1917',
  },
  comingCard: {
    marginTop: 28,
    padding: 20,
    borderRadius: 18,
    backgroundColor: '#EAE4DA',
  },
  comingEyebrow: {
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: '#6F6A64',
  },
  comingTitle: {
    marginTop: 8,
    fontSize: 18,
    fontWeight: '600',
    color: '#1C1917',
  },
  comingBody: {
    marginTop: 8,
    fontSize: 15,
    lineHeight: 22,
    color: '#6F6A64',
  },
});
