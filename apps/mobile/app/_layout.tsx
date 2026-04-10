import FontAwesome from '@expo/vector-icons/FontAwesome';
import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import 'react-native-reanimated';

import { useColorScheme } from '@/components/useColorScheme';
import { useAuthStore } from '../src/store/auth-store';
import { useNutritionStore } from '../src/store/nutrition-store';
import { useCoachingCasesStore } from '../src/store/coaching-cases-store';
import { useHIITProtocolsStore } from '../src/store/hiit-protocols-store';

export {
  ErrorBoundary,
} from 'expo-router';

export const unstable_settings = {
  initialRouteName: '(tabs)',
};

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [loaded, error] = useFonts({
    SpaceMono: require('../assets/fonts/SpaceMono-Regular.ttf'),
    ...FontAwesome.font,
  });

  const authStatus = useAuthStore((s) => s.status);
  const initialize = useAuthStore((s) => s.initialize);
  const hydrateNutrition = useNutritionStore((s) => s.hydrate);
  const hydrateCoachingCases = useCoachingCasesStore((s) => s.hydrate);
  const hydrateHIITProtocols = useHIITProtocolsStore((s) => s.hydrate);

  // Initialize auth session on app launch, and hydrate nutrition +
  // coaching-case + saved-HIIT-protocol state from secureStorage in
  // parallel so today's logged fuel + daily targets + any un-captured
  // "Ask ChatGPT" follow-up draft + the named HIIT protocol library
  // all survive app kill. Each runs independently — failures in any
  // one must not block the others.
  useEffect(() => {
    initialize();
    hydrateNutrition();
    hydrateCoachingCases();
    hydrateHIITProtocols();
  }, [initialize, hydrateNutrition, hydrateCoachingCases, hydrateHIITProtocols]);

  useEffect(() => {
    if (error) throw error;
  }, [error]);

  // Hide splash once fonts loaded AND auth check complete.
  useEffect(() => {
    if (loaded && authStatus !== 'loading') {
      SplashScreen.hideAsync();
    }
  }, [loaded, authStatus]);

  if (!loaded || authStatus === 'loading') {
    return null;
  }

  return <RootLayoutNav />;
}

function RootLayoutNav() {
  const colorScheme = useColorScheme();

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: 'modal' }} />
        <Stack.Screen
          name="timer"
          options={{
            presentation: 'fullScreenModal',
            headerShown: false,
            gestureEnabled: false,
          }}
        />
      </Stack>
    </ThemeProvider>
  );
}
