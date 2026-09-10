# Golden Evaluation Set Sampling Methodology

**Target Brand**: `AppleSupport`  
**Total Golden Benchmark Size**: 200 examples  
**Source Split**: Primary Test Partition (and Dev Partition for rare coverage)  

---

## 1. Sampling Objectives

The golden evaluation set is engineered to test real-world agent competence across both common high-volume support workflows and critical low-frequency operational intents:
1. **Natural Representation**: Common issues (battery drain, software update, app crashing) maintain robust sample counts.
2. **Protection of Rare High-Stakes Intents**: Low-frequency but critical categories (e.g. `activation_lock_and_device_security`, `hardware_damage_and_repair_service`) are deliberately oversampled so that benchmark evaluation metrics (Precision, Recall, F1) remain statistically meaningful.
3. **Conversational Multi-Turn Depth**: Includes single-turn initial queries and deep multi-turn follow-ups where antecedent context is required to resolve references.
4. **Adversarial & Boundary Rigor**: Deliberately includes queries containing misleading keywords (e.g. mentioning "iOS 11" while describing a battery defect).

---

## 2. Distribution & Stratification Table

| Intent Name | Full Corpus Count (Est.) | Full Corpus % | Golden Set Count | Golden Set % | Stratified Oversampling Factor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `software_update_and_os_compatibility` | 29,682 | 27.83% | 22 | 11.0% | 0.40x |
| `battery_drain_and_charging_issues` | 10,440 | 9.79% | 22 | 11.0% | 1.12x |
| `network_and_connectivity_troubleshooting` | 4,001 | 3.75% | 20 | 10.0% | 2.67x |
| `app_crash_freeze_and_performance_lag` | 10,318 | 9.67% | 20 | 10.0% | 1.03x |
| `apple_id_and_account_security` | 4,551 | 4.27% | 18 | 9.0% | 2.11x |
| `billing_subscription_and_app_store_charges` | 5,559 | 5.21% | 18 | 9.0% | 1.73x |
| `storage_backup_and_icloud_sync` | 3,806 | 3.57% | 18 | 9.0% | 2.52x |
| `hardware_damage_and_repair_service` | 6,274 | 5.88% | 18 | 9.0% | 1.53x |
| `activation_lock_and_device_security` | 1,915 | 1.80% | 15 | 7.5% | **4.17x (Oversampled)** |
| `audio_music_and_accessory_issues` | 3,727 | 3.49% | 15 | 7.5% | 2.15x |
| `feedback_complaint_or_general_inquiry` | 26,373 | 24.74% | 14 | 7.0% | 0.28x |
| **TOTAL** | **106,646** | **100.00%** | **200** | **100.00%** | **Balanced Benchmark** |

---

## 3. Conversation Depth Distribution in Golden Set
- **Single-Turn Initial Interactions ($|\mathcal{H}| = 0$)**: 134 examples (67.0%)
- **Multi-Turn Follow-Up Interactions ($|\mathcal{H}| \ge 1$)**: 66 examples (33.0%)
  - 2-turn history: 38 examples
  - 3-turn history: 18 examples
  - 4+ turn history: 10 examples

---

## 4. Leakage & Contamination Protection

1. **Test-Partition Alignment**: All golden examples are sourced from the unseen `Test` and `Dev` temporal partitions.
2. **Permanent RAG / Index Exclusion**: Every `golden_id` is registered in `src/data/leakage.py` and filtered out from all training, demonstration, and retrieval corpora.
