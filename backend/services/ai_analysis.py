import os

from openrouter import OpenRouter

from config import settings

with OpenRouter(api_key=settings.openrouter_api_key) as client:
    response = client.chat.send(
        model="",
        messages=[
            {"role": "system", "content": ""}
        ]
    )
