/**
 * Combat Lab Lauburu — Client-Side Shopify Storefront Checkout Pipeline
 * Subsystem: Commercialization & E-Commerce Monetization
 * Store: https://lauburu-grappling.myshopify.com
 * API: Storefront GraphQL API (2024-04)
 * Architecture: Client-side GraphQL cartCreate mutation with automatic permalink fallback.
 */

// 1. Shopify Storefront Configuration
const SHOPIFY_STOREFRONT_CONFIG = {
  shopDomain: "lauburu-grappling.myshopify.com",
  storefrontAccessToken: "a39ead89f7318e991105e64873b4e10e",
  apiVersion: "2024-04",
  get endpoint() {
    return `https://${this.shopDomain}/api/${this.apiVersion}/graphql.json`;
  },
  // Canonical product variant mapping
  variants: {
    "Starter Athlete": {
      variantId: "gid://shopify/ProductVariant/45919098732680",
      numericId: "45919098732680",
      priceAud: 29.0,
      title: "Starter Athlete (Mat Tier)",
      sellingPlanId: "gid://shopify/SellingPlan/4547477640",
      altVariantId: "gid://shopify/ProductVariant/45919099093128"
    },
    "Pro Grappler & Lab": {
      variantId: "gid://shopify/ProductVariant/45919099093128",
      numericId: "45919099093128",
      priceAud: 99.0,
      title: "Pro Grappler & Lab (Pro Coach)",
      sellingPlanId: "gid://shopify/SellingPlan/4547477640"
    },
    "Elite Academy": {
      variantId: "gid://shopify/ProductVariant/45919099125896",
      numericId: "45919099125896",
      priceAud: 299.0,
      title: "Elite Academy & Team (Gym License)"
    },
    "Hardware Starter Bundle": {
      variantId: "gid://shopify/ProductVariant/44779813994632",
      numericId: "44779813994632",
      priceAud: 249.0,
      title: "Combat Lab Hardware Starter Bundle"
    },
    // Aliases
    "mat_tier": "Starter Athlete",
    "pro_coach": "Pro Grappler & Lab",
    "gym_academy": "Elite Academy",
    "hardware_bundle": "Hardware Starter Bundle"
  }
};

/**
 * Resolves a variant specification from a name or ID.
 * @param {string} identifier - e.g. "Starter Athlete", "pro_coach", or raw GID
 * @returns {{variantId: string, numericId: string, title: string, priceAud?: number, sellingPlanId?: string}}
 */
function resolveVariant(identifier) {
  if (!identifier) {
    throw new Error("Missing variant identifier");
  }

  // If already a variant object with numericId or variantId
  if (typeof identifier === 'object' && identifier !== null) {
    const rawId = identifier.numericId || identifier.variantId || identifier.id;
    if (rawId) {
      const numId = extractNumericId(rawId);
      const gid = (typeof rawId === 'string' && rawId.startsWith("gid://"))
        ? rawId
        : `gid://shopify/ProductVariant/${numId}`;
      return {
        variantId: identifier.variantId || gid,
        numericId: String(numId),
        title: identifier.title || String(rawId),
        priceAud: identifier.priceAud,
        sellingPlanId: identifier.sellingPlanId
      };
    }
    if (identifier.title) {
      return resolveVariant(identifier.title);
    }
  }

  // Direct match or alias
  if (SHOPIFY_STOREFRONT_CONFIG.variants[identifier]) {
    let target = SHOPIFY_STOREFRONT_CONFIG.variants[identifier];
    if (typeof target === 'string') {
      target = SHOPIFY_STOREFRONT_CONFIG.variants[target];
    }
    return target;
  }

  // Check case-insensitive partial match
  const lower = String(identifier).toLowerCase().trim();
  for (const [key, val] of Object.entries(SHOPIFY_STOREFRONT_CONFIG.variants)) {
    if (typeof val === 'object' && val.title && val.title.toLowerCase().includes(lower)) {
      return val;
    }
    if (key.toLowerCase() === lower) {
      return typeof val === 'string' ? SHOPIFY_STOREFRONT_CONFIG.variants[val] : val;
    }
  }

  // Treat as raw GID or numeric ID
  const numId = extractNumericId(identifier);
  const gid = (typeof identifier === 'string' && identifier.startsWith("gid://"))
    ? identifier
    : `gid://shopify/ProductVariant/${numId}`;
  return {
    variantId: gid,
    numericId: String(numId),
    title: typeof identifier === 'string' ? identifier : String(numId)
  };
}

