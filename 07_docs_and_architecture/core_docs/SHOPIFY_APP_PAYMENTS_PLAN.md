# Shopify-linked payments — mobile-first plan

Goal: link Lauburu mobile to a Shopify-managed subscription product so
users get a paid entitlement (e.g. AI Coach + multi-window trends +
Reference + 3D map) without us running a separate payment processor.

This is a **plan only**. Nothing wired today. Do not add payment
buttons to the tester UI before this is implemented and tested
end-to-end.

## Current state

- No Shopify, Stripe, RevenueCat, or in-app-purchase code in the repo.
- `apps/mobile/src/store/tier-store.ts` already exists for capability
  gating (free / basic / premium / etc.) — purely client-side today.
- Backend has no `/entitlement` endpoint yet.
- App store rules (Apple, Google) restrict using third-party
  webview-based payments for digital goods. Shopify subscriptions for
  *digital* content typically need to use Apple IAP / Google Play
  billing on mobile, with Shopify as a backend for non-mobile checkout
  and customer record.

## Recommended architecture

1. **Shopify is the source of truth for the paid customer record.**
   - Web/desktop users buy a Lauburu subscription product on a Shopify
     store (`shop.lauburugrapplingmap.com` or similar).
   - Shopify Customer ID + Subscription line items become the canonical
     entitlement record.

2. **Mobile entitlement comes from the backend, not the app.**
   - New backend endpoint:
     `GET /api/entitlement` (auth: existing Supabase JWT).
   - Returns: `{ tier: 'free'|'basic'|'premium', source: 'shopify'|'apple_iap'|'google_play'|'admin', expiresAt, lastVerifiedAt }`.
   - Mobile `tier-store` reads this on startup and after sign-in,
     caches it, and shows the gated UI.

3. **Webhook from Shopify → Railway backend.**
   - Shopify Admin → Notifications → webhooks.
   - Subscribe to `customers/update`, `subscription_contracts/create`,
     `subscription_contracts/update`, `orders/paid`, `orders/refunded`.
   - Backend route: `POST /api/integrations/shopify/webhook`
     (HMAC-verified using `SHOPIFY_WEBHOOK_SECRET` Railway env).
   - On webhook, write the entitlement row keyed by `shopify_customer_id`,
     plus a join table mapping Lauburu user → Shopify customer.

4. **Linking a user to a Shopify customer.**
   - Settings → "Manage subscription" → opens the Shopify-hosted
     account portal in a `WebBrowser` (Safari View / Chrome Custom
     Tab) at `https://shop.lauburugrapplingmap.com/account`.
   - On first link, the backend correlates by email after the user
     signs into Shopify (matched against Supabase email).

5. **Mobile checkout path (rules-compliant).**
   - **iOS**: must use Apple In-App Purchase for digital subscriptions.
     Use `expo-store-kit` (when stable) or RevenueCat as the SDK. The
     entitlement source is then `apple_iap`.
   - **Android**: same with Google Play Billing.
   - The Shopify webhook becomes the *web/desktop* + admin path; mobile
     IAP is the *App Store / Play Store* path. Both flow into the same
     `/api/entitlement` row keyed by Lauburu user.
   - Don't try to put a Shopify checkout button inside the mobile app
     for digital subscriptions — it gets the app rejected.

## Required env vars

| Var | Where | Purpose |
|---|---|---|
| `SHOPIFY_STORE_DOMAIN` | Railway | e.g. `lauburu-shop.myshopify.com` |
| `SHOPIFY_ADMIN_API_TOKEN` | Railway | server → Shopify Admin API |
| `SHOPIFY_STOREFRONT_TOKEN` | Railway (read-only) | server → Storefront for plan listing |
| `SHOPIFY_WEBHOOK_SECRET` | Railway | HMAC verification on webhook |
| `EXPO_PUBLIC_SHOPIFY_PORTAL_URL` | EAS env | mobile → opens customer portal in browser |

Mobile holds **none** of these — only the public portal URL.

## Backend work

1. New table `entitlements` (Postgres on Railway) — keyed by
   `lauburu_user_id`, fields above. Migration only — **do not run
   `supabase db push`** per repo rules; if Supabase mirror is needed,
   write migration file under `supabase/migrations/` for review.
2. `routes/entitlements.ts`:
   - `GET /api/entitlement` (auth required) → returns current row.
   - `POST /api/integrations/shopify/webhook` → HMAC-verified, writes
     entitlement row.
3. Audit/log every webhook receipt with `[shopify-webhook]
   topic=… customer=…` (no token logged).

## Mobile work (later, when above is live)

1. `tier-store.ts` reads from `/api/entitlement` and caches.
2. Settings → "Manage subscription" row → opens
   `EXPO_PUBLIC_SHOPIFY_PORTAL_URL` in `WebBrowser.openBrowserAsync`.
3. Where features are gated, surface compact upgrade copy that links
   to the subscription portal — no fake CTAs.
4. iOS / Android IAP integration is a separate batch (RevenueCat is
   the lowest-friction option).

## What to do before any code lands

- Decide whether Shopify subscriptions cover web only, or whether we
  also need IAP for mobile. (App store rules force IAP for digital
  subscriptions on mobile.)
- Stand up the Shopify store + create the subscription product.
- Confirm the legal text (Terms / Privacy / refund policy) before any
  paid path is exposed.

## Out of scope this batch

- Any UI in the tester app.
- Any backend route changes.
- Any `tier-store` changes.

A standing reminder: do not add a paid CTA to tester surfaces before
the entitlement source-of-truth is wired and verified. Better to ship
free for testers and add the paid path once the backend webhook +
entitlement endpoint pass smoke tests.
