#!/bin/bash
DOMAIN=$1
TOKEN=$2
FILE="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/lib/src/ui/dashboard_screen.dart"

sed -i '' "s/const SHOPIFY_DOMAIN = 'YOUR_STORE.myshopify.com';/const SHOPIFY_DOMAIN = '${DOMAIN}';/" "$FILE"
sed -i '' "s/const STOREFRONT_TOKEN = 'YOUR_STOREFRONT_ACCESS_TOKEN';/const STOREFRONT_TOKEN = '${TOKEN}';/" "$FILE"
echo "✅ Headless Token Injection Complete."
