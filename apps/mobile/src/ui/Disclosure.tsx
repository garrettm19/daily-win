import { type ReactNode, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { space } from '@/theme';
import { TextButton } from '@/ui/TextButton';

export function Disclosure({
  label,
  openLabel,
  children,
}: {
  label: string;
  openLabel?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <View style={styles.wrap}>
      <TextButton
        label={open ? (openLabel ?? `Hide ${label.toLowerCase()}`) : label}
        onPress={() => setOpen((value) => !value)}
      />
      {open ? <View style={styles.body}>{children}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: space.sm,
  },
  body: {
    marginTop: space.xs,
    gap: space.sm,
  },
});
