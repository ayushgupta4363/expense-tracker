import time

from google import genai
from google.genai import types

from config import GEMINI_API_KEY

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(timeout=15000),  # 15 seconds per model
)

# every model your key can use for text generation, flash and lite only
names = []
for m in client.models.list():
    if "generateContent" in (m.supported_actions or []) and "flash" in m.name:
        names.append(m.name.replace("models/", ""))

print("Testing", len(names), "models...\n")

for name in names:
    start = time.time()
    try:
        client.models.generate_content(model=name, contents="Reply with the word OK")
        print(f"WORKS  {name}  ({time.time() - start:.1f}s)")
    except Exception as error:
        print(f"FAILS  {name}  ({str(error)[:60]})")