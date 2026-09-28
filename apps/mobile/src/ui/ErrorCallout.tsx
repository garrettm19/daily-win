import { type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { colors, radius, space } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { DevError } from '@/ui/DevError';
import type { ApiErrorKind } from '@/lib/api/parentErrors';

export function ErrorCallout({
  message,
  errorCode,
  errorKind,
  onRetry,
  children,
}: {
  message: string;
  errorCode?: string | null;
  errorKind?: ApiErrorKind | null;
  onRetry?: () => void;
  children?: ReactNode;
}) {
  return (
    <View style={styles.wrap} accessibilityRole="alert">
      <View style={styles.bar} />
      <AppText variant="bodyEmphasized" style={styles.message}>
        {message}
      </AppText>
      <DevError code={errorCode} kind={errorKind} />
      {onRetry ? (
        <AppButton label="Try again" variant="secondary" onPress={onRetry} />
      ) : null}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: space.md,
    padding: space.md,
    borderRadius: radius.card,
    backgroundColor: colors.dangerSoft,
    borderWidth: 1,
    borderColor: colors.dangerSoft,
  },
  bar: {
    width: 28,
    height: 3,
    borderRadius: 2,
    backgroundColor: colors.danger,
    marginBottom: 8,
  },
  message: {
    color: colors.textPrimary,
  },
});
