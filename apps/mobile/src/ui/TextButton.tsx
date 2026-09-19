import { Pressable, StyleSheet, Text } from 'react-native';

import { colors, motion, type } from '@/theme';

export function TextButton({
  label,
  onPress,
  disabled = false,
  accessibilityLabel,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  accessibilityLabel?: string;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={{ disabled }}
      disabled={disabled}
      hitSlop={8}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        disabled && styles.disabled,
        pressed && !disabled && styles.pressed,
      ]}>
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 44,
    minWidth: 44,
    justifyContent: 'center',
    alignSelf: 'flex-start',
    paddingVertical: 8,
  },
  disabled: {
    opacity: 0.45,
  },
  pressed: {
    opacity: 0.7,
    transform: [{ scale: motion.pressScale }],
  },
  label: {
    ...type.bodyEmphasized,
    color: colors.actionPrimary,
  },
});
