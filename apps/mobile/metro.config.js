// Learn more https://docs.expo.io/guides/customizing-metro
const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const workspaceRoot = path.resolve(__dirname, '../..');
const config = getDefaultConfig(__dirname);

// Monorepo: watch workspace root for shared packages
config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(workspaceRoot, 'node_modules'),
  path.resolve(__dirname, 'node_modules'),
];

// Block native health packages ONLY in Expo Go.
// In dev builds (expo run:ios), native packages must resolve normally.
//
// Detection: Expo Go sets EXPO_GO=1 or we can check for the absence
// of ios/android build directories as a heuristic. The safest approach:
// set NATIVE_BUILD=1 env var when running expo run:ios.
//
// Default: block (safe for Expo Go). Set NATIVE_BUILD=1 to allow.
const isNativeBuild = process.env.NATIVE_BUILD === '1';

if (!isNativeBuild) {
  const NATIVE_BLOCKED = [
    '@kingstinct/react-native-healthkit',
    'react-native-health-connect',
    'react-native-nitro-modules',
  ];

  const STUB_PATH = path.resolve(__dirname, 'src/services/native-stub.js');
  const origResolve = config.resolver.resolveRequest;

  config.resolver.resolveRequest = (context, moduleName, platform) => {
    if (NATIVE_BLOCKED.some((pkg) => moduleName === pkg || moduleName.startsWith(pkg + '/'))) {
      return {
        type: 'sourceFile',
        filePath: STUB_PATH,
      };
    }
    if (origResolve) {
      return origResolve(context, moduleName, platform);
    }
    return context.resolveRequest(context, moduleName, platform);
  };
}

module.exports = config;
