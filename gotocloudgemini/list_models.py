from google import genai
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path("backend/.env"))
client = genai.Client(http_options={"api_version": "v1beta"}, api_key=os.getenv("GEMINI_API_KEY"))
for m in client.models.list():
    print(m.name)
