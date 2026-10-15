// Shopify Membership Tier & Compute Credits Card Component

import '../models/biometrics_model.dart';
import 'theme.dart';

class ShopifyTierCardRenderer {
  final double width;

  const ShopifyTierCardRenderer({this.width = 320.0});

  String renderSvgCard(ShopifyMembership membership) {
    final isPro = membership.tier == ShopifyTier.proAthlete;
    final isCrowd = membership.tier == ShopifyTier.crowdsourcedComputeLifetime;
    final badgeColor = isCrowd ? '#9D00FF' : (isPro ? '#00FFCC' : '#64748B');
    final badgeText = isCrowd ? 'LIFETIME CONTRIBUTOR' : (isPro ? 'PRO ATHLETE' : 'FREE COMMUNITY');

    return '''
<svg width="$width" height="150" viewBox="0 0 $width 150" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#131B2A" rx="8" stroke="#334155" stroke-width="1"/>

  <!-- Header -->
  <text x="16" y="24" fill="#94A3B8" font-size="11" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    SHOPIFY MEMBERSHIP TIER
  </text>
  
  <!-- Tier Badge -->
  <rect x="${width - 150}" y="12" width="134" height="20" fill="$badgeColor" fill-opacity="0.2" rx="4" stroke="$badgeColor" stroke-width="1"/>
  <text x="${width - 83}" y="26" text-anchor="middle" fill="$badgeColor" font-size="9" font-weight="900" font-family="${LauburuTypography.fontFamily}">
    $badgeText
  </text>

  <!-- Plan Details -->
  <text x="16" y="52" fill="#FFFFFF" font-size="14" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    ${membership.tierName}
  </text>
  <text x="16" y="70" fill="#94A3B8" font-size="10" font-family="${LauburuTypography.fontFamily}">
    Customer: ${membership.customerId}
  </text>

  <!-- Credits Bar -->
  <rect x="16" y="85" width="${width - 32}" height="8" fill="#1E293B" rx="4"/>
  <rect x="16" y="85" width="${(width - 32) * (membership.activeSubscription ? 0.92 : 0.15)}" height="8" fill="$badgeColor" rx="4"/>
  
  <text x="16" y="110" fill="#94A3B8" font-size="10" font-family="${LauburuTypography.fontFamily}">
    Compute Credits: <tspan fill="#FFFFFF" font-weight="bold">${membership.computeCreditsGflops} GFLOPS</tspan>
  </text>

  <text x="16" y="130" fill="#64748B" font-size="9" font-family="${LauburuTypography.fontFamily}">
    Features: ${membership.allowedFeatures.length} unlocked (Pan-Tompkins 512Hz, Zone 2 Coach)
  </text>
</svg>
''';
  }
}
