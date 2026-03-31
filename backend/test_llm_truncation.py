import asyncio
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath("."))
load_dotenv(".env", override=True)

from modules.code_mapper.services.llm_client import chat

async def main():
    msgs = [
        {"role": "system", "content": "You are a helpful assistant. Pace your answer to ~8000 tokens."},
        {"role": "user", "content": "Write a massive essay about Rome. As long as possible. Output as much text as you can."}
    ]
    try:
        print("Calling chat()...")
        result = await chat(msgs, temperature=0.7)
        print(f"Success! Length: {len(result)}")
        print(f"Snippet: {result[:50]} ... {result[-50:]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
