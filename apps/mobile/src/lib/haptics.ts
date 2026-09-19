import * as Haptics from 'expo-haptics';

async function run(task: () => Promise<unknown>): Promise<void> {
  try {
    await task();
  } catch {
    // Haptics are optional. Never block the parent flow.
  }
}

export function hapticSuccess(): void {
  void run(() =>
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success),
  );
}

export function hapticSelection(): void {
  void run(() => Haptics.selectionAsync());
}
