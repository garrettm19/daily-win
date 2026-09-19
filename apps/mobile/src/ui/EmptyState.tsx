import { StyleSheet, View } from 'react-native';

import { colors } from '@/theme';
import { AppButton } from '@/ui/AppButton';
import { AppText } from '@/ui/AppText';
import { Icon, type IconName } from '@/ui/Icon';

export function EmptyState({
  title,
  body,
  icon = 'sparkles-outline',
  actionLabel,
  onAction,
}: {
  title: string;
  body?: string;
  icon?: IconName;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <View style={styles.wrap}>
      <Icon name={icon} size={28} color={colors.actionPrimary} />
      <AppText variant="cardTitle" style={styles.title}>
        {title}
      </AppText>
      {body ? <AppText variant="secondary">{body}</AppText> : null}
      {actionLabel && onAction ? (
        <AppButton label={actionLabel} onPress={onAction} />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 16,
    gap: 8,
    alignItems: 'flex-start',
  },
  title: {
    marginTop: 4,
  },
});
