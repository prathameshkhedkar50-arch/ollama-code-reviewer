import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional
from fastapi import UploadFile
from services.file_service import process_uploaded_file
from services.ollama_service import generate as ollama_generate
from services.prompt_service import build_prompt
from utils.json_parser import extract_json_string, validate_and_clean

logger = logging.getLogger(__name__)

STAGE_PROMPTS = {
    "understanding": "stage1_understanding.txt",
    "bugs": "stage2_bugs.txt",
    "security": "stage3_security.txt",
    "performance": "stage4_performance.txt",
    "architecture": "stage5_architecture.txt"
}

class ReviewManager:
    def __init__(self):
        self.reviews: Dict[str, Dict[str, Any]] = {}

    def create_review(self, file_data: dict) -> str:
        """Initializes a new review and starts the background pipeline."""
        review_id = str(uuid.uuid4())
        self.reviews[review_id] = {
            "review_id": review_id,
            "status": "running",
            "stage": 3,  # Start at Stage 1 (Index 3)
            "result": None,
            "error": None
        }
        # Start the pipeline in the background so the HTTP request doesn't block/timeout
        asyncio.create_task(self._run_review_pipeline(review_id, file_data))
        return review_id

    def get_progress(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Returns the current progress object for a specific review."""
        return self.reviews.get(review_id)

    async def _run_stage(self, review_id: str, stage_name: str, stage_index: int, filename: str, language: str, code: str, understanding: str = "") -> dict:
        """Executes a single stage with retry logic and progress updates."""
        self.reviews[review_id]["stage"] = stage_index
        template_name = STAGE_PROMPTS[stage_name]
        prompt = build_prompt(filename, language, code, template_name, understanding)
        
        try:
            raw_response = await ollama_generate(prompt)
            json_str = extract_json_string(raw_response)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Stage {stage_name} failed: {e}. Retrying...")
            try:
                raw_response = await ollama_generate(prompt)
                json_str = extract_json_string(raw_response)
                return json.loads(json_str)
            except Exception as retry_e:
                logger.error(f"Stage {stage_name} failed after retry: {retry_e}")
                return {}

    async def _run_review_pipeline(self, review_id: str, file_data: dict):
        """The main background pipeline for a single review."""
        try:
            filename = file_data["filename"]
            language = file_data["language"]
            code = file_data["content"]

            # Stage 1: Understanding
            stage1_result = await self._run_stage(review_id, "understanding", 3, filename, language, code)
            understanding_str = self._format_understanding(stage1_result)

            # Stages 2-5: Parallel Analysis
            self.reviews[review_id]["stage"] = 4
            results = await asyncio.gather(
                self._run_stage(review_id, "bugs", 4, filename, language, code, understanding_str),
                self._run_stage(review_id, "security", 5, filename, language, code, understanding_str),
                self._run_stage(review_id, "performance", 6, filename, language, code, understanding_str),
                self._run_stage(review_id, "architecture", 7, filename, language, code, understanding_str)
            )
            stage2, stage3, stage4, stage5 = results

            # Merge Results
            self.reviews[review_id]["stage"] = 8
            merged_review = {
                "summary": stage1_result.get("summary", "No summary available."),
                "overall_score": stage5.get("overall_score", 0),
                "bugs": stage2.get("bugs", []),
                "security": stage3.get("security", []),
                "performance": stage4.get("performance", []),
                "readability": stage5.get("readability", []),
                "architecture": stage5.get("architecture", []),
                "best_practices": stage5.get("best_practices", []),
                "refactoring": stage5.get("refactoring", []),
                "documentation": stage5.get("documentation", []),
                "positive_points": stage5.get("positive_points", []),
                "conclusion": stage5.get("conclusion", "No conclusion available.")
            }
            cleaned_review = validate_and_clean(merged_review)

            # Finalize
            self.reviews[review_id]["stage"] = 9
            self.reviews[review_id]["status"] = "completed"
            self.reviews[review_id]["result"] = {
                "success": True,
                "filename": filename,
                "language": language,
                "review": cleaned_review
            }
            logger.info(f"Review {review_id} completed successfully.")

        except Exception as e:
            logger.error(f"Review {review_id} pipeline failed: {e}")
            self.reviews[review_id]["status"] = "failed"
            self.reviews[review_id]["error"] = str(e)

    def _format_understanding(self, stage1_result: dict) -> str:
        if not stage1_result: return "No understanding generated."
        lines = []
        if stage1_result.get("summary"): lines.append(f"Summary: {stage1_result['summary']}")
        if stage1_result.get("classes"): lines.append(f"Classes: {', '.join(stage1_result['classes'])}")
        if stage1_result.get("methods"): lines.append(f"Methods: {', '.join(stage1_result['methods'])}")
        if stage1_result.get("important_variables"): lines.append(f"Key Variables: {', '.join(stage1_result['important_variables'])}")
        if stage1_result.get("control_flow"): lines.append(f"Control Flow: {stage1_result['control_flow']}")
        if stage1_result.get("complexity"): lines.append(f"Complexity: {stage1_result['complexity']}")
        return "\n".join(lines) if lines else "No understanding generated."

# Global instance that api/review.py imports
review_manager = ReviewManager()