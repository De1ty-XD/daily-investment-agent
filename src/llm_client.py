import os
import re
import sys
import time
import unicodedata
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
from openai import APIConnectionError, APITimeoutError, APIStatusError


try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


load_dotenv()


class LLMResponseError(Exception):
    pass


def get_env(name: str, default: Optional[str] = None) -> str:
    return os.getenv(name, default)


LLM_BASE_URL = get_env("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
LLM_API_KEY = get_env("LLM_API_KEY", "local")
LLM_MODEL = get_env("LLM_MODEL", "gpt-oss-120b-Derestricted-q8_0.gguf")

LLM_TIMEOUT_SECONDS = float(get_env("LLM_TIMEOUT_SECONDS", "300"))
LLM_MAX_RETRIES = int(get_env("LLM_MAX_RETRIES", "2"))
LLM_TEMPERATURE = float(get_env("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(get_env("LLM_MAX_TOKENS", "1536"))


client = OpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
    timeout=LLM_TIMEOUT_SECONDS,
    max_retries=0,
)


SYSTEM_INSTRUCTION = """
You are a rigorous financial, macroeconomic, technology, and geopolitical news analysis assistant.

Rules:
1. Do not fabricate facts.
2. Do not infer details that are not supported by the provided text.
3. If information is insufficient, say "信息不足".
4. Do not provide direct buy, sell, or hold recommendations.
5. Do not provide personalized financial advice.
6. The final user-facing answer must be written in Simplified Chinese.
7. Do not include hidden reasoning in the final answer.
8. Do not include analysis text in the final answer.
9. Do not include special tokens.
10. Do not include XML-like tags.

Output format:
You must output the final answer after this exact marker:

FINAL_ANSWER_ZH:

Only write the final Simplified Chinese answer after the marker.
""".strip()


STOP_TOKENS = [
    "<|im_user|>",
    "<|im_start|>",
    "<|im_end|>",
    "<|endoftext|>",
    "<|assistant|>",
    "<|user|>",
    "<|system|>",
]


FINAL_MARKERS = [
    r"FINAL_ANSWER_ZH\s*[:：]",
    r"assistant\s*final\s*[:：]?",
    r"assistantfinal\s*[:：]?",
    r"最终答案\s*[:：]",
    r"Final answer\s*[:：]",
]


def extract_final_answer(text: str) -> str:
    """
    Extract only the final answer from models that may leak reasoning.
    """

    if not text:
        return ""

    original = text

    # Prefer content after explicit final markers.
    for marker in FINAL_MARKERS:
        matches = list(re.finditer(marker, text, flags=re.IGNORECASE | re.DOTALL))
        if matches:
            text = text[matches[-1].end():]
            break
    else:
        text = original

    # If special tokens appear after the final answer, cut there.
    for token in STOP_TOKENS:
        if token in text:
            text = text.split(token)[0]

    return text.strip()


def clean_llm_output(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)

    # Extract final answer first.
    text = extract_final_answer(text)

    # Remove leaked reasoning blocks.
    text = re.sub(r"(?is)<think>.*?</think>", "", text)
    text = re.sub(r"(?is)<analysis>.*?</analysis>", "", text)
    text = re.sub(r"(?is)<reasoning>.*?</reasoning>", "", text)

    # Remove common leaked labels.
    text = re.sub(r"(?is)^analysis\s*[:：]", "", text).strip()
    text = re.sub(r"(?is)^final\s*[:：]", "", text).strip()
    text = re.sub(r"(?is)^assistantfinal\s*[:：]?", "", text).strip()

    # Remove special-token-like fragments.
    text = re.sub(r"<\|[^>]+?\|>", "", text)
    text = re.sub(r"<\|[^>]*$", "", text)

    # Remove control chars except newline and tab.
    text = "".join(
        ch for ch in text
        if ch == "\n" or ch == "\t" or ord(ch) >= 32
    )

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove accidental repeated final marker if still present.
    text = re.sub(r"(?is)^FINAL_ANSWER_ZH\s*[:：]", "", text).strip()

    return text.strip()


def build_raw_prompt(user_prompt: str, system_prompt: Optional[str] = None) -> str:
    instruction = system_prompt.strip() if system_prompt else SYSTEM_INSTRUCTION

    return f"""
Instruction:
{instruction}

User task:
{user_prompt}

Remember:
- The final answer must be written in Simplified Chinese.
- Do not include reasoning.
- Do not include analysis.
- Do not include English unless it is a proper noun, company name, product name, or source title.
- Start the final answer with exactly this marker:

FINAL_ANSWER_ZH:
""".strip()


def ask_llm(
    user_prompt: str,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    if not user_prompt or not user_prompt.strip():
        raise ValueError("user_prompt cannot be empty.")

    temperature = LLM_TEMPERATURE if temperature is None else temperature
    max_tokens = LLM_MAX_TOKENS if max_tokens is None else max_tokens

    prompt = build_raw_prompt(user_prompt, system_prompt=system_prompt)

    last_error = None

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = client.completions.create(
                model=LLM_MODEL,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=STOP_TOKENS,
            )

            if not response.choices:
                raise LLMResponseError("LLM returned no choices.")

            content = response.choices[0].text

            if not content:
                raise LLMResponseError("LLM returned empty content.")

            cleaned = clean_llm_output(content)

            if not cleaned:
                raise LLMResponseError("LLM returned empty content after cleaning.")

            return cleaned

        except (APIConnectionError, APITimeoutError, APIStatusError, LLMResponseError) as e:
            last_error = e

            if attempt < LLM_MAX_RETRIES:
                wait_seconds = 2 ** attempt
                print(
                    f"[LLM warning] Attempt {attempt + 1} failed: {repr(e)}. "
                    f"Retrying in {wait_seconds}s..."
                )
                time.sleep(wait_seconds)
            else:
                break

    raise RuntimeError(
        f"LLM request failed after {LLM_MAX_RETRIES + 1} attempt(s). "
        f"Base URL: {LLM_BASE_URL}, Model: {LLM_MODEL}, Last error: {repr(last_error)}"
    )


def health_check() -> str:
    return ask_llm(
        """
Explain what a Treasury yield is in exactly one short sentence.
Do not use Markdown.
""".strip(),
        temperature=0.1,
        max_tokens=256,
    )


if __name__ == "__main__":
    print("LLM base URL:", LLM_BASE_URL)
    print("LLM model:", LLM_MODEL)
    print("Endpoint mode: /v1/completions")
    print("Testing LLM connection...")
    print()
    print(health_check())
