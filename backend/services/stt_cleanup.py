import logging

from openrouter import OpenRouter
from openrouter.errors import UnauthorizedResponseError

from config import settings

logger = logging.getLogger(__name__)

FREE_MODEL = "openrouter/free"


async def clean_transcript(
        raw_text: str,
        llm_model: str = FREE_MODEL,
) -> str:
    system_prompt = """You are a speech-to-text cleanup assistant. The user is recording
    their feelings and thoughts about a song they are listening to — this is a music
    listening context. Correct any transcription errors in their spoken message.
    Preserve their exact meaning, sentiment, and wording. Do not rephrase or summarize.
    Return ONLY the corrected transcript, nothing else."""
    try:
        async with OpenRouter(api_key=settings.openrouter_api_key) as client:
            response = await client.chat.send_async(
                model=llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.1,
            )
        # Returns the cleaned up transcription
        return response.choices[0].message.content.strip()
    except UnauthorizedResponseError:
        logger.error("OpenRouter 401: API key is unauthorized. Returning raw transcription as fallback.")
        return raw_text
