#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the server directory to path
sys.path.insert(0, "/home/insomnia/git/custom_tts_mcp_tool/alltalk-mcp-server")

from server import generate_tts


async def test_tts():
    """Test TTS generation directly."""
    print("Testing AllTalk TTS generation...")

    # Test with a simple message
    result = await generate_tts(
        text_input="Hello, this is a test of the AllTalk TTS system.",
        character_voice_gen="female_03.wav",
        autoplay=True,
        rvccharacter_voice_gen="latina_egirl/Latina_egirl.pth",
        rvccharacter_pitch=0,
        language="auto",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_tts())
