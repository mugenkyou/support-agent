# Temporal Drift, Response Latency & OS Evolution Report

**Target Brand**: `AppleSupport`  
**Phase**: Phase 2 — Dataset Construction & Leakage Control  

---

## 1. Temporal Volume Distribution

The `AppleSupport` corpus spans March 2016 to December 2017, but is heavily concentrated during the **Q4 2017 Apple Product Launch & iOS 11 Rollout**:

```
Monthly AppleSupport Volume (Tweets):
  2016-03 to 2017-08:       47 tweets (Early historical pilot)
  2017-09:                 144 tweets (iOS 11 Beta / Launch prep)
  2017-10:              43,102 tweets (iOS 11.0 / 11.0.3 Public Surge & iPhone 8 launch)
  2017-11:              58,844 tweets (iPhone X Launch & iOS 11.1 / 11.2 updates)
  2017-12:               4,716 tweets (First 3 days of December)
```

**Key Finding**: Over **95.6%** of all interactions occur within a concentrated 60-day window (October 1 to November 30, 2017).

---

## 2. Operating System & Device Evolution

We tracked mentions of key operating systems across all `AppleSupport` responses:

| Operating System Mentioned | Total Mentions in Dataset | Primary Monthly Occurrence | Core Support Topics |
| :--- | :--- | :--- | :--- |
| **iOS 11** | **6,937** | Oct–Dec 2017 | Post-update battery drain, Control Center Wi-Fi toggle changes, 32-bit app deprecation, keyboard lag |
| **macOS (Sierra / High Sierra)** | **684** | Oct–Dec 2017 | APFS conversion issues, FaceTime login errors, OS X update stall |
| **watchOS / Apple Watch** | **693** | Oct–Dec 2017 | Apple Watch Series 3 pairing, LTE connectivity, workout calorie sync |
| **iOS 10** | **45** | 2016–2017 | Legacy 10.3.3 update verification |
| **iOS 9** | **7** | 2016–2017 | Legacy device compatibility limits (iPhone 4s) |

---

## 3. Response Latency Analysis

Response latency was calculated on all 106,646 customer $\rightarrow$ support pairs:

$$\text{Latency} = T(\text{Support Tweet}) - T(\text{Customer Tweet})$$

| Latency Metric | Seconds | Minutes / Hours | Interpretation |
| :--- | :--- | :--- | :--- |
| **Median (p50)** | 4,258 s | **70.97 minutes** (~1.18 hours) | Standard Twitter queue turnaround |
| **p75** | 12,474 s | **207.9 minutes** (~3.46 hours) | Moderate queue backlog |
| **p90** | 26,797 s | **446.6 minutes** (~7.44 hours) | End-of-day / overnight queue clearance |
| **p95** | 31,762 s | **529.4 minutes** (~8.82 hours) | Extended backlog during viral outages |
| **Max** | 2,837,706 s | **32.84 days** | Late customer follow-up response |

### Latency by Interaction Category:
- **Pure Diagnostic Responses**: Median **55.13 minutes** (Fastest triage).
- **Direct Message (DM) Redirections**: Median **69.92 minutes** (Standard privacy handoff).
- **Link Sharing (Support Articles)**: Median **95.55 minutes** (In-depth documentation search).

---

## 4. Grounding Policy & External Documentation Implications

1. **Strict Historical Grounding**: Because the corpus reflects 2017 Apple device and OS software states (iOS 11, iPhone 7/8/X, macOS High Sierra), the AI Support Agent must learn to resolve customer queries according to **historical brand behavior at that point in time**.
2. **Exclusion of Modern Documentation**: Modern Apple support documentation (iOS 16/17/18, Apple Silicon M1/M2/M3, USB-C iPhones) must **NEVER** be mixed into the primary benchmark. Doing so would create anachronistic hallucination (e.g. suggesting an iOS 16 battery widget for an iOS 11 user on an iPhone 6s).
3. **Temporal Evaluation Integrity**: Evaluating on the late November 2017 test set ($N=10,666$) accurately tests whether an agent trained on early October data can generalize to point releases (iOS 11.1/11.2) without temporal lookahead leakage.
