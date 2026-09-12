"""Tests for Intent Classification Module (Baselines and Metrics)."""

import unittest
from src.classification.baselines import (
    MajorityClassifier,
    TFIDFLogisticRegressionClassifier,
    LexicalKeywordClassifier,
    SemanticTaxonomyClassifier,
)
from src.classification.metrics import compute_classification_metrics


class TestClassification(unittest.TestCase):
    def setUp(self):
        self.classes = [
            "software_update_and_os_compatibility",
            "battery_drain_and_charging_issues",
            "network_and_connectivity_troubleshooting",
            "app_crash_freeze_and_performance_lag",
            "apple_id_and_account_security",
            "billing_subscription_and_app_store_charges",
            "storage_backup_and_icloud_sync",
            "hardware_damage_and_repair_service",
            "activation_lock_and_device_security",
            "audio_music_and_accessory_issues",
            "feedback_complaint_or_general_inquiry",
        ]

    def test_majority_classifier(self):
        clf = MajorityClassifier()
        clf.fit(["a", "b", "c"], ["battery_drain_and_charging_issues", "battery_drain_and_charging_issues", "network_and_connectivity_troubleshooting"])
        preds = clf.predict(["my iphone is not working"])
        self.assertEqual(preds[0], "battery_drain_and_charging_issues")

    def test_tfidf_logreg_classifier(self):
        train_x = [
            "my battery drains in 2 hours since ios 11",
            "wifi drops out constantly on home network",
            "forgot my apple id password please help me reset",
            "got charged twice for apple music subscription",
            "screen is cracked after dropping on concrete",
        ]
        train_y = [
            "battery_drain_and_charging_issues",
            "network_and_connectivity_troubleshooting",
            "apple_id_and_account_security",
            "billing_subscription_and_app_store_charges",
            "hardware_damage_and_repair_service",
        ]
        clf = TFIDFLogisticRegressionClassifier()
        clf.fit(train_x, train_y)
        pred, conf = clf.predict_single("my battery dies fast")
        self.assertIn(pred, train_y)
        self.assertGreaterEqual(conf, 0.0)

    def test_lexical_keyword_classifier_and_precedence(self):
        clf = LexicalKeywordClassifier()
        # Battery precedence over OS update
        pred, conf = clf.predict_single("@AppleSupport my battery dies in 1 hour after updating to ios 11")
        self.assertEqual(pred, "battery_drain_and_charging_issues")
        self.assertGreater(conf, 0.5)

        # Hardware precedence
        pred_hw, _ = clf.predict_single("screen shattered need genius bar appointment")
        self.assertEqual(pred_hw, "hardware_damage_and_repair_service")

    def test_semantic_taxonomy_classifier(self):
        clf = SemanticTaxonomyClassifier(taxonomy_path="src/taxonomy/taxonomy.yaml")
        pred, conf = clf.predict_single("cannot install ios 11 verification failed error")
        self.assertEqual(pred, "software_update_and_os_compatibility")

    def test_classification_metrics_computation(self):
        y_true = ["battery_drain_and_charging_issues", "apple_id_and_account_security", "hardware_damage_and_repair_service"]
        y_pred = ["battery_drain_and_charging_issues", "apple_id_and_account_security", "battery_drain_and_charging_issues"]
        metrics = compute_classification_metrics(y_true, y_pred, self.classes)
        self.assertAlmostEqual(metrics["accuracy"], 2 / 3, places=2)
        self.assertIn("macro_f1", metrics)
        self.assertIn("per_class", metrics)


if __name__ == "__main__":
    unittest.main()
