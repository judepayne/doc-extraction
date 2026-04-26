#!/usr/bin/env python3
"""Validate extracted facility/deal JSON with project-local validation logic."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

from validation_lib.validation_engine import ValidationEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = PROJECT_ROOT / "validation"


class LocalConfigLoader:
    """Minimal config loader interface required by ValidationEngine."""

    def __init__(self, validation_dir: Path):
        self.validation_dir = validation_dir
        self.cache_dir = Path("/tmp/doc-extraction-validation")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with (validation_dir / "business-config.yaml").open() as f:
            self.business_config = yaml.safe_load(f)

    def get_business_config(self) -> Dict[str, Any]:
        """Return project-local business configuration."""
        return self.business_config


def flatten_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten hierarchical validation results."""
    flattened = []
    for result in results:
        flattened.append(result)
        flattened.extend(flatten_results(result.get("children", [])))
    return flattened


def validate(entity_type: str, ruleset_name: str, json_path: Path) -> List[Dict[str, Any]]:
    """Validate one extraction file and return validation results."""
    with json_path.open() as f:
        entity_data = json.load(f)
    if not isinstance(entity_data, dict):
        raise ValueError("Extraction JSON root must be an object")

    config_loader = LocalConfigLoader(VALIDATION_DIR)
    engine = ValidationEngine(config_loader=config_loader, logic_dir=str(VALIDATION_DIR))
    required_terms = engine.get_required_data(
        entity_type=entity_type,
        schema_url=entity_data.get("$schema", ""),
        ruleset_name=ruleset_name,
    )
    required_data = {term: None for term in required_terms}
    return engine.validate(entity_type, entity_data, ruleset_name, required_data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate facility/deal extraction JSON against project-local rules."
    )
    parser.add_argument("json_path", type=Path, help="Path to extracted JSON file")
    parser.add_argument(
        "--entity",
        choices=["facility", "deal"],
        required=True,
        help="Entity type to validate",
    )
    parser.add_argument(
        "--ruleset",
        choices=["facility", "deal"],
        help="Ruleset to run; defaults to the entity name",
    )
    args = parser.parse_args()

    ruleset_name = args.ruleset or args.entity
    if ruleset_name != args.entity:
        print(
            f"error: ruleset '{ruleset_name}' does not match entity '{args.entity}'",
            file=sys.stderr,
        )
        return 2

    try:
        results = validate(args.entity, ruleset_name, args.json_path)
    except Exception as e:
        print(f"validation failed to run: {e}", file=sys.stderr)
        return 2
    print(json.dumps(results, indent=2))

    flattened = flatten_results(results)
    if not flattened:
        return 1
    statuses = {result.get("status") for result in flattened}
    if statuses.intersection({"FAIL", "ERROR", "NORUN"}):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