/**
 * Extracts clean numeric variant ID from GID or raw string.
 */
function extractNumericId(idString) {
  if (typeof idString === 'object' && idString !== null) {
    idString = idString.numericId || idString.variantId || idString.id || '';
  }
  const s = String(idString || '').trim();
  const match = s.match(/(\d+)$/);
  return match ? match[1] : s;
}

/**
 * Generates direct Shopify cart permalink.
 * Format: https://{shop_domain}/cart/{numeric_variant_id}:{quantity}
 */
function getFallbackPermalink(variantIdentifier, quantity = 1) {
  const v = (typeof variantIdentifier === 'object' && variantIdentifier !== null && variantIdentifier.numericId)
    ? variantIdentifier
    : resolveVariant(variantIdentifier);
  return `https://${SHOPIFY_STOREFRONT_CONFIG.shopDomain}/cart/${v.numericId}:${quantity}`;
}

/**
 * Client-side Storefront GraphQL cartCreate mutation.
 * @param {string|object} variantInput - Plan title, tier ID, or variant object
 * @param {object} [options]
 * @param {number} [options.quantity=1]
 * @param {string} [options.sellingPlanId]
 * @param {Array<{key: string, value: string}>} [options.customAttributes]
 * @returns {Promise<{success: boolean, checkoutUrl: string, cartId: string|null, totalAmount: object|null, method: string, raw?: any}>}
 */
