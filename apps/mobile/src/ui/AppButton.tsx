import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { colors, motion, radius, type } from '@/theme';

type AppButtonProps = {
  label: string;
  onPress: () => void;
  accessibilityLabel?: string;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  loading?: boolean;
};

export function AppButton({
  label,
  onPress,
  accessibilityLabel,
  variant = 'primary',
  disabled = false,
  loading = false,
}: AppButtonProps) {
  const inactive = disabled || loading;
  const onPrimary = variant === 'primary' || variant === 'danger';

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={{ disabled: inactive, busy: loading }}
      disabled={inactive}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        variant === 'primary' && styles.primary,
        variant === 'secondary' && styles.secondary,
        variant === 'danger' && styles.danger,
        inactive && styles.disabled,
        pressed && !inactive && styles.pressed,
        pressed && !inactive && variant === 'primary' && styles.primaryPressed,
      ]}>
      <View style={styles.row}>
        {loading ? (
          <ActivityIndicator
            color={onPrimary ? colors.textOnAction : colors.actionPrimary}
            style={styles.spinner}
            accessibilityLabel="Loading"
          />
        ) : null}
        <Text
          style={[
            type.button,
            variant === 'secondary' ? styles.secondaryLabel : styles.onActionLabel,
          ]}>
          {label}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 52,
    minWidth: 44,
    marginTop: 16,
    paddingHorizontal: 18,
    borderRadius: radius.button,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primary: {
    backgroundColor: colors.actionPrimary,
  },
  primaryPressed: {
    backgroundColor: colors.actionPrimaryPressed,
  },
  secondary: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  danger: {
    backgroundColor: colors.danger,
  },
  disabled: {
    opacity: 0.45,
  },
  pressed: {
    opacity: 0.88,
    transform: [{ scale: motion.pressScale }],
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  spinner: {
    marginRight: 2,
  },
  onActionLabel: {
    color: colors.textOnAction,
  },
  secondaryLabel: {
    color: colors.actionPrimary,
  },
});
