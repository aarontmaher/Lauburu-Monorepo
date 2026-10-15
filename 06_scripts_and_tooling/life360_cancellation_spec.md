# Life360 Web Cancellation Specification

## Overview
This specification details the steps, URLs, and DOM selectors required to automate the cancellation of a Life360 membership that is billed directly via the web. 
*Note: Memberships billed through Apple App Store or Google Play Store cannot be canceled via the web interface.*

## URLs
- **Homepage:** `https://www.life360.com`
- **Login URL:** `https://www.life360.com/circles/#/` or `https://www.life360.com/login/`
- **Billing/Settings URL:** Varies slightly by user state, but generally accessed via the Account Settings or a dedicated "Manage Membership" page after logging in.

## Playwright Automation Flow

### 1. Navigation & Login
- Navigate to the login page: `https://www.life360.com/circles/#/`
- Standard Playwright locators for login (using user-facing accessibility labels where possible):
  - **Email/Phone input:** `page.getByLabel('Email Address')` or `page.getByPlaceholder('Email or Phone')`
  - **Password input:** `page.getByLabel('Password')`
  - **Submit button:** `page.getByRole('button', { name: /Continue|Log in/i })`

```javascript
// Example Playwright Login snippet
await page.goto('https://www.life360.com/circles/#/');
await page.getByLabel('Email Address').fill('user@example.com');
await page.getByLabel('Password').fill('password123');
await page.getByRole('button', { name: /Continue|Log in/i }).click();
```

### 2. Navigating to Billing
- Wait for the main dashboard to load.
- Click on the **Account Settings** or **Manage Membership** option (typically located in a user dropdown or top navigation menu).
- Locator strategies:
  - `page.getByRole('link', { name: /Manage Membership|Billing/i })`
  - `page.getByText('Account Settings')`

### 3. Executing the Cancellation
- On the Billing/Manage Membership page, locate the active subscription.
- Click the **Cancel Subscription** or **Cancel Membership** button.
- A confirmation modal or secondary page may appear to confirm cancellation.
- Locator strategies:
  - `page.getByRole('button', { name: /Cancel Membership|Cancel Subscription/i })`
  - *Confirm Modal:* `page.getByRole('button', { name: /Yes, Cancel/i })`

```javascript
// Example Playwright Cancellation snippet
await page.getByRole('link', { name: /Manage Membership/i }).click();
await page.getByRole('button', { name: /Cancel Membership/i }).click();
// Handle confirmation dialog if present
await page.getByRole('button', { name: /Confirm|Yes, Cancel/i }).click();
```

## Troubleshooting & Edge Cases
- **OTP / 2FA:** Life360 may send an SMS or email OTP on new logins. Automation scripts must be prepared to intercept and input this code.
- **Third-Party Billing:** If the UI does not display a "Cancel Membership" button and instead directs to Google Play or Apple App Store, the subscription was not billed via web, and this script cannot cancel it.
- **DOM Stability:** Prefer `getByRole` and `getByLabel` as Life360's CSS classes and DOM structure may change frequently.
