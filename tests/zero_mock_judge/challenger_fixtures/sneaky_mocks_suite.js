/**
 * Adversarial Fixture Suite 2: Sneaky Mock Patterns (JavaScript / TypeScript)
 * ===========================================================================
 * Constructed by Challenger 1 to stress-test JS regex / pattern scanner evasion:
 * 1. String concatenation & template literals for latency: `0.` + `28ms`, `${0.28}ms`.
 * 2. Unconventional whitespace / multiline formatting for object properties.
 * 3. Indirection in FLEET_DEVICES static arrays (e.g. const fleet = [dev1]).
 * 4. Obfuscated synthetic throughput math (single_tp << 1, single_tp / 0.5, variable factors).
 * 5. Deeply nested fallback objects in catch blocks.
 * 6. Indirect setTimeout wrappers and obfuscated Math.random.
 */

// Vector 1: Template literals & string concatenation for latency strings
export const STEALTH_DEVICE_1 = {
  id: "Mac_Node_Local",
  name: "Host Mac Mini M4",
  latency: `${0.28}ms (DMA)`,
  status: "APPLIED"
};

export const STEALTH_DEVICE_2 = {
  id: "Linux_Head_Node",
  name: "Linux Router",
  latency: "0." + "45ms (Ethernet)",
  status: "ACTIVE"
};

// Vector 2: Multiline whitespace evasion
export const STEALTH_DEVICE_MULTILINE = {
  id: "Pixel_Node",
  latency
    :
    "0.28ms (DMA)",
  status
    :
    "ONLINE"
};

// Vector 3: Indirect Static Fleet Array Definition
const dev1 = { id: "mac_01", status: "APPLIED" };
const dev2 = { id: "linux_02", status: "APPLIED" };
export const FLEET_DEVICES = [dev1, dev2];

// Vector 4: Obfuscated synthetic math multipliers
export function computeSpeed(single_tp) {
  const multiplier = 2.0;
  const merged_tp = single_tp * multiplier; // Variable indirection
  const pixel_tp = single_tp / 0.5; // Division by 0.5 instead of * 2.0
  const doubled_tp = single_tp << 1; // Bitwise shift
  return { merged_tp, pixel_tp, doubled_tp };
}

// Vector 5: Nested fallback status objects in catch blocks
export async function fetchFleetStatus() {
  try {
    const res = await fetch("/api/dark-mode/status");
    return await res.json();
  } catch (err) {
    return {
      payload: {
        darkFleet: {
          status: "FLEET_DARK_ACTIVE",
          devices_active: 6
        }
      }
    };
  }
}

// Vector 6: Indirect setTimeout UI simulation
export function triggerSimulatedSuccess(callback) {
  const statusToSet = "ONLINE";
  window.setTimeout(() => {
    callback(statusToSet);
  }, 1000);
}

// Vector 7: Obfuscated Math.random in telemetry pipeline
export function getSimulatedThroughput() {
  // Alias Math object
  const M = Math;
  return M.random() * 100.0;
}
