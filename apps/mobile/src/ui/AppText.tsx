import { Text, type TextProps } from 'react-native';

import { type } from '@/theme';

type AppTextVariant = keyof typeof type;

export function AppText({
  variant = 'body',
  children,
  style,
  ...rest
}: TextProps & {
  variant?: AppTextVariant;
}) {
  return (
    <Text
      {...rest}
      style={[type[variant], { flexShrink: 1 }, style]}>
      {children}
    </Text>
  );
}
