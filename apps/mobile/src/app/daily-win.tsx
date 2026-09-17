import { type ReactNode, useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';

import { fetchLatestDemoDailyWin } from '@/lib/api/demo';
import type { DailyWinSegment, DemoDailyWin } from '@/lib/api/types';

const MATERIAL_LABELS: Record<string, string> = {
  NONE: 'None needed',
  PAPER: 'Paper',
  PENCIL: 'Pencil',
  CRAYONS_OR_MARKERS: 'Crayons or markers',
  TAPE: 'Tape',
  INDEX_CARDS: 'Index cards',
  PLASTIC_CUPS: 'Plastic cups',
  BLOCKS: 'Blocks',
  BOOK: 'Book',
  COINS: 'Coins',
  SOFT_BALL: 'Soft ball',
  TIMER: 'Timer',
};

export default function DailyWinScreen() {
  const router = useRouter();
  const [dailyWin, setDailyWin] = useState<DemoDailyWin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [started, setStarted] = useState(false);
  const generationRef = useRef(0);

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

  return (
    <SafeAreaView style={styles.safeArea}>
      {loading ? (
        <Centered
          title={"Loading today's Daily Win"}
          body="Pulling the saved activity from Daily Win."
        />
      ) : null}
      {!loading && error ? (
        <Centered
          title={"Couldn't load the Daily Win"}
          body={error}
          actionLabel="Go back"
          onAction={() => router.back()}
        />
      ) : null}
      {!loading && dailyWin && !started ? (
        <Briefing dailyWin={dailyWin} onStart={() => setStarted(true)} />
      ) : null}
      {!loading && dailyWin && started ? <Activity dailyWin={dailyWin} /> : null}
    </SafeAreaView>
  );
}

function Centered({
  title,
  body,
  actionLabel,
  onAction,
}: {
  title: string;
  body: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <View style={styles.centered}>
      <Text style={styles.brand}>Daily Win</Text>
      <Text style={styles.statusTitle}>{title}</Text>
      <Text style={styles.statusBody}>{body}</Text>
      {actionLabel && onAction ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={actionLabel}
          onPress={onAction}
          style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
          <Text style={styles.buttonLabel}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function Briefing({
  dailyWin,
  onStart,
}: {
  dailyWin: DemoDailyWin;
  onStart: () => void;
}) {
  const materials = dailyWin.content.materials
    .filter((item) => item !== 'NONE')
    .map((item) => MATERIAL_LABELS[item] ?? item);

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.brand}>Daily Win</Text>
      <Text style={styles.title}>{dailyWin.title}</Text>
      <Text style={styles.meta}>
        Focus: {dailyWin.primary_skill_display_name} · About{' '}
        {dailyWin.duration_minutes} minutes
      </Text>

      {dailyWin.content.adaptation_summary ? (
        <View style={styles.changeCard}>
          <Text style={styles.changeEyebrow}>What changed today</Text>
          <Text style={styles.changeBody}>{dailyWin.content.adaptation_summary}</Text>
        </View>
      ) : null}

      <Section title={`Why this fits ${dailyWin.child_nickname}`}>
        <Text style={styles.body}>{dailyWin.content.personalization_summary}</Text>
      </Section>

      <Section title="Before you start">
        <Text style={styles.body}>
          {materials.length > 0 ? materials.join(', ') : 'No extra materials.'}
        </Text>
      </Section>

      <Section title="Parent briefing">
        <LabelBlock label="Purpose" text={dailyWin.content.parent_briefing.purpose} />
        <LabelBlock
          label="How to coach"
          text={dailyWin.content.parent_briefing.how_to_coach}
        />
        <LabelBlock
          label="Watch for"
          text={dailyWin.content.parent_briefing.watch_for}
        />
        <LabelBlock label="Avoid" text={dailyWin.content.parent_briefing.avoid} />
      </Section>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Start with ${dailyWin.child_nickname}`}
        onPress={onStart}
        style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
        <Text style={styles.buttonLabel}>{`Start with ${dailyWin.child_nickname}`}</Text>
      </Pressable>
    </ScrollView>
  );
}

function Activity({ dailyWin }: { dailyWin: DemoDailyWin }) {
  const router = useRouter();
  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.brand}>Daily Win</Text>
      <Text style={styles.title}>{dailyWin.title}</Text>
      <Text style={styles.meta}>Do this together, then continue offline.</Text>

      {dailyWin.content.adaptation_summary ? (
        <View style={styles.changeCard}>
          <Text style={styles.changeEyebrow}>What changed today</Text>
          <Text style={styles.changeBody}>{dailyWin.content.adaptation_summary}</Text>
        </View>
      ) : null}

      {dailyWin.content.segments.map((segment, index) => (
        <SegmentCard
          key={`${segment.type}-${index}`}
          index={index + 1}
          segment={segment}
        />
      ))}

      <Section title={"If it's too easy"}>
        <Text style={styles.body}>{dailyWin.content.adaptations.if_too_easy}</Text>
      </Section>
      <Section title={"If it's too hard"}>
        <Text style={styles.body}>{dailyWin.content.adaptations.if_too_hard}</Text>
      </Section>
      <Section title="What success looks like">
        {dailyWin.content.success_checks.map((item) => (
          <Text key={item} style={styles.listItem}>
            {item}
          </Text>
        ))}
      </Section>
      <Section title="What to notice">
        <Text style={styles.body}>{dailyWin.content.observation_focus}</Text>
      </Section>

      {dailyWin.has_feedback ? (
        <View style={styles.comingCard}>
          <Text style={styles.comingTitle}>Reflection saved</Text>
          <Text style={styles.body}>
            Daily Win already has your report for this activity.
          </Text>
        </View>
      ) : (
        <View style={styles.comingCard}>
          <Text style={styles.comingTitle}>How did it go?</Text>
          <Text style={styles.body}>
            A short reflection helps Daily Win adapt the next activity.
          </Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Reflect on this Win"
            onPress={() => router.push('/reflect')}
            style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
            <Text style={styles.buttonLabel}>Reflect on this Win</Text>
          </Pressable>
        </View>
      )}
    </ScrollView>
  );
}

function SegmentCard({
  index,
  segment,
}: {
  index: number;
  segment: DailyWinSegment;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>
        {index}. {segment.type}
      </Text>
      <Text style={styles.goalName}>{segment.title}</Text>
      <Text style={styles.meta}>About {segment.minutes} minutes</Text>
      {segment.steps.map((step) => (
        <Text key={step} style={styles.listItem}>
          {step}
        </Text>
      ))}
      <Text style={[styles.note, styles.parentRole]}>
        Parent role: {segment.parent_role}
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

function LabelBlock({ label, text }: { label: string; text: string }) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <Text style={styles.body}>{text}</Text>
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
  body: {
    fontSize: 16,
    lineHeight: 24,
    color: '#1C1917',
  },
  listItem: {
    marginTop: 8,
    fontSize: 16,
    lineHeight: 24,
    color: '#1C1917',
  },
  field: {
    marginBottom: 14,
  },
  fieldLabel: {
    marginBottom: 6,
    fontSize: 15,
    fontWeight: '600',
    color: '#1C1917',
  },
  note: {
    fontSize: 15,
    lineHeight: 22,
    color: '#4A4541',
  },
  parentRole: {
    marginTop: 12,
  },
  goalName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1C1917',
  },
  button: {
    alignSelf: 'flex-start',
    marginTop: 24,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 12,
    backgroundColor: '#2C4A3E',
  },
  buttonLabel: {
    color: '#F8F6F1',
    fontSize: 16,
    fontWeight: '600',
  },
  pressed: {
    opacity: 0.88,
  },
  comingCard: {
    marginTop: 28,
    padding: 20,
    borderRadius: 18,
    backgroundColor: '#EAE4DA',
  },
  comingTitle: {
    marginBottom: 8,
    fontSize: 18,
    fontWeight: '600',
    color: '#1C1917',
  },
  changeCard: {
    marginTop: 20,
    padding: 20,
    borderRadius: 18,
    backgroundColor: '#2C4A3E',
  },
  changeEyebrow: {
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: '#C5D4CC',
  },
  changeBody: {
    marginTop: 8,
    fontSize: 17,
    lineHeight: 24,
    fontWeight: '600',
    color: '#F8F6F1',
  },
});
