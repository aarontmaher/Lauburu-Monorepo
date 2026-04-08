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

// Block native health packages from being bundled in Expo Go.
// Redirect them to an empty stub module instead of { type: 'empty' }.
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

module.exports = config;
