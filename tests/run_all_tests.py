"""Central test runner for Phase 2 test suite."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))


def run_phase2_test_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    test_summary = {
        "tests_run": result.testsRun,
        "failures_count": len(result.failures),
        "errors_count": len(result.errors),
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "failures": [f[0].id() for f in result.failures],
        "errors": [e[0].id() for e in result.errors],
    }

    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/phase2_test_results.json", "w", encoding="utf-8") as f:
        json.dump(test_summary, f, indent=2)

    print("\n" + "=" * 80)
    print(f"PHASE 2 TEST SUITE RESULT: {test_summary['status']} ({result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun} passed)")
    print("=" * 80)

    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    run_phase2_test_suite()
