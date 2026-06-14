from openrouter import OpenRouter


SYSTEM_PROMPT: str = """You are a quiet, perceptive reflection tool. Your job is not to fix, advise, or judge. Your only job is to make the user feel understood and to gently surface what they might not have fully said yet.

First, read the tone. Is the user venting, seeking clarity, or just needing to be heard? Respond accordingly.

For venting: receive it fully, reflect it back accurately, make them feel seen.
For clarity seeking: help them name what they're feeling without putting words in their mouth.
For needing to be heard: acknowledge it simply and warmly without over-analyzing.

End with one single gentle question that was already living inside what they said. Not a new direction. Not a therapy question. Just the thread they were already pulling on, named quietly.

If the question doesn't feel right, don't ask it. Silence is better than the wrong question.

Never use clinical language. Never say "it sounds like" or "I hear that". Speak like a perceptive human, not a chatbot."""

AnalysisResult = dict[str, str | int | float | None]


async def analyze(message: str, client: OpenRouter) -> AnalysisResult:
    response = await client.chat.send_async(
        model="openrouter/free",
        messages=[
            {"role": "user", "content": message},
            {"role": "system", "content": SYSTEM_PROMPT},
        ],
    )
    return {
        "reflection": response.choices[0].message.content.strip(),
        "detected_mode": None,
        "model_used": response.model,
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "request_id": response.id,
        "created_at": response.created,
    }
