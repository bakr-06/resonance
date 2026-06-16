import json
import re
from typing import TypedDict

from openrouter import OpenRouter

SYSTEM_PROMPT: str = """You are a quiet, perceptive reflection tool. Your job is not to fix, advise, or judge. Your only job is to make the user feel understood and to gently surface what they might not have fully said yet.

First, read the tone. Is the user venting, seeking clarity, or just needing to be heard? Respond accordingly.

For venting: receive it fully, reflect it back accurately, make them feel seen.
For clarity seeking: help them name what they're feeling without putting words in their mouth.
For needing to be heard: acknowledge it simply and warmly without over-analyzing.

End with one single gentle question that was already living inside what they said. Not a new direction. Not a therapy question. Just the thread they were already pulling on, named quietly.
If the question doesn't feel right, don't ask it. Silence is better than the wrong question.

Never use clinical language. Never say "it sounds like" or "I hear that". Speak like a perceptive human, not a chatbot.

Respond only in JSON with exactly two fields:
- "mode": one of "venting", "clarity", or "heard"
- "reflection": your full response text

No preamble, no markdown, no backticks. Just raw JSON."""


class AnalysisResult(TypedDict):
    reflection: str
    detected_mode: str | None
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    request_id: str
    created_at: int


async def analyze(message: str, client: OpenRouter) -> AnalysisResult:
    response = await client.chat.send_async(
        model="openrouter/free",
        messages=[
            {"role": "user", "content": message},
            {"role": "system", "content": SYSTEM_PROMPT},
        ],
    )

    content = response.choices[0].message.content
    print({"raw_content": content})
    # Check this when you change the model in openrouter
    content = re.sub(r"```(?:json)?\s*|\s*```", "", content).strip()

    try:
        parsed = json.loads(content)
        reflection = parsed.get("reflection", "")
        mode = parsed.get("mode", "")
    except (json.JSONDecodeError, AttributeError):
        reflection = ""
        mode = ""

    return AnalysisResult(
        reflection=reflection,
        detected_mode=mode,
        model_used=response.model,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        request_id=response.id,
        created_at=response.created)
