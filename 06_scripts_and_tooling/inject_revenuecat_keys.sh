#!/bin/bash
echo "=========================================="
echo "   Lauburu Monetization Key Injector"
echo "=========================================="
echo ""
read -p "Enter your RevenueCat Public Apple Key (appl_...): " APPLE_KEY
read -p "Enter your RevenueCat Secret V1 API Key: " SECRET_KEY

echo ""
echo "Injecting into Flutter (Frontend)..."
sed -i '' "s/mock_rc_apple_api_key/$APPLE_KEY/g" /Volumes/Lauburu-Monorepo/01_apps/biometrics/lauburu_zone2_endurance/lib/services/revenuecat_entitlement_service.dart

echo "Injecting into Python (Backend) via ~/.zshrc..."
if ! grep -q "REVENUECAT_SECRET_API_KEY" ~/.zshrc; then
    echo "export REVENUECAT_SECRET_API_KEY=\"$SECRET_KEY\"" >> ~/.zshrc
else
    sed -i '' "s/.*REVENUECAT_SECRET_API_KEY.*/export REVENUECAT_SECRET_API_KEY=\"$SECRET_KEY\"/" ~/.zshrc
fi

echo ""
echo "✅ Keys automatically injected! Open a new terminal to apply."
