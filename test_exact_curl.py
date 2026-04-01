#!/usr/bin/env python3
import httpx
import asyncio
import sys


async def test_exact_curl():
    """Test exact curl command equivalent in Python."""
    url = "http://lucabrasi.vahalla.local:7851/api/tts-generate"

    # Exact parameters from working curl command
    data = {
        "text_input": "Hello GPU test exact match",
        "character_voice_gen": "female_03.wav",
        "autoplay": "false",
        "rvccharacter_voice_gen": "latina_egirl/Latina_egirl.pth",
        # NO rvccharacter_pitch parameter!
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "test-exact-curl",
    }

    print(f"Testing exact curl match...")
    print(f"URL: {url}")
    print(f"Data: {data}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, data=data, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")

            if response.status_code == 200:
                import json

                result = response.json()
                print(f"\nSuccess! File: {result.get('output_file_path')}")

                # Try to play it
                file_path = result.get("output_file_path")
                if file_path:
                    import subprocess

                    try:
                        subprocess.run(["paplay", file_path], check=True, timeout=10)
                        print("Audio played successfully!")
                    except:
                        print(f"Audio file at: {file_path}")
            else:
                print(f"Error: {response.text}")

        except Exception as e:
            print(f"Exception: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_exact_curl())
