import FontAwesome from '@expo/vector-icons/FontAwesome';
import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { useFonts } from 'expo-font';
import { Stack, usePathname, useRouter } from 'expo-router';
import { Pressable } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useColorScheme } from '@/components/useColorScheme';
import { useAuthStore } from '../src/store/auth-store';
import { useNutritionStore } from '../src/store/nutrition-store';
import { useCoachingCasesStore } from '../src/store/coaching-cases-store';
import { useHIITProtocolsStore } from '../src/store/hiit-protocols-store';
import { useReferenceProgressStore } from '../src/store/reference-progress-store';
import { usePreferencesStore } from '../src/store/preferences-store';
import { useTrainingStore } from '../src/store/training-store';
import { useFeedbackStore } from '../src/store/feedback-store';
import { useConsentStore } from '../src/store/consent-store';
import { useTierStore } from '../src/store/tier-store';
import { useHealthStore } from '../src/store/health-store';
import { useNutritionEvidenceStore } from '../src/store/nutrition-evidence-store';
import { useHIITWorkoutStore } from '../src/store/hiit-workout-store';
import { AppTour, useAppTourStore } from '../src/components/AppTour';
import { FeedbackFab } from '../src/components/FeedbackFab';

export {
  ErrorBoundary,
} from 'expo-router';

export const unstable_settings = {
  initialRouteName: '(tabs)',
};

SplashScreen.preventAutoHideAsync();

function hydrateLaunchStores(tasks: Array<() => Promise<void> | void>) {
  for (const task of tasks) {
    void task();
  }
}

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
  const hydrateReferenceProgress = useReferenceProgressStore((s) => s.hydrate);
  const hydratePreferences = usePreferencesStore((s) => s.hydrate);
  const hydrateTraining = useTrainingStore((s) => s.hydrate);
  const hydrateFeedback = useFeedbackStore((s) => s.hydrate);
  const hydrateConsent = useConsentStore((s) => s.hydrate);
  const hydrateTier = useTierStore((s) => s.hydrate);
  const hydrateHealthMeta = useHealthStore((s) => s.hydrateMeta);
  const hydrateNutritionEvidence = useNutritionEvidenceStore((s) => s.hydrate);
  const hydrateHIITWorkouts = useHIITWorkoutStore((s) => s.hydrate);
  const hydrateTour = useAppTourStore((s) => s.hydrate);

  // Initialize auth session on app launch, and hydrate all stores
  // from secureStorage in parallel. Each runs independently —
  // failures in any one must not block the others.
  useEffect(() => {
    initialize();
    hydrateLaunchStores([
      hydrateNutrition,
      hydrateCoachingCases,
      hydrateHIITProtocols,
      hydrateReferenceProgress,
      hydratePreferences,
      hydrateTraining,
      hydrateFeedback,
      hydrateConsent,
      hydrateTier,
      hydrateHealthMeta,
      hydrateNutritionEvidence,
      hydrateHIITWorkouts,
      hydrateTour,
    ]);
  }, [
    initialize,
    hydrateNutrition,
    hydrateCoachingCases,
    hydrateHIITProtocols,
    hydrateReferenceProgress,
    hydratePreferences,
    hydrateTraining,
    hydrateFeedback,
    hydrateConsent,
    hydrateTier,
    hydrateHealthMeta,
    hydrateNutritionEvidence,
    hydrateHIITWorkouts,
    hydrateTour,
  ]);

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
  const tourVisible = useAppTourStore((s) => s.visible && s.ready);
  const tourDismiss = useAppTourStore((s) => s.dismiss);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: 'modal' }} />
        <Stack.Screen
          name="ai-chat"
          options={{
            presentation: 'modal',
            headerShown: false,
            gestureEnabled: true,
          }}
        />
        <Stack.Screen
          name="timer"
          options={{
            presentation: 'fullScreenModal',
            headerShown: false,
            gestureEnabled: false,
          }}
        />
        <Stack.Screen
          name="feedback-viewer"
          options={{
            title: 'Recent feedback',
            headerBackTitle: 'Settings',
          }}
        />
      </Stack>
      {!tourVisible && <AiLauncherFab />}
      {!tourVisible && <FeedbackFab />}
      <AppTour visible={tourVisible} onDismiss={tourDismiss} />
    </ThemeProvider>
  );
}

/** Global AI launcher FAB — visible on all tab screens. */
function AiLauncherFab() {
  const router = useRouter();
  const pathname = usePathname();
  const insets = useSafeAreaInsets();
  // Hide the FAB when the AI chat modal is already open
  const isModalOpen = pathname === '/ai-chat' || pathname === '/timer';
  if (isModalOpen) return null;

  return (
    <Pressable
      style={{
        position: 'absolute',
        bottom: Math.max(insets.bottom, 10) + 72,
        left: 16,
        minWidth: 56,
        height: 48,
        borderRadius: 24,
        backgroundColor: '#d4e157',
        paddingHorizontal: 14,
        gap: 6,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 3 },
        shadowOpacity: 0.35,
        shadowRadius: 6,
        elevation: 6,
        zIndex: 999,
      }}
      accessibilityRole="button"
      accessibilityLabel="Open AI coach"
      onPress={() => router.push('/ai-chat')}>
      <FontAwesome name="android" size={16} color="#0b0b0b" />
      <FontAwesome name="comment" size={14} color="#0b0b0b" />
    </Pressable>
  );
}
