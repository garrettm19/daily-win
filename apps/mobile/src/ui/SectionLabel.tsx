import { type TextStyle } from 'react-native';

import { space } from '@/theme';
import { AppText } from '@/ui/AppText';

export function SectionLabel({
  children,
  style,
}: {
  children: string;
  style?: TextStyle;
}) {
  return (
    <AppText
      variant="sectionLabel"
      style={[{ marginTop: space.md, marginBottom: space.xs }, style]}>
      {children}
    </AppText>
  );
}
