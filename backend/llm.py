import json
from datetime import date

from google import genai
from google.genai import types

from config import GEMINI_API_KEY
from schemas import CATEGORIES


# Turns text like "spent 250 on lunch yesterday" into a dict:
# {"amount": 250, "category": "Food", "description": "lunch", "date": "2026-10-24"}
def parse_expense_text(text: str) -> dict:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in the backend .env file")

    # timeout is in milliseconds: give up after 30 seconds instead of hanging
    client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=30000),
    )

    prompt = f"""Extract one expense from the text below.
Today's date is {date.today()}.
Allowed categories: {CATEGORIES}.

Reply with a JSON object with these keys:
amount (number), category (one of the allowed categories),
description (short text), date (YYYY-MM-DD).

Text: {text}"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    try:
        return json.loads(response.text)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("The AI did not return JSON")