import { Pressable, StyleSheet, Text } from 'react-native';
import { useRouter } from 'expo-router';

import { colors, type } from '@/theme';

export function HeaderHomeButton() {
  const router = useRouter();

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel="Home"
      hitSlop={8}
      onPress={() => {
        router.dismissTo('/');
      }}
      style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
      <Text style={styles.label}>Home</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: 44,
    minWidth: 44,
    paddingHorizontal: 8,
    justifyContent: 'center',
    alignItems: 'flex-end',
  },
  pressed: {
    opacity: 0.7,
  },
  label: {
    ...type.bodyEmphasized,
    color: colors.actionPrimary,
  },
});
