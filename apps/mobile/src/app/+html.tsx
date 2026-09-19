import { type ReactNode } from 'react';
import { ScrollViewStyleReset } from 'expo-router/html';

import { colors } from '@/theme';

export default function Root({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, shrink-to-fit=no"
        />
        <ScrollViewStyleReset />
        <style
          dangerouslySetInnerHTML={{
            __html: `html, body, #root { background-color: ${colors.background}; }`,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
