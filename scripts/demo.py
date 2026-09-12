#!/usr/bin/env python3
"""Interactive & Batch Demo for AppleSupport Causal Agent.

Demonstrates 5 core architectural capabilities:
1. Standard Grounded Diagnostic Support (Battery drain)
2. Short Contextual Follow-up with Context Inheritance ("Still not working.")
3. Physical Safety Hazard Escalation ("Bulging and smoking battery")
4. Out-of-Scope Detection & Redirection ("Honda Civic oil change")
5. Third-Party Mention Isolation ("@TechFriend recommended...")
"""

import json
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent.support_agent import SupportAgent


def run_demo():
    agent = SupportAgent()

    scenarios = [
        {
            "title": "Scenario 1: Standard Grounded Troubleshooting",
            "description": "User asks a legitimate battery drain troubleshooting question.",
            "context": [],
            "query": "My iPhone battery is draining really fast after updating to iOS 11.",
        },
        {
            "title": "Scenario 2: Context Inheritance on Short Elliptical Query",
            "description": "User provides a 3-word follow-up ('Still not working.') which requires causal history.",
            "context": [
                {"author_type": "customer", "text": "My iPhone 7 speaker sound is crackling whenever I receive a call."},
                {"author_type": "support", "text": "We'd like to help with your audio. Have you tried restarting your device?"}
            ],
            "query": "Still not working.",
        },
        {
            "title": "Scenario 3: Physical Safety Hazard Boundary",
            "description": "Thermal hazard detected; system immediately escalates without dangerous DIY troubleshooting.",
            "context": [],
            "query": "My battery is bulging, sparking, and smoking from the charging port!",
        },
        {
            "title": "Scenario 4: Out-of-Scope Domain Detection",
            "description": "Unsupported automotive query redirected politely without hallucinating Apple troubleshooting.",
            "context": [],
            "query": "How do I change the oil in a 2015 Honda Civic?",
        },
        {
            "title": "Scenario 5: Third-Party Handle Authority Control",
            "description": "User quotes another user handle; mention is sanitized to @user to prevent authority leakage.",
            "context": [],
            "query": "@TechFriend recommended resetting network settings, but my Wi-Fi is still failing.",
        },
    ]

    print("=" * 80)
    print("  AppleSupport Causal Agent — Live Architecture Showcase")
    print("=" * 80)

    for idx, sc in enumerate(scenarios, 1):
        print(f"\n--- {sc['title']} ---")
        print(f"Goal: {sc['description']}")
        if sc["context"]:
            print("Prior History:")
            for turn in sc["context"]:
                print(f"  [{turn['author_type'].capitalize()}]: {turn['text']}")
        print(f"Customer Input: \"{sc['query']}\"")

        res = agent.predict(sc["context"], sc["query"])

        print(f"\nAgent Decision Outputs:")
        print(f"  - Primary Intent:       {res['intent']}")
        print(f"  - Intent Confidence:    {res['intent_confidence']:.2f}")
        print(f"  - Escalation State:     {res['escalation_decision']}")
        print(f"  - Decision Rationale:   {res['escalation_reason']}")
        print(f"  - Safety Rubric Pass:   {res['safety_passed']}")
        print(f"  - Grounding Status:     {res['grounding_status']}")
        print(f"  - Synthesized Response:\n    \"{res['draft_response']}\"")
        print("-" * 80)


if __name__ == "__main__":
    run_demo()
