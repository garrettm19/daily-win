import { StyleSheet, Text } from 'react-native';

import { diagnosticLabel, type ApiErrorKind } from '@/lib/api/parentErrors';
import { isParentPilotView } from '@/lib/pilotView';
import { colors, type } from '@/theme';

export function DevError({
  code,
  kind,
}: {
  code?: string | null;
  kind?: ApiErrorKind | null;
}) {
  if (!__DEV__ || isParentPilotView()) {
    return null;
  }
  const diagnostic = diagnosticLabel(kind);
  if (!code && !diagnostic) {
    return null;
  }
  return (
    <Text style={styles.text}>
      {diagnostic ? diagnostic : null}
      {diagnostic && code ? ' · ' : null}
      {code ? `Dev error: ${code}` : null}
    </Text>
  );
}

const styles = StyleSheet.create({
  text: {
    ...type.caption,
    marginTop: 6,
    color: colors.textSecondary,
  },
});
