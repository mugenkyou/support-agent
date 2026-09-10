# Golden Evaluation Set Labeling Guide

**Target Brand**: `AppleSupport`  
**Taxonomy Version**: `taxonomy_v1`  
**Purpose**: Provide clear, operational annotation standards for human labelers evaluating customer support intents.

---

## 1. Annotation Unit & Information Boundary

### 1.1 The Annotation Unit
Labelers must annotate the **Primary Support Intent** of the customer's incoming message:

$$\mathcal{U}_k = \Big( \text{Context: } (C_1, S_1, \dots, C_{k-1}, S_{k-1}), \quad \text{Current Message: } C_k \Big)$$

### 1.2 Information-Time Boundary
- **ALLOWED**: You may only inspect the preceding conversation history $(C_1, S_1, \dots)$ and the current customer message $C_k$.
- **STRICTLY FORBIDDEN**: You must **NOT** inspect the subsequent support response $S_k$ or future customer follow-ups $(C_{k+1}, \dots)$ to determine the intent. The annotation must reflect the customer's stated need at the moment $C_k$ was submitted.

---

## 2. Multi-Intent Policy (Single Primary Intent Selection)

When a customer message expresses more than one symptom or concern (e.g. *"My iPhone 7 battery dies in 2 hours and Wi-Fi won't connect"*):
1. **Root Actionable Intent**: Select the intent representing the primary defect the customer is asking Apple Support to resolve.
2. **Precedence Hierarchy for Multi-Topic Complaints**:
   - **Tier 1 (Physical Safety & Urgent Loss)**: `hardware_damage_and_repair_service` > `activation_lock_and_device_security`
   - **Tier 2 (Account Security & Financial Charges)**: `apple_id_and_account_security` > `billing_subscription_and_app_store_charges`
   - **Tier 3 (Specific Hardware/OS Malfunctions)**: `battery_drain_and_charging_issues` > `network_and_connectivity_troubleshooting` > `audio_music_and_accessory_issues` > `storage_backup_and_icloud_sync`
   - **Tier 4 (Software Stability & Updates)**: `app_crash_freeze_and_performance_lag` > `software_update_and_os_compatibility`
   - **Tier 5 (Broad Feedback)**: `feedback_complaint_or_general_inquiry`

---

## 3. Complete 11-Intent Operational Taxonomy

### 1. `software_update_and_os_compatibility`
- **Definition**: Inquiries regarding OS update installation, verification stalls, downgrade procedures, or device model compatibility.
- **Inclusion**: Installing iOS 11, iTunes update errors (e.g. error 3194), compatibility checks for legacy devices.
- **Exclusion**: Battery drain after update (use `battery_drain_and_charging_issues`).
- **Rule**: If installation failed $\rightarrow$ `software_update_and_os_compatibility`. If update finished but phone runs hot/dies $\rightarrow$ `battery_drain_and_charging_issues`.

### 2. `battery_drain_and_charging_issues`
- **Definition**: Rapid battery depletion, unexpected shutdowns at 20-30%, charging failure, or device overheating.
- **Inclusion**: Battery percentage drops, slow charging, charger accessory warnings, overheating.
- **Exclusion**: Physically swollen battery lifting the screen (use `hardware_damage_and_repair_service`).

### 3. `network_and_connectivity_troubleshooting`
- **Definition**: Wi-Fi, Bluetooth, Cellular Data, Hotspot, GPS, or CarPlay connection failures.
- **Inclusion**: Wi-Fi dropping, Bluetooth pairing failure, "No Service", mobile data loss.
- **Exclusion**: AirPods audio distortion with established Bluetooth pairing (use `audio_music_and_accessory_issues`).

### 4. `app_crash_freeze_and_performance_lag`
- **Definition**: App crashes, screen freezing, keyboard typing lag, UI stutter, or unresponsiveness.
- **Inclusion**: Native or third-party apps quitting unexpectedly, keyboard lag, touchscreen stutter.
- **Exclusion**: Physical screen glass shatter (use `hardware_damage_and_repair_service`).

### 5. `apple_id_and_account_security`
- **Definition**: Apple ID password recovery, account disabled for security reasons, 2FA verification code issues.
- **Inclusion**: iforgot.apple.com procedures, locked Apple ID, trusted phone number verification.
- **Exclusion**: Device stuck on Activation Lock screen after factory reset (use `activation_lock_and_device_security`).

### 6. `billing_subscription_and_app_store_charges`
- **Definition**: App Store / iTunes unauthorized charges, refund requests, subscription cancellations.
- **Inclusion**: Double billing, accidental in-app purchases, cancelling trial subscriptions.
- **Exclusion**: Hardware refund at Apple Retail Store (use `feedback_complaint_or_general_inquiry`).

### 7. `storage_backup_and_icloud_sync`
- **Definition**: "iPhone Storage Full" warnings, system storage cleanup, iCloud backup failures, cross-device photo sync issues.
- **Inclusion**: Freeing device storage, iCloud backup stalls, Photos/Notes sync across Mac/iPhone.
- **Exclusion**: Forgotten Apple ID password (use `apple_id_and_account_security`).

### 8. `hardware_damage_and_repair_service`
- **Definition**: Cracked screen, liquid damage, broken buttons, swollen battery, Genius Bar repair booking.
- **Inclusion**: Physical drops, shattered glass, water immersion, broken microphone hardware.
- **Exclusion**: Software keyboard lag (use `app_crash_freeze_and_performance_lag`).

### 9. `activation_lock_and_device_security`
- **Definition**: Activation Lock screen, Find My iPhone remote lock, lost/stolen device lockouts.
- **Inclusion**: Locked to previous owner's Apple ID, erasing lost device remotely, proof-of-purchase unlocking.
- **Exclusion**: Forgotten lockscreen passcode on user's own device (use `apple_id_and_account_security`).

### 10. `audio_music_and_accessory_issues`
- **Definition**: AirPods sound defects, microphone muffled on calls, speaker crackle, Apple Music playlist sync.
- **Inclusion**: One AirPod not working, receiver quiet on phone calls, Apple Music library sync.
- **Exclusion**: Bluetooth pairing failure (use `network_and_connectivity_troubleshooting`).

### 11. `feedback_complaint_or_general_inquiry`
- **Definition**: Broad complaints, brand praise, retail store inquiries, or vague statements without a specific technical problem.
- **Inclusion**: Store opening hours, general praise/frustration without actionable troubleshooting symptom.
- **Exclusion**: Any actionable technical defect with identifiable symptoms.

---

## 4. Disagreement & Adjudication Procedure

1. Annotators work independently without viewing peer labels.
2. Inter-annotator agreement is computed using Cohen's Kappa.
3. Every disagreement is reviewed in `evaluations/golden_set/adjudication.md` by checking the precedence hierarchy and context.
4. The final ground truth is assigned and frozen.
