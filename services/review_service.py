import asyncio
import json
import logging
import time

from fastapi import HTTPException, UploadFile

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


def format_understanding(stage1_result: dict) -> str:
    """Converts the Stage 1 JSON output into a readable string context for subsequent stages."""
    if not stage1_result:
        return "No understanding generated."
    
    lines = []
    summary = stage1_result.get("summary")
    if summary and isinstance(summary, str):
        lines.append(f"Summary: {summary}")
        
    classes = stage1_result.get("classes")
    if classes and isinstance(classes, list):
        lines.append(f"Classes: {', '.join(str(c) for c in classes)}")
        
    methods = stage1_result.get("methods")
    if methods and isinstance(methods, list):
        lines.append(f"Methods: {', '.join(str(m) for m in methods)}")
        
    variables = stage1_result.get("important_variables")
    if variables and isinstance(variables, list):
        lines.append(f"Key Variables: {', '.join(str(v) for v in variables)}")
        
    control_flow = stage1_result.get("control_flow")
    if control_flow and isinstance(control_flow, str):
        lines.append(f"Control Flow: {control_flow}")
        
    complexity = stage1_result.get("complexity")
    if complexity and isinstance(complexity, str):
        lines.append(f"Complexity: {complexity}")
        
    return "\n".join(lines) if lines else "No understanding generated."


async def run_stage(stage_name: str, filename: str, language: str, code: str, understanding: str = "") -> dict:
    """Executes a single stage with retry logic and execution timing."""
    template_name = STAGE_PROMPTS[stage_name]
    prompt = build_prompt(filename, language, code, template_name, understanding)
    
    logger.info(f"Stage {stage_name} Started")
    start_time = time.time()
    
    try:
        raw_response = await ollama_generate(prompt)
        json_str = extract_json_string(raw_response)
        result = json.loads(json_str)
        duration = time.time() - start_time
        logger.info(f"Stage {stage_name} Completed ({duration:.2f}s)")
        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Stage {stage_name} failed after {duration:.2f}s: {e}. Retrying once...")
        try:
            start_time_retry = time.time()
            raw_response = await ollama_generate(prompt)
            json_str = extract_json_string(raw_response)
            result = json.loads(json_str)
            duration = time.time() - start_time_retry
            logger.info(f"Stage {stage_name} Completed after retry ({duration:.2f}s)")
            return result
        except Exception as retry_e:
            duration = time.time() - start_time
            logger.error(f"Stage {stage_name} failed after retry ({duration:.2f}s): {retry_e}")
            return {}  # Return empty dict to allow partial merge


async def review_file(file: UploadFile) -> dict:
    """Orchestrates the multi-stage AI code review process with parallel execution."""
    logger.info(f"Starting multi-stage review pipeline for file: {file.filename}")
    pipeline_start_time = time.time()
    
    # 1. Process file
    file_data = await process_uploaded_file(file)
    filename = file_data["filename"]
    language = file_data["language"]
    code = file_data["content"]
    
    # 2. Stage 1 (Sequential)
    stage1_result = await run_stage("understanding", filename, language, code)
    understanding_str = format_understanding(stage1_result)
    
    # 3. Stages 2-5 (Parallel)
    logger.info("Launching Parallel Analysis for Stages 2-5...")
    results = await asyncio.gather(
        run_stage("bugs", filename, language, code, understanding_str),
        run_stage("security", filename, language, code, understanding_str),
        run_stage("performance", filename, language, code, understanding_str),
        run_stage("architecture", filename, language, code, understanding_str)
    )
    
    stage2, stage3, stage4, stage5 = results
    
    # 4. Merge results
    logger.info("Merging Results...")
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
    
    total_duration = time.time() - pipeline_start_time
    logger.info(f"Review Completed in {total_duration:.2f}s")
    
    return {
        "success": True,
        "filename": filename,
        "language": language,
        "review": cleaned_review
    }