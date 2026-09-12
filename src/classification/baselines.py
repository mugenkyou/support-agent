"""Intent Classification Baselines for AppleSupport.

Implements 4 distinct classifiers:
- Baseline 0: Majority Class Classifier
- Baseline 1: TF-IDF (1-3 ngrams) + Regularized Logistic Regression
- Baseline 2: Lexical / Keyword Diagnostic Matcher with Precedence Hierarchy
- Baseline 3: Semantic Definition-Grounded Classifier (Zero-Shot / Embedding-based)
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from src.taxonomy.loader import load_taxonomy


class MajorityClassifier:
    """Baseline 0: Majority Class Classifier."""

    def __init__(self, default_intent: str = "software_update_and_os_compatibility"):
        self.default_intent = default_intent
        self.classes: List[str] = [default_intent]

    def fit(self, texts: List[str], labels: List[str]):
        if labels:
            counts = {}
            for lbl in labels:
                counts[lbl] = counts.get(lbl, 0) + 1
            self.default_intent = max(counts, key=counts.get)
            self.classes = sorted(list(set(labels)))

    def predict(self, texts: List[str]) -> List[str]:
        return [self.default_intent for _ in texts]

    def predict_single(self, text: str) -> Tuple[str, float]:
        return self.default_intent, 1.0


class TFIDFLogisticRegressionClassifier:
    """Baseline 1: TF-IDF n-grams (1-2) + Logistic Regression."""

    def __init__(self, C: float = 1.0, max_iter: int = 500, class_weight: str = "balanced"):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=15000,
            min_df=2,
            sublinear_tf=True,
            token_pattern=r"(?u)\b\w+\b|<url>|<user>",
        )
        self.model = LogisticRegression(
            C=C,
            max_iter=max_iter,
            class_weight=class_weight,
            solver="lbfgs",
            random_state=42,
        )
        self.classes_: List[str] = []

    def fit(self, texts: List[str], labels: List[str]):
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, labels)
        self.classes_ = list(self.model.classes_)

    def predict(self, texts: List[str]) -> List[str]:
        X = self.vectorizer.transform(texts)
        return list(self.model.predict(X))

    def predict_proba(self, texts: List[str]) -> np.ndarray:
        X = self.vectorizer.transform(texts)
        return self.model.predict_proba(X)

    def predict_single(self, text: str) -> Tuple[str, float]:
        X = self.vectorizer.transform([text])
        probs = self.model.predict_proba(X)[0]
        pred_idx = np.argmax(probs)
        return self.classes_[pred_idx], float(probs[pred_idx])


class LexicalKeywordClassifier:
    """Baseline 2: Lexical Keyword Diagnostic Matcher with Precedence Rules."""

    KEYWORD_MAP = {
        "hardware_damage_and_repair_service": [
            r"\b(cracked|broken|shattered|screen|glass|water\s+damage|dropped|liquid|genius\s+bar|repair|fix\s+screen|display\s+broken|physical\s+damage)\b"
        ],
        "activation_lock_and_device_security": [
            r"\b(activation\s+lock|locked\s+to\s+owner|icloud\s+lock|lost\s+mode|find\s+my\s+iphone|find\s+my|stolen|imei\s+lock|locked\s+device)\b"
        ],
        "apple_id_and_account_security": [
            r"\b(apple\s*id|appleid|iforgot|reset\s+password|forgot\s+password|locked\s+account|2fa|verification\s+code|two\s*factor|disabled\s+account|security\s+questions|sign\s+in|login)\b"
        ],
        "billing_subscription_and_app_store_charges": [
            r"\b(charged|charge|refund|subscription|billing|receipt|apple\s+music\s+charge|itunes\s+charge|unauthorized\s+charge|app\s+store\s+purchase|payment|dollars?|\$\d+)\b"
        ],
        "battery_drain_and_charging_issues": [
            r"\b(battery|drain|dying|shuts?\s+off|powers?\s+off|charges?|charging|lightning\s+cable|cable|30%|40%|50%|percentage|dies\s+fast|heating\s+up|overheat)\b"
        ],
        "network_and_connectivity_troubleshooting": [
            r"\b(wifi|wi-fi|bluetooth|cellular|lte|4g|3g|no\s+service|searching\.\.\.|disconnecting|disconnect|airdrop|hotspot|carrier|signal|connection)\b"
        ],
        "audio_music_and_accessory_issues": [
            r"\b(airpods?|earphones?|headphones?|speaker|microphone|mic|sound|audio|distorted|crackling|volume|apple\s+music|earbuds?|aux)\b"
        ],
        "storage_backup_and_icloud_sync": [
            r"\b(storage\s+full|other\s+storage|icloud\s+backup|backup\s+failed|sync|syncing|photos\s+not\s+uploading|icloud\s+photos|backup|space|storage)\b"
        ],
        "app_crash_freeze_and_performance_lag": [
            r"\b(lag|laggy|freeze|freezing|frozen|unresponsive|keyboard|stutter|crashing|crash|crashes|slow|app\s+keeps\s+closing|delay|lock\s*up)\b"
        ],
        "software_update_and_os_compatibility": [
            r"\b(ios\s*11|update|updated|updating|install|installer|download|unable\s+to\s+verify|verifying\s+update|bootloop|itunes\s+restore|beta|upgrade|os\s*version)\b"
        ],
        "feedback_complaint_or_general_inquiry": [
            r"\b(store|worst|hate|apple\s+sucks|disappointed|customer\s+service|feedback|when\s+is\s+release|feature\s+request|suggestion|question|guide|books?)\b"
        ],
    }


    PRECEDENCE_ORDER = [
        "hardware_damage_and_repair_service",
        "activation_lock_and_device_security",
        "apple_id_and_account_security",
        "billing_subscription_and_app_store_charges",
        "battery_drain_and_charging_issues",
        "network_and_connectivity_troubleshooting",
        "audio_music_and_accessory_issues",
        "storage_backup_and_icloud_sync",
        "app_crash_freeze_and_performance_lag",
        "software_update_and_os_compatibility",
        "feedback_complaint_or_general_inquiry",
    ]

    def __init__(self):
        self.patterns = {
            intent: [re.compile(p, re.IGNORECASE) for p in pats]
            for intent, pats in self.KEYWORD_MAP.items()
        }

    def predict_single(self, text: str) -> Tuple[str, float]:
        matches = {}
        for intent in self.PRECEDENCE_ORDER:
            pats = self.patterns[intent]
            match_count = sum(len(p.findall(text)) for p in pats)
            if match_count > 0:
                matches[intent] = match_count

        if not matches:
            return "software_update_and_os_compatibility", 0.3

        if "battery_drain_and_charging_issues" in matches and "software_update_and_os_compatibility" in matches:
            return "battery_drain_and_charging_issues", 0.9

        for intent in self.PRECEDENCE_ORDER:
            if intent in matches:
                confidence = min(0.95, 0.5 + 0.15 * matches[intent])
                return intent, confidence

        return "software_update_and_os_compatibility", 0.3

    def predict(self, texts: List[str]) -> List[str]:
        return [self.predict_single(t)[0] for t in texts]


class SemanticTaxonomyClassifier:
    """Baseline 3: Semantic Classifier Grounded in Taxonomy Definitions."""

    def __init__(self, taxonomy_path: str = "src/taxonomy/taxonomy.yaml"):
        self.taxonomy = load_taxonomy(yaml_path=taxonomy_path)
        self.intents = [intent.name for intent in self.taxonomy.intents]
        self.intent_descriptions = {}

        for intent in self.taxonomy.intents:
            doc = (
                f"{intent.name.replace('_', ' ')}. "
                f"{intent.definition} "
                f"{' '.join(intent.inclusion_criteria)} "
                f"{' '.join(intent.positive_examples)}"
            )
            self.intent_descriptions[intent.name] = doc

        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        doc_texts = [self.intent_descriptions[i] for i in self.intents]
        self.doc_matrix = self.vectorizer.fit_transform(doc_texts)

    def predict_single(self, text: str) -> Tuple[str, float]:
        q_vec = self.vectorizer.transform([text])
        sims = (q_vec * self.doc_matrix.T).toarray()[0]
        max_idx = int(np.argmax(sims))
        score = float(sims[max_idx])
        conf = float(1.0 / (1.0 + math.exp(-score * 5))) if score > 0 else 0.2
        return self.intents[max_idx], conf

    def predict(self, texts: List[str]) -> List[str]:
        return [self.predict_single(t)[0] for t in texts]

