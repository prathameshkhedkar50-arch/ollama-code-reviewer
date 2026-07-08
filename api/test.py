from fastapi import APIRouter

from services.prompt_service import build_prompt

router = APIRouter()


@router.get("/prompt/test")
async def test_prompt() -> dict[str, str]:
    """
    Temporary endpoint to test the Prompt Builder.
    Returns the generated prompt string to verify placeholder replacement.
    """
    # Test data
    test_filename = "Main.java"
    test_language = "Java"
    test_source_code = """
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}
"""
    # Build the prompt using the corrected parameter names
    generated_prompt = build_prompt(
        filename=test_filename,
        language=test_language,
        source_code=test_source_code
    )

    return {"prompt": generated_prompt}