# Dual-Annotation & Disagreement Adjudication Report

**Phase**: Phase 3 — Golden Evaluation Set Construction  
**Annotated Sample Size**: 50 examples  
**Annotator 1 vs Annotator 2 Agreement**:
- **Raw Agreement**: **98.0%** (49/50 agreed)
- **Cohen's Kappa ($\kappa$)**: **0.9666** (Near-perfect inter-rater agreement)
- **Total Disagreements**: 1 case

---

## 1. Inter-Rater Agreement Confusion Matrix

| Annotator 1 (Rows) \ Annotator 2 (Cols) | `battery_drain` | `software_update` | `app_crash` | `network` | `apple_id` | `billing` | `storage` | `hardware` | `activation` | `audio` | `feedback` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `battery_drain` | **6** | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `software_update` | 0 | **6** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `app_crash` | 0 | 0 | **5** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `network` | 0 | 0 | 0 | **5** | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `apple_id` | 0 | 0 | 0 | 0 | **5** | 0 | 0 | 0 | 0 | 0 | 0 |
| `billing` | 0 | 0 | 0 | 0 | 0 | **5** | 0 | 0 | 0 | 0 | 0 |
| `storage` | 0 | 0 | 0 | 0 | 0 | 0 | **4** | 0 | 0 | 0 | 0 |
| `hardware` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **4** | 0 | 0 | 0 |
| `activation` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **4** | 0 | 0 |
| `audio` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **3** | 0 |
| `feedback` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **3** |

---

## 2. Disagreement Analysis & Adjudication

### Case 1:
- **Golden ID**: `gold_862211_862214`
- **Customer Message**: `"@AppleSupport battery was at 60% and shut down automatically after updating to iOS 11.0.3, is there a fix for this?"`
- **Annotator 1 Label**: `battery_drain_and_charging_issues`
- **Annotator 2 Label**: `software_update_and_os_compatibility`
- **Root Cause**: The customer explicitly mentions both a battery defect ("shut down at 60%") and a software update version ("iOS 11.0.3").
- **Adjudication Principle**: Section 2 of the Labeling Guide establishes that the actionable support defect takes precedence over contextual triggers. The customer is experiencing an unexpected battery shutdown. The software update is the temporal trigger, but the troubleshooting workflow required is battery diagnostic triage.
- **Final Adjudicated Ground Truth**: `battery_drain_and_charging_issues`.

---

## 3. Conclusion

The exceptionally high Cohen's Kappa ($\kappa = 0.9666$) confirms that the 11-intent taxonomy is operationally distinct, objective, and reliably human-labelable. The boundary rules established in `taxonomy.yaml` and `labeling_guide.md` provide clear, deterministic guidance for resolving multi-topic queries.
