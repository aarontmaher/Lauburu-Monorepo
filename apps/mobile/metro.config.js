// Learn more https://docs.expo.io/guides/customizing-metro
const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

// Find the workspace root (monorepo)
const workspaceRoot = path.resolve(__dirname, '../..');

const config = getDefaultConfig(__dirname);

// Watch the workspace root for shared packages
config.watchFolders = [workspaceRoot];

// Resolve packages from workspace root node_modules
config.resolver.nodeModulesPaths = [
  path.resolve(workspaceRoot, 'node_modules'),
  path.resolve(__dirname, 'node_modules'),
];

// Block native health packages from being bundled in Expo Go.
// These use NitroModules which crash immediately in Expo Go.
// In dev builds (expo prebuild + expo run:ios), remove this block
// or set EXPO_GO=0.
//
// Metro evaluates the entire module graph at bundle time, so even
// a lazy require() inside a function body gets resolved and bundled.
// The only way to prevent the crash is to prevent Metro from seeing
// the native package at all.
const NATIVE_HEALTH_PACKAGES = [
  '@kingstinct/react-native-healthkit',
  'react-native-health-connect',
  'react-native-nitro-modules',
];

const originalResolveRequest = config.resolver.resolveRequest;

config.resolver.resolveRequest = (context, moduleName, platform) => {
  // Block native health packages — they crash in Expo Go
  if (NATIVE_HEALTH_PACKAGES.some((pkg) => moduleName === pkg || moduleName.startsWith(pkg + '/'))) {
    // Return an empty module
    return {
      type: 'empty',
    };
  }

  // Default resolution
  if (originalResolveRequest) {
    return originalResolveRequest(context, moduleName, platform);
  }
  return context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
