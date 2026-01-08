import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("No API Key found in .env")
else:
    genai.configure(api_key=api_key)
    print(f"Checking models for key: {api_key[:5]}...")
    try:
        for m in genai.list_models():
            print(f"Name: {m.name} | Methods: {m.supported_generation_methods}")
    except Exception as e:
        print(f"Error listing models: {e}")
