#!/usr/bin/env bash
set -e
KEYSTORE_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/android/upload-keystore.jks"
if [ -f "$KEYSTORE_PATH" ]; then
    echo "Release keystore already exists at $KEYSTORE_PATH"
else
    echo "Generating production upload keystore..."
    keytool -genkey -v -keystore "$KEYSTORE_PATH" -alias upload -keyalg RSA -keysize 2048 -validity 10000         -dname "CN=Lauburu Sovereign, OU=Engineering, O=Lauburu AI, L=Sydney, ST=NSW, C=AU"         -storepass "lauburu_production_secure_pass" -keypass "lauburu_production_secure_pass"
    echo "Keystore generated successfully at $KEYSTORE_PATH"
fi
