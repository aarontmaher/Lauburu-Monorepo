# 🫀 Custom Movesense Bicep ECG Band — Ready-to-Integrate Strategy

**Executive Summary:** A specialized medical-grade compression bicep/tricep band designed for Brazilian Jiu-Jitsu, wrestling, and high-motion combat sports. Replaces failing chest straps with a dual-electrode inner-arm compression sleeve integrating standard Movesense 45mm snap studs.

---

## 1. Problem & Clinical Biomechanics
*   **The Chest Strap Flaw in Combat Sports:** Standard chest straps slip down to the abdomen during guard passing, get caught in lapels, and suffer severe motion artifacts (baseline wander) due to pectoral contraction and heavy breathing.
*   **The Bicep Solution:** Placing the sensor on the medial bicep over the brachial artery keeps the device protected from arm-bars, eliminates chest compression restrictions, and provides pristine single-lead ECG signal integrity at 512Hz.
*   **DSP Integration:** Direct streaming to Lauburu's Pan-Tompkins QRS detection engine on Port 4000 for sub-millisecond R-R intervals and DFA-$\alpha_1$ Zone 2 aerobic threshold tracking.

---

## 2. Hardware Specifications & Bill of Materials (BOM)

| Component | Technical Specification | Unit Cost (AUD) | Supplier Source |
| :--- | :--- | :--- | :--- |
| **Snap Studs (Pair)** | 45mm spacing, nickel-plated brass, medical snap connector | $0.85 | Shenzhen Snap-Fast Hardware |
| **Conductive Electrodes** | Silver-knitted antimicrobial fabric (zero-gel, dry contact) | $2.10 | Statex Shieldex / Dongguan Textile |
| **Band Material** | Breathable compression nylon-spandex with anti-slip silicone interior ribs | $3.50 | Ningbo Sportswear Co. |
| **Closure System** | Low-profile micro-hook Velcro (non-abrasive to rashguards) | $0.80 | YKK Micro-Lok |
| **Assembly & Testing** | Ultrasonic welding of electrode leads + QA continuity check | $3.25 | Shenzhen OEM Assembler |
| **Branded Packaging** | Matte black anti-static slide box with UV spot Lauburu logo | $1.50 | Dongguan Box Master |
| **TOTAL COGS** | **Fully Packaged Landed Unit** | **$12.00 AUD** | |

---

## 3. Financial Model & Pricing Architecture

*   **Standalone Custom Band RRP:** **$59.00 AUD**
    *   Gross Profit per unit: **$47.00 AUD (79.6% Gross Margin)**
*   **Movesense MD+ Pro Athlete Bundle RRP:** **$229.00 AUD**
    *   Movesense Medical Sensor Wholesale: ~$110.00 AUD
    *   Custom Band COGS: $12.00 AUD
    *   Total Bundle COGS: $122.00 AUD
    *   Gross Profit per bundle: **$107.00 AUD (46.7% Gross Margin)**
*   **Break-Even Horizon:** Initial run of 200 units ($2,400 AUD production tooling) breaks even after 52 standalone unit sales.

---

## 4. Ready-to-Integrate Execution Plan (Pull the Trigger)

1.  **Tooling & Spec Sheet:** CAD drawing with 45.0mm $\pm$0.2mm snap spacing sent to Shenzhen manufacturer.
2.  **Sample Validation Gate:** 5 prototypes bench-tested under sweat immersion (512Hz ECG Pan-Tompkins SNR $\ge 25\text{ dB}$).
3.  **Direct Storefront Launch:** Synced to Shopify and MedusaJS under category `Hardware & Biometrics`.
