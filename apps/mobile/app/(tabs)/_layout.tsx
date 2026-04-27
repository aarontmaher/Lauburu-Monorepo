import React from 'react';
import FontAwesome from '@expo/vector-icons/FontAwesome';
import { Tabs } from 'expo-router';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';

function TabBarIcon(props: {
  name: React.ComponentProps<typeof FontAwesome>['name'];
  color: string;
}) {
  return <FontAwesome size={24} style={{ marginBottom: -3 }} {...props} />;
}

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const colors = Colors[colorScheme ?? 'dark'];

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.tint,
        tabBarInactiveTintColor: colors.tabIconDefault,
        tabBarStyle: {
          backgroundColor: colors.card,
          borderTopColor: colors.border,
        },
        headerStyle: { backgroundColor: colors.card },
        headerTintColor: colors.text,
        headerShadowVisible: false,
      }}>
      {/* Daily workflow tabs */}
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ color }) => <TabBarIcon name="home" color={color} />,
        }}
      />
      <Tabs.Screen
        name="train"
        options={{
          title: 'Train',
          tabBarIcon: ({ color }) => <TabBarIcon name="plus-circle" color={color} />,
        }}
      />
      <Tabs.Screen
        name="health"
        options={{
          title: 'Health',
          tabBarIcon: ({ color }) => <TabBarIcon name="heartbeat" color={color} />,
        }}
      />
      <Tabs.Screen
        name="feedback"
        options={{
          title: 'Check-in',
          tabBarIcon: ({ color }) => <TabBarIcon name="check-circle" color={color} />,
        }}
      />
      <Tabs.Screen
        name="map-3d"
        options={{
          title: 'Map',
          headerShown: false,
          tabBarIcon: ({ color }) => <TabBarIcon name="globe" color={color} />,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          tabBarIcon: ({ color }) => <TabBarIcon name="cog" color={color} />,
        }}
      />
      {/* Hidden tabs — still navigable but not in tab bar */}
      <Tabs.Screen
        name="suggest"
        options={{ href: null }}
      />
      <Tabs.Screen
        name="control"
        options={{ href: null }}
      />
      <Tabs.Screen
        name="reference"
        options={{ href: null, title: 'Reference' }}
      />
      <Tabs.Screen
        name="syllabus"
        options={{ href: null, title: 'Belt syllabus' }}
      />
      <Tabs.Screen
        name="coaching-history"
        options={{ href: null, title: 'Coaching history' }}
      />
    </Tabs>
  );
}
