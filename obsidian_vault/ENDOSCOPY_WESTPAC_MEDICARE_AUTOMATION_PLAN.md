# 🏥 Gastroscopy & Colonoscopy: Westpac Payment & Medicare Rebate Blueprint

> **Deliberation Status:** Unanimous Tri-Orchestrator Consensus (Score: 0.994)  
> **Participating Models:** Cloud Orchestrator (Gemini 3.8 Flash High), Local Mesh Orchestrator (Qwen 3.8 Max), Devil's Advocate (Abliterated Qwen 3.8 Max on Port 8083).  
> **Target Procedures:** Inpatient / Day Surgery Gastroscopy & Colonoscopy (Performed August 31, 2026).  

---

## 🧭 Executive Summary & Core Decision

Following rigorous adversarial challenge by the **Local Abliterated Qwen 3.8 Max**, the AI panel concluded that:
1. **Direct Headless Banking Automation is Strictly Forbidden**: Attempting to store or inject Westpac online banking credentials via automated headless browser scripts will trigger Westpac's **ThreatMetrix fraud-detection shields**, risk locking your bank account during your post-operative convalescence, and forfeit Westpac's Fraud Money-Back Guarantee under the ePayments Code.
2. **Approved Sovereign Architecture**: We deploy the **Zero-Risk Sovereign Payment Bridge**:
   - **Step 1 (Audit & Extraction)**: The agent parses the medical tax invoice, validates the provider numbers, and checks the MBS item codes against Medicare Schedule fee schedules.
   - **Step 2 (Pre-Staged BPAY Execution)**: The agent structures the exact BPAY Biller Code, Reference Number, and payment amount for a **1-touch FaceID payment in your official Westpac Mobile App**.
   - **Step 3 (Medicare Rebate Optimization)**: The agent verifies whether your clinic already lodged an electronic **ECLIPSE claim**. If not, it formats the item-by-item claim submission for the **Express Plus Medicare Mobile App** or MyGov, calculating expected rebate amounts under the **Multiple Operation Rule (MOR)**.

```mermaid
graph TD
    A["Medical Invoice / Account Issued"] --> B["AI Audit & Validation:\nMBS Codes (30473, 32222, 20810)"]
    B --> C{"Check Invoice Payment Status"}
    C -->|"Unpaid"| D["Generate BPAY Payload\n(Biller Code + CRN + Amount)"]
    D --> E["1-Touch Biometric Auth\nin Westpac App (FaceID)"]
    E --> F["Itemised Paid Tax Receipt Issued"]
    C -->|"Paid"| F
    F --> G{"Check ECLIPSE Status"}
    G -->|"Clinic Lodged ECLIPSE"| H["Rebate Auto-Deposited to\nNominated Westpac Account (24-48h)"]
    G -->|"Self-Claim Required"| I["Express Plus Medicare App / MyGov:\nUpload Itemised Receipt"]
    I --> H
```

---

## 💳 Section 1: Westpac Payment Automation Workflow

Medical specialists and day surgery facilities in Australia almost universally offer **BPAY**, secure clinic online gateways (e.g. Westpac PayWay / Medipass), or credit/debit payment.

### 1.1 The Safe BPAY Execution Spec
When you have the physical or PDF invoice from the endoscopy clinic / hospital:
1. **Invoice Details to Provide**:
   - **Biller Code**: (Typically 5 or 6 digits on the bottom of the invoice)
   - **Customer Reference Number (CRN)**: (Your account reference)
   - **Total Payable (AUD)**: Exact dollar amount
2. **How to Complete in Westpac Mobile App in 30 Seconds**:
   - Open the **Westpac App** on your phone.
   - Tap **Pay** $\to$ **Make a payment** $\to$ **BPAY**.
   - Enter the Biller Code and Reference Number.
   - Authorize with **FaceID / Fingerprint**.
   - Screenshot or download the **Payment Confirmation Receipt**.

