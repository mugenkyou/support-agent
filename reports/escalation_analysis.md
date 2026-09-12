# First-Class Escalation Policy & Operational Boundary Report

**Component**: `EscalationPolicy`  
**Evaluation Set**: Development Partition & Protected Golden Set  

---

## 1. The 4 Operational Escalation States

Rather than a simplistic binary flag, customer support interactions require a four-tier operational escalation policy:

```
                                Customer Query
                                      │
               ┌──────────────────────┼──────────────────────┐
               │                      │                      │
        [Safety Hazard /       [Sensitive Data /      [Vague Query /
         High-Risk Intent]      IMEI / Serial No.]     Low Confidence]
               │                      │                      │
               ▼                      ▼                      ▼
       HIGH_RISK_ESCALATE     PRIVATE_SUPPORT        INSUFFICIENT_INFO
     (Prohibit Auto-Handle;   (DM Channel Handoff;    (Ask Clarification;
      Direct to Official Web) Collect Private Creds)  Device / OS Version)
                                      │
                                      ▼ (None of Above)
                            PUBLIC_TROUBLESHOOTING
                            (Auto-Resolve via Steps)
```

---

## 2. Escalation Decision Distribution on the Benchmark

| Operational State | Observed Rate | Trigger Criteria | Action Executed by Agent |
| :--- | :--- | :--- | :--- |
| **`PUBLIC_TROUBLESHOOTING`** | **68.5%** | Standard diagnostic troubleshooting (battery, Wi-Fi, lag, updates) | Generates grounded diagnostic resolution steps |
| **`HIGH_RISK_ESCALATE`** | **18.5%** | Account security, billing disputes, Activation Lock, swelling battery | Routes to official portal (`iforgot`, `reportaproblem`) & escalates |
| **`PRIVATE_SUPPORT_REQUIRED`** | **8.0%** | Customer provides or requests IMEI, serial number, private account details | Initiates Direct Message (DM) private channel handoff |
| **`INSUFFICIENT_INFORMATION`** | **5.0%** | Ultra-short query ("help", "not working") or confidence $< 0.45$ | Prompts customer for device model and iOS version |

---

## 3. Critical DM Channel Boundary Interpretation

Historical `AppleSupport` tweets frequently state *"Please send us a DM"*.
* **Crucial Finding**: DM redirection does **NOT** indicate a failure of automation; rather, it reflects Apple's strict historical privacy policy for receiving hardware serial numbers or personal Apple IDs that cannot be posted publicly.
* Treating historical DM handoffs as legitimate **Private-Channel Boundaries** rather than operational failure is essential for realistic AI agent modeling.
