import { StyleSheet, View } from 'react-native';

import { ChoiceChip } from '@/ui/ChoiceChip';

type ChipPickerProps = {
  options: string[];
  selected: string[];
  onToggle: (value: string) => void;
  max?: number;
};

export function ChipPicker({ options, selected, onToggle, max }: ChipPickerProps) {
  return (
    <View style={styles.row}>
      {options.map((option) => {
        const active = selected.some(
          (item) => item.toLowerCase() === option.toLowerCase(),
        );
        const atMax = max !== undefined && selected.length >= max && !active;
        return (
          <ChoiceChip
            key={option}
            label={option}
            selected={active}
            disabled={atMax}
            onPress={() => onToggle(option)}
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
});
