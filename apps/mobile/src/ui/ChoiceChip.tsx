import { Pressable, StyleSheet, Text, View } from 'react-native';

import { hapticSelection } from '@/lib/haptics';
import { colors, motion, radius, type } from '@/theme';
import { Icon } from '@/ui/Icon';

export function ChoiceChip({
  label,
  selected,
  onPress,
  disabled = false,
  block = false,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
  disabled?: boolean;
  block?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected, disabled }}
      accessibilityLabel={selected ? `${label}, selected` : label}
      disabled={disabled}
      onPress={() => {
        hapticSelection();
        onPress();
      }}
      style={({ pressed }) => [
        styles.chip,
        block && styles.block,
        selected && styles.selected,
        disabled && styles.disabled,
        pressed && !disabled && styles.pressed,
      ]}>
      <View style={styles.row}>
        {selected ? (
          <Icon name="checkmark" size={16} color={colors.actionPrimary} />
        ) : null}
        <Text style={[styles.label, selected && styles.selectedLabel]}>{label}</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    minHeight: 44,
    minWidth: 44,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: radius.chip,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.borderSubtle,
    justifyContent: 'center',
  },
  block: {
    alignSelf: 'stretch',
  },
  selected: {
    backgroundColor: colors.actionPrimarySoft,
    borderColor: colors.actionPrimary,
    borderWidth: 2,
  },
  disabled: {
    opacity: 0.4,
  },
  pressed: {
    opacity: 0.86,
    transform: [{ scale: motion.pressScale }],
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexShrink: 1,
  },
  label: {
    ...type.secondary,
    color: colors.textPrimary,
    fontWeight: '500',
    flexShrink: 1,
  },
  selectedLabel: {
    color: colors.textPrimary,
    fontWeight: '600',
  },
});