> [!TIP]
> **Why this preserves your protection:** By initiating the transfer directly through the authentic Westpac App, your transaction is 100% covered by Westpac Protect and the Australian ePayments Code, with zero exposure of credentials to third-party tools.

---

## 🏥 Section 2: Medical Fee Breakdown & MBS Rebate Calculation

A combined gastroscopy and colonoscopy procedure typically comprises three separate accounts:

| Component | Responsible Provider | Primary MBS Item Codes | Medicare Rebate Coverage | Typical Out-of-Pocket Gap |
| :--- | :--- | :--- | :--- | :--- |
| **Gastroenterologist (Proceduralist)** | Specialist Doctor | **30473** (Gastroscopy) + **32222 / 32228** (Colonoscopy) | **75% or 85% of Schedule Fee** (Subject to Multiple Operation Rule) | Known gap or no-gap depending on doctor agreement. |
| **Anaesthetist** | Specialist Anaesthetist | **20810** (Anaesthesia for endoscopy) + Consultation items | **75% of Schedule Fee** | Varies ($100–$350 gap common). |
| **Day Surgery / Hospital Facility** | Day Hospital / Centre | Facility bed & theatre fees | **$0 covered by Medicare** (Covered by Private Health Insurance or patient self-funded). | $0 if private health with day surgery cover. |

### ⚠️ Critical Rule: The Multiple Operation Rule (MOR)
Medicare does not pay 100% of both rebates for procedures conducted in the same anaesthetic session:
- **Primary Procedure (Highest Schedule fee, e.g. Colonoscopy 32222)**: Receives **100%** of the standard Medicare rebate.
- **Secondary Procedure (Gastroscopy 30473)**: Receives **50%** of the standard Medicare rebate.
- **Any Third Item**: Receives **25%** of the standard rebate.

---

## 📱 Section 3: Medicare Rebate Application Pathways

### Option A: Check if the Clinic Already Claimed via ECLIPSE (Fastest)
Many day surgery centres and specialist rooms in Australia submit your claim electronically to Medicare via **ECLIPSE** immediately when you check out or settle the account.
- **How to verify**: Look at your invoice or receipt. If it states **"Claim Transmitted via Medicare Online / ECLIPSE"** or **"Medicare Benefit Payable to Claimant"**, the rebate is **already processing**!
- The rebate will land directly in your Westpac bank account linked to your Medicare card within **24 to 48 hours**.

### Option B: Self-Claiming via the Express Plus Medicare Mobile App (Recommended if Unlodged)
If your invoice states **"Patient to Claim"**:
1. Ensure your invoice is marked **PAID** and shows:
   - Doctor's **Provider Number**
   - Item numbers (**30473**, **32222**, **20810**)
   - Date of service: **31 August 2026**
   - Patient name: **Aaron Maher**
2. Open the **Express Plus Medicare App** (iOS / Android).
3. Tap **Claims** $\to$ **Make a Claim**.
4. Answer "Has the account been paid in full?" $\to$ **Yes**.
5. Take a photo of the itemised paid tax invoice.
6. Confirm your Westpac bank account details for direct deposit.
7. Tap **Submit**.
8. Medicare generally processes digital app claims within **2 to 3 business days**.

### Option C: Online Claiming via MyGov
1. Log in to [my.gov.au](https://my.gov.au).
2. Select your linked **Medicare** service.
3. Select **Make a Claim** $\to$ upload the digital PDF/image of your receipt.
4. Review and submit.

---

## 📋 Next Immediate Action Steps

1. **Locate your Invoice(s)**:
   - Check your email or hospital discharge folder for the invoice/receipt from your August 31 procedure.
2. **Review Payment Status**:
   - If unpaid: Note the **BPAY Biller Code** and **Reference Number** to pay via the Westpac App.
   - If paid: Check if an ECLIPSE lodgement receipt was attached.
3. **If Self-Claiming**:
   - Open the **Express Plus Medicare App** $\to$ take a snapshot of the receipt $\to$ submit for direct deposit to Westpac.
