"""Gemini API 독립 테스트 스크립트.

실행:
    source venv/Scripts/activate
    python tests/test_gemini.py
    python tests/test_gemini.py "원하는 프롬프트"
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT))
from config import GEMINI_MODEL as MODEL
DEFAULT_PROMPT = "안녕하세요. 오늘 날씨를 한 문장으로 묘사해 주세요."


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return 1

    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT

    print(f"[MODEL]  {MODEL}")
    print(f"[PROMPT] {prompt}")
    print("-" * 60)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=200),
    )

    print(response.text.strip())
    print("-" * 60)

    usage = getattr(response, "usage_metadata", None)
    if usage is not None:
        print(
            f"[USAGE] prompt={getattr(usage, 'prompt_token_count', '?')} "
            f"output={getattr(usage, 'candidates_token_count', '?')} "
            f"total={getattr(usage, 'total_token_count', '?')}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
