import { Ionicons } from '@expo/vector-icons';
import { type ComponentType } from 'react';

import { colors } from '@/theme';

export type IconName =
  | 'sparkles'
  | 'sparkles-outline'
  | 'checkmark'
  | 'checkmark-circle'
  | 'book-outline'
  | 'walk-outline'
  | 'leaf-outline'
  | 'time-outline'
  | 'person-outline'
  | 'calendar-outline';

type GlyphProps = {
  name: IconName;
  size: number;
  color: string;
  accessibilityLabel?: string;
  accessibilityElementsHidden?: boolean;
  importantForAccessibility?: 'yes' | 'no-hide-descendants';
};

const Glyph = Ionicons as unknown as ComponentType<GlyphProps>;

export function Icon({
  name,
  size = 18,
  color = colors.actionPrimary,
  label,
}: {
  name: IconName;
  size?: number;
  color?: string;
  label?: string;
}) {
  return (
    <Glyph
      name={name}
      size={size}
      color={color}
      accessibilityLabel={label}
      accessibilityElementsHidden={label ? undefined : true}
      importantForAccessibility={label ? 'yes' : 'no-hide-descendants'}
    />
  );
}
