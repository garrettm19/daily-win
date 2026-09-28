import { Nunito_700Bold, Nunito_800ExtraBold, useFonts } from '@expo-google-fonts/nunito';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { startAdvisoryHealthProbe } from '@/lib/api/health';
import { hydratePilotView, setPilotViewStore } from '@/lib/pilotView';
import { colors, fontFamily } from '@/theme';
import { HeaderHomeButton } from '@/ui/HeaderHomeButton';

void SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Nunito_700Bold,
    Nunito_800ExtraBold,
  });

  useEffect(() => {
    void SplashScreen.hideAsync();
  }, [fontsLoaded]);

  useEffect(() => {
    if (__DEV__) {
      startAdvisoryHealthProbe();
      void (async () => {
        try {
          const SecureStore = await import('expo-secure-store');
          setPilotViewStore({
            getItem: (key) => SecureStore.getItemAsync(key),
            setItem: (key, value) => SecureStore.setItemAsync(key, value),
          });
          await hydratePilotView();
        } catch {
          return;
        }
      })();
    }
  }, []);

  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.background },
          headerTintColor: colors.textPrimary,
          headerTitleStyle: {
            fontFamily: fontFamily.heading,
            fontSize: 17,
            color: colors.textPrimary,
          },
          headerShadowVisible: false,
          headerBackTitle: 'Back',
          contentStyle: { backgroundColor: colors.background },
          animation: 'default',
        }}>
        <Stack.Screen name="index" options={{ headerShown: false, title: 'Home' }} />
        <Stack.Screen
          name="setup"
          options={{
            title: 'Create a profile',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="guide"
          options={{
            title: 'How Daily Win works',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="profile"
          options={{
            title: 'Profile',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="profile-edit"
          options={{
            title: 'Edit profile',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="progress"
          options={{
            title: 'Progress',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="history"
          options={{
            title: 'Recent Daily Wins',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="daily-win"
          options={{
            title: 'Daily Win',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="reflect"
          options={{
            title: 'How did it go?',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="insight"
          options={{
            title: 'Result',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="test-feedback"
          options={{
            title: 'Test feedback',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="weekly-report"
          options={{
            title: 'This week',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
        <Stack.Screen
          name="learning-qa"
          options={{
            title: 'Learning QA',
            headerRight: () => <HeaderHomeButton />,
          }}
        />
      </Stack>
    </>
  );
}
