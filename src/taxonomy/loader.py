"""Taxonomy loader, object model, and validator."""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional

TAXONOMY_YAML_PATH = "src/taxonomy/taxonomy.yaml"
TAXONOMY_JSON_PATH = "src/taxonomy/taxonomy.json"


@dataclass
class Intent:
    name: str
    definition: str
    inclusion_criteria: List[str] = field(default_factory=list)
    exclusion_criteria: List[str] = field(default_factory=list)
    positive_examples: List[str] = field(default_factory=list)
    negative_examples: List[str] = field(default_factory=list)
    boundary_cases: List[str] = field(default_factory=list)
    support_behavior_notes: str = ""


@dataclass
class Taxonomy:
    version: str
    brand: str
    description: str
    intents: List[Intent] = field(default_factory=list)

    def get_intent(self, name: str) -> Optional[Intent]:
        for intent in self.intents:
            if intent.name == name:
                return intent
        return None

    def intent_names(self) -> List[str]:
        return [intent.name for intent in self.intents]


def parse_taxonomy_yaml(yaml_path: str = TAXONOMY_YAML_PATH) -> Dict[str, Any]:
    """Parses taxonomy.yaml into a structured dictionary without external dependencies."""
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"Taxonomy YAML not found at: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract top-level fields
    version_m = re.search(r'version:\s*"([^"]+)"', content)
    brand_m = re.search(r'brand:\s*"([^"]+)"', content)
    desc_m = re.search(r'description:\s*"([^"]+)"', content)

    taxonomy = {
        "version": version_m.group(1) if version_m else "taxonomy_v1",
        "brand": brand_m.group(1) if brand_m else "AppleSupport",
        "description": desc_m.group(1) if desc_m else "",
        "intents": [],
    }

    # Split into intent blocks
    intent_blocks = re.split(r'\n\s*-\s*name:\s*"([^"]+)"', content)
    for i in range(1, len(intent_blocks), 2):
        name = intent_blocks[i].strip()
        body = intent_blocks[i + 1]

        def extract_quoted_field(field_name: str) -> str:
            m = re.search(rf'{field_name}:\s*"([^"]+)"', body)
            return m.group(1) if m else ""

        def extract_list_field(field_name: str) -> List[str]:
            items = []
            m = re.search(rf'{field_name}:\s*\n((?:\s*-\s*"(?:[^"\\]|\\.)*"\s*(?:#.*)?\n?)+)', body)
            if m:
                raw_items = re.findall(r'-\s*"((?:[^"\\]|\\.)*)"', m.group(1))
                items = [it.replace('\\"', '"') for it in raw_items]
            return items

        # Support behavior notes might be a list or multiline string
        support_notes_list = extract_list_field("typical_support_behavior")
        support_notes_str = "; ".join(support_notes_list) if support_notes_list else extract_quoted_field("typical_support_behavior")

        intent = {
            "name": name,
            "definition": extract_quoted_field("definition"),
            "inclusion": extract_list_field("inclusion"),
            "exclusion": extract_list_field("exclusion"),
            "positive_examples": extract_list_field("positive_examples"),
            "negative_examples": extract_list_field("negative_examples"),
            "boundary_cases": extract_list_field("boundary_cases"),
            "typical_support_behavior": support_notes_str,
        }
        taxonomy["intents"].append(intent)

    # Cache as JSON for instant lookup
    os.makedirs(os.path.dirname(TAXONOMY_JSON_PATH), exist_ok=True)
    with open(TAXONOMY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, indent=2)

    return taxonomy


def load_taxonomy_dict(json_path: str = TAXONOMY_JSON_PATH, yaml_path: str = TAXONOMY_YAML_PATH) -> Dict[str, Any]:
    """Loads taxonomy as raw dictionary from cached JSON or parses from YAML."""
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return parse_taxonomy_yaml(yaml_path)


def load_taxonomy(json_path: str = TAXONOMY_JSON_PATH, yaml_path: str = TAXONOMY_YAML_PATH) -> Taxonomy:
    """Loads taxonomy into a typed Taxonomy data model object."""
    data = load_taxonomy_dict(json_path, yaml_path)
    intents = []
    for item in data.get("intents", []):
        intent = Intent(
            name=item["name"],
            definition=item.get("definition", ""),
            inclusion_criteria=item.get("inclusion", []),
            exclusion_criteria=item.get("exclusion", []),
            positive_examples=item.get("positive_examples", []),
            negative_examples=item.get("negative_examples", []),
            boundary_cases=item.get("boundary_cases", []),
            support_behavior_notes=item.get("typical_support_behavior", ""),
        )
        intents.append(intent)

    return Taxonomy(
        version=data.get("version", "taxonomy_v1"),
        brand=data.get("brand", "AppleSupport"),
        description=data.get("description", ""),
        intents=intents,
    )


def get_all_intent_names(yaml_path: str = TAXONOMY_YAML_PATH) -> List[str]:
    """Returns list of all registered canonical intent names."""
    tax = load_taxonomy(yaml_path=yaml_path)
    return tax.intent_names()


def validate_intent_name(intent_name: str, yaml_path: str = TAXONOMY_YAML_PATH) -> bool:
    """Validates if given string is a registered taxonomy intent."""
    return intent_name in get_all_intent_names(yaml_path=yaml_path)


if __name__ == "__main__":
    tax = parse_taxonomy_yaml()
    print(f"Loaded taxonomy version: {tax['version']}")
    print(f"Total intents: {len(tax['intents'])}")
    for it in tax["intents"]:
        print(f"  - {it['name']:<45}: {len(it['inclusion'])} incl, {len(it['exclusion'])} excl, {len(it['positive_examples'])} pos")