async function createStorefrontCheckout(variantInput, options = {}) {
  const v = typeof variantInput === 'object' && variantInput.variantId ? variantInput : resolveVariant(variantInput);
  const quantity = options.quantity || 1;
  const sellingPlanId = options.sellingPlanId || v.sellingPlanId || null;

  const lineItem = {
    merchandiseId: v.variantId,
    quantity: quantity
  };

  if (sellingPlanId) {
    lineItem.sellingPlanId = sellingPlanId;
  }

  if (options.customAttributes && Array.isArray(options.customAttributes)) {
    lineItem.attributes = options.customAttributes;
  }

  const query = `
    mutation cartCreate($input: CartInput!) {
      cartCreate(input: $input) {
        cart {
          id
          checkoutUrl
          totalQuantity
          cost {
            totalAmount {
              amount
              currencyCode
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
  `;

  try {
    const response = await fetch(SHOPIFY_STOREFRONT_CONFIG.endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Shopify-Storefront-Access-Token": SHOPIFY_STOREFRONT_CONFIG.storefrontAccessToken
      },
      body: JSON.stringify({
        query: query,
        variables: {
          input: {
            lines: [lineItem],
            attributes: [
              { key: "source_application", value: "Combat Lab Lauburu PWA" },
              { key: "checkout_engine", value: "client_storefront_graphql" }
            ]
          }
        }
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
    }

    const resData = await response.json();
    const cartData = resData?.data?.cartCreate;

    // Handle user errors
    if (cartData?.userErrors && cartData.userErrors.length > 0) {
      const errorMsg = cartData.userErrors.map(e => e.message).join("; ");
      
      // Auto-retry with selling plan if required
      if (errorMsg.includes("Variant can only be purchased with a selling plan") && !lineItem.sellingPlanId) {
        return await createStorefrontCheckout(v, {
          ...options,
          sellingPlanId: "gid://shopify/SellingPlan/4547477640"
        });
      }

      // Auto-retry with alt variant if available
      if (errorMsg.includes("does not exist") && v.altVariantId) {
        return await createStorefrontCheckout({
          variantId: v.altVariantId,
          numericId: extractNumericId(v.altVariantId),
          title: v.title,
          sellingPlanId: v.sellingPlanId
        }, options);
      }

      throw new Error(`Shopify cartCreate userError: ${errorMsg}`);
    }

    const checkoutUrl = cartData?.cart?.checkoutUrl;
    if (checkoutUrl) {
      return {
        success: true,
        checkoutUrl: checkoutUrl,
        cartId: cartData.cart.id,
        totalAmount: cartData.cart.cost?.totalAmount || null,
        method: "graphql",
        raw: cartData
      };
    }

    throw new Error("No checkoutUrl returned in cart response");
  } catch (err) {
    // Fallback permalink
    const permalink = getFallbackPermalink(v, quantity);
    return {
      success: true,
      checkoutUrl: permalink,
      cartId: null,
      totalAmount: null,
      method: "fallback_permalink",
      fallbackReason: err.message
    };
  }
}

/**
 * High-level checkout entry point.
 * Validates plan, creates session URL, notifies UI, and redirects user.
 * @param {string} planIdentifier - Name of tier or hardware kit
 * @param {number} [priceAud] - Expected price for UI messaging
 * @param {object} [options]
 * @param {boolean} [options.redirect=true] - Set false to only return the URL without redirecting
 * @param {boolean} [options.newTab=false] - Open checkout in new tab
 * @returns {Promise<{success: boolean, checkoutUrl: string, method: string}>}
 */
async function initiatePlanCheckout(planIdentifier, priceAud, options = {}) {
  const redirect = options.redirect !== false;
  const newTab = Boolean(options.newTab);

  // Trigger UI notification if toast function exists
  if (typeof window !== 'undefined' && typeof window.showToast === 'function') {
    const priceText = priceAud ? ` ($${priceAud} AUD)` : '';
    window.showToast(`🛒 Generating secure Shopify checkout for ${planIdentifier}${priceText}...`);
  }

  const result = await createStorefrontCheckout(planIdentifier, options);

  // Dispatch custom event for telemetry / audit logging
  if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function' && typeof CustomEvent === 'function') {
    window.dispatchEvent(new CustomEvent('lauburu:checkout_initiated', {
      detail: {
        plan: planIdentifier,
        price: priceAud,
        checkoutUrl: result.checkoutUrl,
        method: result.method,
        cartId: result.cartId
      }
    }));
  }

  if (redirect && typeof window !== 'undefined' && window.location) {
    if (newTab) {
      window.open(result.checkoutUrl, '_blank');
    } else {
      window.location.href = result.checkoutUrl;
    }
  }

  return result;
}

/**
 * Installs integration hooks into Combat Lab global functions.
 */
function installCheckoutHooks() {
  if (typeof window === 'undefined') return;

  window.subscribeTier = function (name, price) {
    return initiatePlanCheckout(name, price);
  };

  window.buyHardwareBundle = function () {
    return initiatePlanCheckout("Hardware Starter Bundle", 249);
  };

  window.initiatePlanCheckout = initiatePlanCheckout;
  window.createStorefrontCheckout = createStorefrontCheckout;
  window.getFallbackPermalink = getFallbackPermalink;
  window.SHOPIFY_STOREFRONT_CONFIG = SHOPIFY_STOREFRONT_CONFIG;

  console.info("🥋 Combat Lab Shopify Checkout Pipeline initialized & hooked to UI.");
}

// Auto-install hooks in browser environments
if (typeof window !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', installCheckoutHooks);
  } else {
    installCheckoutHooks();
  }
}

// Global & CommonJS exports
const exported = {
  SHOPIFY_STOREFRONT_CONFIG,
  resolveVariant,
  extractNumericId,
  getFallbackPermalink,
  createStorefrontCheckout,
  initiatePlanCheckout,
  installCheckoutHooks
};

if (typeof globalThis !== 'undefined') {
  globalThis.CombatLabCheckout = exported;
}

if (typeof window !== 'undefined') {
  window.CombatLabCheckout = exported;
}

export {
  SHOPIFY_STOREFRONT_CONFIG,
  resolveVariant,
  extractNumericId,
  getFallbackPermalink,
  createStorefrontCheckout,
  initiatePlanCheckout,
  installCheckoutHooks
};

export default exported;

