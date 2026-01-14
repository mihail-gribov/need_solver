#!/usr/bin/env python3
"""
Extract numerical features for dog breeds using OpenAI API with web search.

Usage:
    python extract_features.py                    # Process all breeds
    python extract_features.py --breed akita     # Process single breed
    python extract_features.py --limit 10        # Process first 10 breeds
    python extract_features.py --dry-run         # Show what would be processed
"""

import json
import os
import re
import sys
import argparse
import logging
from pathlib import Path
from typing import Any

from openai import OpenAI
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

# Setup paths
SCRIPT_DIR = Path(__file__).parent
DOMAIN_DIR = SCRIPT_DIR.parent
CONFIG_FILE = DOMAIN_DIR / "config.json"


def load_config() -> dict:
    """Load domain config."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_config()
PROMPTS_DIR = DOMAIN_DIR / CONFIG["paths"]["prompts"]
CONTENT_DIR = DOMAIN_DIR / CONFIG["paths"]["content"]
SOURCE_DIR = DOMAIN_DIR / CONFIG["paths"]["source"]
OUTPUT_DIR = DOMAIN_DIR / CONFIG["paths"]["extracted"]

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract breed features using OpenAI API."""

    def __init__(
        self,
        model: str | None = None,
        use_web_search: bool | None = None
    ):
        load_dotenv()

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not found. Set it in environment or .env file.")

        llm_config = CONFIG["llm"]
        extraction_config = CONFIG["extraction"]

        self.model = model or llm_config["default_model"]
        self.temperature = llm_config["temperature"]["extraction"]
        self.use_web_search = use_web_search if use_web_search is not None else extraction_config["use_web_search"]
        self.web_search_tool = extraction_config["web_search_tool"]

        self.client = OpenAI(
            timeout=llm_config["timeout"],
            max_retries=llm_config["max_retries"]
        )

        # Setup Jinja2
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(PROMPTS_DIR)),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def load_breeds(self) -> list[dict]:
        """Load breed list from content/breeds.json."""
        breeds_file = CONTENT_DIR / "breeds.json"
        with open(breeds_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["breeds"]

    def load_breed_source(self, breed_id: str) -> dict | None:
        """Load source data for a breed."""
        source_file = SOURCE_DIR / f"breed_{breed_id}.json"
        if source_file.exists():
            with open(source_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def render_prompt(self, breed: dict, breed_data: dict | None) -> str:
        """Render the extraction prompt."""
        template = self.jinja_env.get_template("extract_features.prompt.md")
        return template.render(
            breed_id=breed["id"],
            breed_name=breed["name_en"],
            breed_data=breed_data or {}
        )

    def extract_json(self, text: str) -> str:
        """Extract JSON from model response."""
        # Try to find JSON block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            return json_match.group(1).strip()

        # Try to find raw JSON object
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            return brace_match.group(0)

        return text.strip()

    def call_api(self, prompt: str) -> dict:
        """Call OpenAI API and return parsed JSON."""
        kwargs = {
            "model": self.model,
            "input": prompt,
            "temperature": self.temperature,
        }

        if self.use_web_search:
            kwargs["tools"] = [{"type": self.web_search_tool}]

        log.debug(f"Calling API with model={self.model}, web_search={self.use_web_search}")

        response = self.client.responses.create(**kwargs)

        text = getattr(response, "output_text", None)
        if not text:
            raise RuntimeError("Empty response from API")

        json_str = self.extract_json(text)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            log.error(f"JSON parse error: {e}")
            log.error(f"Raw response: {text[:500]}...")
            raise

    # Required features (31 total)
    REQUIRED_FEATURES = [
        # Coat & Allergens
        "shedding", "coat_type", "dander_level", "grooming",
        # Health
        "health_robustness", "genetic_risk",
        # Living Conditions
        "apartment_ok", "barking", "energy", "reactivity", "noise_tolerance", "exercise_need",
        # Alone Time & Adaptability
        "alone_tolerance", "separation_anxiety_risk", "sitter_compatibility", "adaptability",
        # Social Compatibility
        "child_friendly", "pet_friendly", "stranger_friendly", "territoriality", "protectiveness",
        # Temperament
        "stress_sensitivity", "affection_level", "independence", "playfulness",
        # Training & Work
        "trainability", "working_drive", "behavior_management_need", "mental_stimulation",
        # Hunting Instincts
        "prey_drive", "hunting_instinct"
    ]

    REQUIRED_PARAMETERS = ["weight_kg", "height_cm", "lifespan_years"]

    def _validate_result(self, result: dict, breed_id: str) -> None:
        """Validate extracted result structure."""
        # Check top-level fields
        if "features" not in result:
            raise ValueError("Response missing 'features' field")
        if "parameters" not in result:
            raise ValueError("Response missing 'parameters' field")

        features = result["features"]
        parameters = result["parameters"]

        # Check features structure (each should be array of source entries)
        missing_features = []
        invalid_features = []

        for feat_id in self.REQUIRED_FEATURES:
            if feat_id not in features:
                missing_features.append(feat_id)
                continue

            feat_data = features[feat_id]
            if not isinstance(feat_data, list):
                invalid_features.append(f"{feat_id}: expected array, got {type(feat_data).__name__}")
                continue

            # Validate each source entry
            for i, entry in enumerate(feat_data):
                if not isinstance(entry, dict):
                    invalid_features.append(f"{feat_id}[{i}]: expected object, got {type(entry).__name__}")
                    continue
                if "value" not in entry:
                    invalid_features.append(f"{feat_id}[{i}]: missing 'value'")
                if "confidence" not in entry:
                    invalid_features.append(f"{feat_id}[{i}]: missing 'confidence'")
                if "source" not in entry:
                    invalid_features.append(f"{feat_id}[{i}]: missing 'source'")

        # Check parameters structure
        missing_params = []
        for param_id in self.REQUIRED_PARAMETERS:
            if param_id not in parameters:
                missing_params.append(param_id)

        # Log warnings but don't fail on missing features (LLM may not find all data)
        if missing_features:
            log.warning(f"{breed_id}: missing features ({len(missing_features)}): {', '.join(missing_features[:5])}...")
        if invalid_features:
            log.warning(f"{breed_id}: invalid feature entries: {invalid_features[:3]}")
        if missing_params:
            log.warning(f"{breed_id}: missing parameters: {missing_params}")

    def process_breed(self, breed: dict) -> dict | None:
        """Process a single breed and return extracted features."""
        breed_id = breed["id"]
        output_file = OUTPUT_DIR / f"{breed_id}.json"

        # Skip if already processed
        if output_file.exists():
            log.info(f"[SKIP] {breed_id} - already extracted")
            return None

        log.info(f"[EXTRACT] {breed['name_en']} ({breed_id})")

        # Load source data
        breed_data = self.load_breed_source(breed_id)

        # Render prompt
        prompt = self.render_prompt(breed, breed_data)

        try:
            result = self.call_api(prompt)

            # Validate result structure
            self._validate_result(result, breed_id)

            # Save result
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            log.info(f"[OK] {breed_id} - saved to {output_file.name}")
            return result

        except Exception as e:
            log.error(f"[ERROR] {breed_id}: {e}")
            return None

    def run(
        self,
        breed_id: str | None = None,
        limit: int | None = None,
        dry_run: bool = False
    ) -> dict[str, Any]:
        """Run extraction for breeds."""
        breeds = self.load_breeds()

        # Filter by breed_id if specified
        if breed_id:
            breeds = [b for b in breeds if b["id"] == breed_id]
            if not breeds:
                log.error(f"Breed not found: {breed_id}")
                return {"processed": 0, "errors": 1}

        # Apply limit
        if limit:
            breeds = breeds[:limit]

        log.info(f"Processing {len(breeds)} breeds (dry_run={dry_run})")

        if dry_run:
            for b in breeds:
                status = "SKIP" if (OUTPUT_DIR / f"{b['id']}.json").exists() else "PROCESS"
                print(f"[{status}] {b['id']} - {b['name_en']}")
            return {"processed": 0, "would_process": len(breeds)}

        results = {"processed": 0, "skipped": 0, "errors": 0}

        for breed in breeds:
            result = self.process_breed(breed)
            if result is None:
                if (OUTPUT_DIR / f"{breed['id']}.json").exists():
                    results["skipped"] += 1
                else:
                    results["errors"] += 1
            else:
                results["processed"] += 1

        log.info(f"Done: {results}")
        return results


def main():
    parser = argparse.ArgumentParser(description="Extract breed features using OpenAI API")
    parser.add_argument("--breed", type=str, help="Process single breed by ID")
    parser.add_argument("--limit", type=int, help="Limit number of breeds to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--model", type=str, default="gpt-4.1", help="OpenAI model to use")
    parser.add_argument("--no-web-search", action="store_true", help="Disable web search")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    extractor = FeatureExtractor(
        model=args.model,
        use_web_search=not args.no_web_search
    )

    results = extractor.run(
        breed_id=args.breed,
        limit=args.limit,
        dry_run=args.dry_run
    )

    sys.exit(0 if results.get("errors", 0) == 0 else 1)


if __name__ == "__main__":
    main()
