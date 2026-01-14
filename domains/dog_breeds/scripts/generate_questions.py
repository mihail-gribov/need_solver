#!/usr/bin/env python3
"""
Generate question formulations for user needs using OpenAI API.

Usage:
    python generate_questions.py                    # Process all needs
    python generate_questions.py --need hypoallergenic  # Process single need
    python generate_questions.py --dry-run          # Show what would be processed
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
OUTPUT_DIR = DOMAIN_DIR / CONFIG["paths"]["questions"]

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


class QuestionGenerator:
    """Generate questions for user needs using OpenAI API."""

    def __init__(self, model: str | None = None):
        load_dotenv()

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not found. Set it in environment or .env file.")

        llm_config = CONFIG["llm"]
        self.model = model or llm_config["default_model"]
        self.temperature = llm_config["temperature"]["generation"]
        timeout = llm_config["timeout"]
        max_retries = llm_config["max_retries"]

        self.client = OpenAI(timeout=timeout, max_retries=max_retries)

        # Setup Jinja2
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(PROMPTS_DIR)),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def load_user_needs(self) -> dict:
        """Load user_needs.json."""
        needs_file = CONTENT_DIR / "user_needs.json"
        with open(needs_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_object_features(self) -> dict:
        """Load object_features.json with breed characteristics."""
        features_file = CONTENT_DIR / "object_features.json"
        with open(features_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_block_info(self, block_id: str, blocks: list[dict]) -> dict:
        """Get block name and description by ID."""
        for block in blocks:
            if block["id"] == block_id:
                return block
        return {"id": block_id, "name": block_id, "description": ""}

    def render_prompt(
        self,
        need: dict,
        block_info: dict,
        questions_count: int,
        object_features: dict
    ) -> str:
        """Render the question generation prompt."""
        template = self.jinja_env.get_template("generate_questions.prompt.md")
        return template.render(
            need_id=need["id"],
            need_name=need["name"],
            need_description=need["description"],
            block_name=block_info["name"],
            block_description=block_info.get("description", ""),
            questions_count=questions_count,
            features=object_features["features"],
            size_group=object_features["size_group"],
            height_group=object_features["height_group"],
            lifespan_group=object_features["lifespan_group"]
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
        log.debug(f"Calling API with model={self.model}")

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=self.temperature,
        )

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

    def process_need(
        self,
        need: dict,
        block_info: dict,
        questions_count: int,
        object_features: dict
    ) -> dict | None:
        """Process a single need and return generated questions."""
        need_id = need["id"]
        output_file = OUTPUT_DIR / f"{need_id}.json"

        # Skip if already processed
        if output_file.exists():
            log.info(f"[SKIP] {need_id} - already generated")
            return None

        log.info(f"[GENERATE] {need['name']} ({need_id})")

        # Render prompt
        prompt = self.render_prompt(need, block_info, questions_count, object_features)

        try:
            result = self.call_api(prompt)

            # Validate result structure
            if "questions" not in result:
                raise ValueError("Response missing 'questions' field")
            if "formula" not in result:
                raise ValueError("Response missing 'formula' field")

            # Add metadata
            result["need_id"] = need_id
            result["need_name"] = need["name"]
            result["need_description"] = need["description"]
            result["block"] = block_info["id"]
            result["answer_options"] = CONFIG["questions"]["answer_options"]

            # Save result
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            log.info(f"[OK] {need_id} - {len(result['questions'])} questions generated")
            return result

        except Exception as e:
            log.error(f"[ERROR] {need_id}: {e}")
            return None

    def run(
        self,
        need_id: str | None = None,
        dry_run: bool = False
    ) -> dict[str, Any]:
        """Run question generation for needs."""
        data = self.load_user_needs()
        needs = data["needs"]
        blocks = data["blocks"]
        questions_count = CONFIG["questions"]["per_need"]

        # Load breed features for formula generation
        object_features = self.load_object_features()

        log.info(f"Config: {questions_count} questions per need, {len(object_features['features'])} features available")

        # Filter by need_id if specified
        if need_id:
            needs = [n for n in needs if n["id"] == need_id]
            if not needs:
                log.error(f"Need not found: {need_id}")
                return {"processed": 0, "errors": 1}

        log.info(f"Processing {len(needs)} needs (dry_run={dry_run})")

        if dry_run:
            for n in needs:
                status = "SKIP" if (OUTPUT_DIR / f"{n['id']}.json").exists() else "PROCESS"
                block_info = self.get_block_info(n["block"], blocks)
                print(f"[{status}] {n['id']} ({block_info['name']})")
            return {"processed": 0, "would_process": len(needs)}

        results = {"processed": 0, "skipped": 0, "errors": 0}

        for need in needs:
            block_info = self.get_block_info(need["block"], blocks)
            result = self.process_need(need, block_info, questions_count, object_features)

            if result is None:
                if (OUTPUT_DIR / f"{need['id']}.json").exists():
                    results["skipped"] += 1
                else:
                    results["errors"] += 1
            else:
                results["processed"] += 1

        log.info(f"Done: {results}")
        return results


def main():
    parser = argparse.ArgumentParser(description="Generate questions for user needs")
    parser.add_argument("--need", type=str, help="Process single need by ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--model", type=str, default="gpt-4.1", help="OpenAI model to use")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    generator = QuestionGenerator(model=args.model)

    results = generator.run(
        need_id=args.need,
        dry_run=args.dry_run
    )

    sys.exit(0 if results.get("errors", 0) == 0 else 1)


if __name__ == "__main__":
    main()
