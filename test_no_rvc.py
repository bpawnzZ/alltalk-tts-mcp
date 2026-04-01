#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the server directory to path
sys.path.insert(0, "/home/insomnia/git/custom_tts_mcp_tool/alltalk-mcp-server")

from server import generate_tts


async def test_tts_no_rvc():
    """Test TTS generation WITHOUT RVC."""
    print("Testing AllTalk TTS generation WITHOUT RVC...")

    # Test with a simple message, NO RVC
    result = await generate_tts(
        text_input="Hello, this is a test WITHOUT RVC voice conversion.",
        character_voice_gen="female_03.wav",
        autoplay=True,
        # NO RVC parameters
        rvccharacter_voice_gen="",  # Empty string = no RVC
        language="auto",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_tts_no_rvc())
